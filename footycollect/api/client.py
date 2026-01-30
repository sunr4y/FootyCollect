import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Bulk endpoint constraints
MIN_BULK_SLUGS = 2
MAX_BULK_SLUGS = 30


class CircuitBreaker:
    """Circuit breaker pattern to prevent cascading failures."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "closed"  # closed, open, half_open

    def record_success(self):
        """Record a successful request."""
        self.failure_count = 0
        self.state = "closed"
        self.last_failure_time = None

    def record_failure(self):
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                "Circuit breaker opened after %d failures",
                self.failure_count,
            )

    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self.state == "open":
            if self.last_failure_time:
                time_since_failure = datetime.now(UTC) - self.last_failure_time
                if time_since_failure.total_seconds() >= self.timeout:
                    self.state = "half_open"
                    logger.info("Circuit breaker transitioning to half-open state")
                    return False
            return True
        return False

    def allow_request(self) -> bool:
        """Check if request should be allowed."""
        return not self.is_open()


@dataclass
class RequestContext:
    """Context for a single API request."""

    endpoint: str
    params: dict | None
    cache_key: str
    use_cache: bool


class FKAPIClient:
    """Client to interact with the Football Kit Archive API."""

    def __init__(self):
        self.base_url = f"http://{settings.FKA_API_IP}"
        self.api_key = settings.API_KEY
        self.cache_timeout = 3600  # 1 hour cache by default
        self.request_timeout = 60
        self.max_retries = 3
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        # Rate limiting: max 100 requests per minute
        self.rate_limit_max = 100
        self.rate_limit_window = 60  # seconds

    def _get(
        self,
        endpoint: str,
        params: dict | None = None,
        *,
        use_cache: bool = True,
    ) -> dict | None:
        """
        Perform GET request with caching, retry logic, and circuit breaker.

        Returns:
            dict: Response data if successful, None if all retries fail
        """
        ctx = self._create_request_context(endpoint, params, use_cache=use_cache)

        # Try cache first
        if cached := self._try_cache(ctx):
            return cached

        # Check availability (circuit breaker + rate limit)
        if not self._check_availability(ctx):
            return self._get_stale_cache(ctx)

        # Make the actual request
        data = self._make_request_with_retries(ctx)
        if data is not None:
            self._cache_response(ctx, data)
            return data

        return self._get_stale_cache(ctx)

    def _create_request_context(
        self,
        endpoint: str,
        params: dict | None,
        *,
        use_cache: bool,
    ) -> RequestContext:
        """Create request context with cache key."""
        params_str = json.dumps(params, sort_keys=True) if params else ""
        hash_key = hashlib.sha256(f"{endpoint}:{params_str}".encode()).hexdigest()
        cache_key = f"fkapi_{hash_key}"
        return RequestContext(
            endpoint=endpoint,
            params=params,
            cache_key=cache_key,
            use_cache=use_cache,
        )

    def _try_cache(self, ctx: RequestContext) -> dict | None:
        """Try to get response from cache."""
        if not ctx.use_cache:
            return None
        cached = cache.get(ctx.cache_key)
        if cached:
            logger.debug("Cache hit for endpoint: %s", ctx.endpoint)
            return cached
        return None

    def _get_stale_cache(self, ctx: RequestContext) -> dict | None:
        """Get stale cache as fallback."""
        if not ctx.use_cache:
            return None
        stale = cache.get(ctx.cache_key)
        if stale:
            logger.info("Returning stale cache as fallback for: %s", ctx.endpoint)
            return stale
        return None

    def _cache_response(self, ctx: RequestContext, data: dict) -> None:
        """Cache the response."""
        if ctx.use_cache:
            cache.set(ctx.cache_key, data, self.cache_timeout)
            logger.debug("Cached response for endpoint: %s", ctx.endpoint)

    def _check_availability(self, ctx: RequestContext) -> bool:
        """Check if request should proceed (circuit breaker + rate limit)."""
        if not self.circuit_breaker.allow_request():
            logger.warning("Circuit breaker is open for endpoint: %s", ctx.endpoint)
            return False

        if not self._check_rate_limit():
            logger.warning("Rate limit exceeded for endpoint: %s", ctx.endpoint)
            return False

        return True

    def _check_rate_limit(self) -> bool:
        """Check if request is within rate limit."""
        rate_limit_key = "fkapi_rate_limit"
        current_count = cache.get(rate_limit_key) or 0

        if current_count >= self.rate_limit_max:
            logger.warning(
                "Rate limit exceeded: %d requests in the last %d seconds",
                current_count,
                self.rate_limit_window,
            )
            return False

        cache.set(rate_limit_key, current_count + 1, self.rate_limit_window)
        return True

    def _make_request_with_retries(self, ctx: RequestContext) -> dict | None:
        """Make HTTP request with retry logic and exponential backoff."""
        full_url = f"{self.base_url}/api{ctx.endpoint}"
        logger.info("Making request to FKAPI: %s", full_url)

        last_exception = None
        for attempt in range(self.max_retries):
            if attempt > 0:
                self._wait_with_backoff(attempt)

            result = self._execute_request(full_url, ctx.params, ctx.endpoint, attempt)
            if result.success:
                self.circuit_breaker.record_success()
                return result.data

            last_exception = result.error
            if result.should_stop:
                break

        self._handle_all_retries_failed(ctx.endpoint, last_exception)
        return None

    def _wait_with_backoff(self, attempt: int) -> None:
        """Wait with exponential backoff before retry."""
        wait_time = 2**attempt
        logger.info(
            "Retrying request (attempt %d/%d) after %ds delay",
            attempt + 1,
            self.max_retries,
            wait_time,
        )
        time.sleep(wait_time)

    def _post(
        self,
        endpoint: str,
        data: dict | None = None,
        *,
        use_cache: bool = False,
    ) -> dict | None:
        """Perform POST request with retry logic."""
        full_url = f"{self.base_url}/api{endpoint}"
        logger.info("Making POST request to FKAPI: %s", full_url)

        last_exception = None
        for attempt in range(self.max_retries):
            if attempt > 0:
                self._wait_with_backoff(attempt)

            result = self._execute_post_request(full_url, data, endpoint, attempt)
            if result.success:
                self.circuit_breaker.record_success()
                return result.data

            last_exception = result.error
            if result.should_stop:
                break

        self._handle_all_retries_failed(endpoint, last_exception)
        return None

    def _execute_post_request(
        self,
        url: str,
        data: dict | None,
        endpoint: str,
        attempt: int,
    ) -> "RequestResult":
        """Execute a single HTTP POST request."""
        try:
            response = requests.post(
                url,
                json=data,
                headers=self.headers,
                timeout=self.request_timeout,
            )
            logger.info("FKAPI POST response status: %s for %s", response.status_code, endpoint)

            if response.status_code in (200, 202):
                response_data = response.json() if response.content else {}
                data = self._normalize_response(response_data)
                return RequestResult(success=True, data=data)
            error_msg = response.text[:200] if response.text else f"{response.status_code} {response.reason}"
            try:
                error_data = response.json()
                if isinstance(error_data, dict):
                    error_msg = error_data.get("error") or error_data.get("message") or error_msg
                elif isinstance(error_data, str):
                    error_msg = error_data
            except (ValueError, TypeError):
                logger.debug("Could not parse error response as JSON")
            error_message = f"{error_msg} for url: {url}"
            raise requests.exceptions.HTTPError(error_message, response=response)

        except requests.exceptions.Timeout:
            logger.warning(
                "POST request timeout (attempt %d/%d) for endpoint: %s",
                attempt + 1,
                self.max_retries,
                endpoint,
            )
            return RequestResult(
                success=False,
                error=requests.exceptions.Timeout(
                    f"Request timeout after {self.request_timeout}s",
                ),
            )

        except requests.exceptions.RequestException as e:
            logger.warning(
                "POST request error (attempt %d/%d) for endpoint %s: %s",
                attempt + 1,
                self.max_retries,
                endpoint,
                str(e),
            )
            return RequestResult(success=False, error=e)

        except json.JSONDecodeError as e:
            logger.exception(
                "JSON decode error (attempt %d/%d) from FKAPI POST endpoint %s",
                attempt + 1,
                self.max_retries,
                endpoint,
            )
            return RequestResult(success=False, error=e, should_stop=True)

    def _execute_request(
        self,
        url: str,
        params: dict | None,
        endpoint: str,
        attempt: int,
    ) -> "RequestResult":
        """Execute a single HTTP request."""
        try:
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.request_timeout,
            )
            logger.info("FKAPI response status: %s", response.status_code)
            response.raise_for_status()

            data = self._normalize_response(response.json())
            return RequestResult(success=True, data=data)

        except requests.exceptions.Timeout:
            logger.warning(
                "Request timeout (attempt %d/%d) for endpoint: %s",
                attempt + 1,
                self.max_retries,
                endpoint,
            )
            return RequestResult(
                success=False,
                error=requests.exceptions.Timeout(
                    f"Request timeout after {self.request_timeout}s",
                ),
            )

        except requests.exceptions.RequestException as e:
            logger.warning(
                "Request error (attempt %d/%d) for endpoint %s: %s",
                attempt + 1,
                self.max_retries,
                endpoint,
                str(e),
            )
            return RequestResult(success=False, error=e)

        except json.JSONDecodeError as e:
            logger.exception(
                "JSON decode error (attempt %d/%d) from FKAPI endpoint %s",
                attempt + 1,
                self.max_retries,
                endpoint,
            )
            return RequestResult(success=False, error=e, should_stop=True)

    def _normalize_response(self, data: dict | list) -> dict:
        """Normalize API response to dict format."""
        if isinstance(data, dict):
            return data
        logger.info(
            "FKAPI returned %s directly, normalizing to dict format",
            type(data).__name__,
        )
        return {"results": data} if isinstance(data, list) else {"data": data}

    def _handle_all_retries_failed(
        self,
        endpoint: str,
        last_exception: Exception | None,
    ) -> None:
        """Handle the case when all retries have failed."""
        self.circuit_breaker.record_failure()
        logger.error(
            "All retries failed for endpoint %s. Last error: %s",
            endpoint,
            str(last_exception),
        )

    # Public API methods

    def search_clubs(self, query: str) -> list[dict]:
        """Search clubs by name."""
        result = self._get("/clubs/search", params={"keyword": query})
        return self._extract_list_from_result(result)

    def get_club_seasons(self, club_id: int) -> list[dict]:
        """Get seasons for a club."""
        result = self._get("/seasons", params={"id": club_id})
        return self._extract_list_from_result(result)

    def get_club_kits(self, club_id: int, season_id: int) -> list[dict]:
        """Get kits for a club for a specific season."""
        # Use nested club kits endpoint from FKAPI
        endpoint = f"/clubs/{club_id}/kits"
        params = {"season": season_id}
        result = self._get(endpoint, params=params)
        return self._extract_list_from_result(result)

    def get_kit_details(self, kit_id: int, *, use_cache: bool = True) -> dict | None:
        """Get complete details of a kit."""
        # Use primary kit details endpoint (legacy /kit-json/{id} is still available but deprecated)
        return self._get(f"/kits/{kit_id}", use_cache=use_cache)

    def search_kits(self, query: str) -> list[dict]:
        """Search kits by name."""
        logger.info("Searching kits with query: '%s'", query)
        result = self._get("/kits/search", params={"keyword": query})

        if result is None:
            logger.warning("FKAPI unavailable, returning empty results for kit search")
            return []

        results = self._extract_list_from_result(result)
        logger.info("Search returned %s results", len(results))
        return results

    def search_brands(self, query: str) -> list[dict]:
        """Search brands by name from external database."""
        logger.info("Searching brands with query: '%s'", query)
        result = self._get("/brands/search", params={"keyword": query})

        if result is None:
            logger.warning("FKAPI unavailable, trying alternative method for brand search")
            kits = self.search_kits(query)
            brands = {}
            for kit in kits:
                brand = kit.get("brand") or kit.get("team", {}).get("brand")
                if brand:
                    brand_name = brand.get("name") if isinstance(brand, dict) else brand
                    if brand_name and brand_name not in brands:
                        brands[brand_name] = {
                            "id": brand.get("id") if isinstance(brand, dict) else None,
                            "name": brand_name,
                        }
            return list(brands.values())

        results = self._extract_list_from_result(result)
        logger.info("Brand search returned %s results", len(results))
        return results

    def search_competitions(self, query: str) -> list[dict]:
        """Search competitions by name from external database."""
        logger.info("Searching competitions with query: '%s'", query)
        result = self._get("/competitions/search", params={"keyword": query})

        if result is None:
            logger.warning("FKAPI unavailable, trying alternative method for competition search")
            kits = self.search_kits(query)
            competitions = {}
            for kit in kits:
                comps = kit.get("competition") or kit.get("competitions", [])
                if not isinstance(comps, list):
                    comps = [comps] if comps else []
                for comp in comps:
                    comp_name = comp.get("name") if isinstance(comp, dict) else comp
                    if comp_name and comp_name not in competitions:
                        competitions[comp_name] = {
                            "id": comp.get("id") if isinstance(comp, dict) else None,
                            "name": comp_name,
                        }
            return list(competitions.values())

        results = self._extract_list_from_result(result)
        logger.info("Competition search returned %s results", len(results))
        return results

    def get_kits_bulk(self, slugs: list[str]) -> list[dict]:
        """Get multiple kits by their slugs in a single request.

        Args:
            slugs: List of kit slugs (2-30 slugs supported)

        Returns:
            List of kit data with reduced response format:
            - name, team (name, logo, country), season (year), brand (name, logo), main_img_url
        """
        if not slugs:
            return []

        if len(slugs) < MIN_BULK_SLUGS:
            logger.warning("Bulk endpoint requires at least %d slugs, got %d", MIN_BULK_SLUGS, len(slugs))
            return []

        if len(slugs) > MAX_BULK_SLUGS:
            logger.warning("Bulk endpoint supports max %d slugs, got %d. Truncating.", MAX_BULK_SLUGS, len(slugs))
            slugs = slugs[:MAX_BULK_SLUGS]

        slugs_param = ",".join(slugs)
        logger.info("Fetching %d kits in bulk", len(slugs))
        result = self._get("/kits/bulk", params={"slugs": slugs_param})
        logger.debug("Bulk API raw result type: %s", type(result))
        if result:
            logger.debug("Bulk API result keys: %s", result.keys() if isinstance(result, dict) else "N/A (list)")
        extracted = self._extract_list_from_result(result)
        logger.info("Bulk API extracted %d kits", len(extracted))
        return extracted

    def _extract_list_from_result(self, result: dict | list | None) -> list[dict]:
        """Extract list from API result, handling various response formats."""
        if result is None:
            return []
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("results", result.get("data", []))
        logger.warning("Unexpected response type: %s", type(result))
        return []

    def post_scrape_user_collection(self, userid: int) -> dict | None:
        """POST to scrape user collection endpoint. Returns API response."""
        return self._post(f"/user-collection/{userid}/scrape")

    def scrape_user_collection(self, userid: int) -> dict | None:
        """Start scraping user collection. Returns response with task_id or data."""
        from .tasks import scrape_user_collection_task

        scrape_user_collection_task.delay(userid)
        return {"status": "queued"}

    def get_user_collection(
        self, userid: int, page: int = 1, page_size: int = 20, *, use_cache: bool = False
    ) -> dict | None:
        """Get user collection with pagination."""
        endpoint = f"/user-collection/{userid}"
        params = {"page": page, "page_size": page_size}
        return self._get(endpoint, params=params, use_cache=use_cache)


@dataclass
class RequestResult:
    """Result of a single HTTP request attempt."""

    success: bool
    data: dict | None = None
    error: Exception | None = None
    should_stop: bool = False
