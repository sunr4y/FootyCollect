import hashlib
import json
import logging
import time
from datetime import UTC, datetime

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker pattern to prevent cascading failures"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "closed"  # closed, open, half_open

    def record_success(self):
        """Record a successful request"""
        self.failure_count = 0
        self.state = "closed"
        self.last_failure_time = None

    def record_failure(self):
        """Record a failed request"""
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                "Circuit breaker opened after %d failures",
                self.failure_count,
            )

    def is_open(self) -> bool:
        """Check if circuit breaker is open"""
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
        """Check if request should be allowed"""
        return not self.is_open()


class FKAPIClient:
    """Client to interact with the Football Kit Archive API"""

    def __init__(self):
        self.base_url = f"http://{settings.FKA_API_IP}"
        self.api_key = settings.API_KEY
        self.cache_timeout = 3600  # 1 hour cache by default
        self.request_timeout = 10  # Reduced from 30s to 10s
        self.max_retries = 3
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

    def _get(  # noqa: PLR0912, PLR0915, C901
        self,
        endpoint: str,
        params: dict | None = None,
        *,
        use_cache: bool = True,
    ) -> dict | None:
        """
        Perform GET request with caching, retry logic, and circuit breaker.

        Returns:
            dict: Response data if successful, None if all retries fail and no cache available
        """
        # Create a secure cache key using hash
        params_str = json.dumps(params, sort_keys=True) if params else ""
        hash_key = hashlib.sha256(f"{endpoint}:{params_str}".encode()).hexdigest()
        cache_key = f"fkapi_{hash_key}"

        # Try to get from cache first
        if use_cache:
            cached_response = cache.get(cache_key)
            if cached_response:
                logger.debug("Cache hit for endpoint: %s", endpoint)
                return cached_response

        # Check circuit breaker
        if not self.circuit_breaker.allow_request():
            logger.warning(
                "Circuit breaker is open, returning cached data or None for endpoint: %s",
                endpoint,
            )
            # Try to return stale cache if available
            if use_cache:
                stale_cache = cache.get(cache_key)
                if stale_cache:
                    logger.info("Returning stale cache due to circuit breaker")
                    return stale_cache
            return None

        # Build the full URL for logging
        full_url = f"{self.base_url}/api{endpoint}"
        logger.info("Making request to FKAPI: %s", full_url)
        logger.info("Parameters: %s", params)

        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    wait_time = 2**attempt  # Exponential backoff: 2s, 4s, 8s
                    logger.info(
                        "Retrying request (attempt %d/%d) after %ds delay",
                        attempt + 1,
                        self.max_retries,
                        wait_time,
                    )
                    time.sleep(wait_time)

                response = requests.get(
                    full_url,
                    params=params,
                    headers=self.headers,
                    timeout=self.request_timeout,
                )

                logger.info("FKAPI response status: %s", response.status_code)

                response.raise_for_status()
                data = response.json()

                # Validate response structure
                if not isinstance(data, dict):
                    logger.info(
                        "FKAPI returned %s directly, normalizing to dict format",
                        type(data).__name__,
                    )
                    data = {"results": data} if isinstance(data, list) else {"data": data}

                # Save to cache
                if use_cache:
                    cache.set(cache_key, data, self.cache_timeout)
                    logger.debug("Cached response for endpoint: %s", endpoint)

                # Record success in circuit breaker
                self.circuit_breaker.record_success()
                return data  # noqa: TRY300
            except requests.exceptions.Timeout:
                last_exception = requests.exceptions.Timeout(
                    f"Request timeout after {self.request_timeout}s",
                )
                logger.warning(
                    "Request timeout (attempt %d/%d) for endpoint: %s",
                    attempt + 1,
                    self.max_retries,
                    endpoint,
                )
            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.warning(
                    "Request error (attempt %d/%d) for endpoint %s: %s",
                    attempt + 1,
                    self.max_retries,
                    endpoint,
                    str(e),
                )
            except json.JSONDecodeError as e:
                last_exception = e
                logger.exception(
                    "JSON decode error (attempt %d/%d) from FKAPI endpoint %s",
                    attempt + 1,
                    self.max_retries,
                    endpoint,
                )
                # Don't retry JSON decode errors
                break
            except Exception as e:
                last_exception = e
                logger.exception(
                    "Unexpected error (attempt %d/%d) in FKAPI request to %s",
                    attempt + 1,
                    self.max_retries,
                    endpoint,
                )

        # All retries failed
        self.circuit_breaker.record_failure()
        logger.error(
            "All retries failed for endpoint %s. Last error: %s",
            endpoint,
            str(last_exception),
        )

        # Try to return stale cache as fallback
        if use_cache:
            stale_cache = cache.get(cache_key)
            if stale_cache:
                logger.info("Returning stale cache as fallback after all retries failed")
                return stale_cache

        return None

    def search_clubs(self, query: str) -> list[dict]:
        """Search clubs by name"""
        result = self._get("/clubs/search", params={"keyword": query})
        if result is None:
            return []
        if isinstance(result, dict):
            return result.get("results", result.get("data", []))
        if isinstance(result, list):
            return result
        return []

    def get_club_seasons(self, club_id: int) -> list[dict]:
        """Get seasons for a club"""
        result = self._get("/seasons", params={"id": club_id})
        if result is None:
            return []
        if isinstance(result, dict):
            return result.get("results", result.get("data", []))
        if isinstance(result, list):
            return result
        return []

    def get_club_kits(self, club_id: int, season_id: int) -> list[dict]:
        """Get kits for a club for a specific season"""
        result = self._get(
            "/kits",
            params={
                "club": club_id,
                "season": season_id,
            },
        )
        if result is None:
            return []
        if isinstance(result, dict):
            return result.get("results", result.get("data", []))
        if isinstance(result, list):
            return result
        return []

    def get_kit_details(self, kit_id: int) -> dict | None:
        """Get complete details of a kit"""
        return self._get(f"/kit-json/{kit_id}")

    def search_kits(self, query: str) -> list[dict]:
        """Search kits by name"""
        logger.info("Searching kits with query: '%s'", query)

        result = self._get("/kits/search", params={"keyword": query})
        if result is None:
            logger.warning("FKAPI unavailable, returning empty results for kit search")
            return []

        # Ensure we return a list
        if isinstance(result, dict):
            if "results" in result:
                results = result["results"]
            elif "data" in result:
                results = result["data"]
            else:
                logger.warning("Unexpected response structure: %s", result)
                results = []
        elif isinstance(result, list):
            results = result
        else:
            logger.warning("Unexpected response type: %s", type(result))
            results = []

        logger.info("Search returned %s results", len(results))
        if results:
            logger.debug("First result: %s", results[0])

        return results
