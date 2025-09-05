import hashlib
import json
import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class FKAPIClient:
    """Client to interact with the Football Kit Archive API"""

    def __init__(self):
        self.base_url = f"http://{settings.FKA_API_IP}"
        self.api_key = settings.API_KEY
        self.cache_timeout = 3600  # 1 hour cache by default
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Perform GET request with caching"""
        # Create a secure cache key using hash
        params_str = json.dumps(params, sort_keys=True) if params else ""
        hash_key = hashlib.sha256(f"{endpoint}:{params_str}".encode()).hexdigest()
        cache_key = f"fkapi_{hash_key}"

        # Try to get from cache
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.debug("Cache hit for endpoint: %s", endpoint)
            return cached_response

        # Build the full URL for logging
        full_url = f"{self.base_url}/api{endpoint}"
        logger.info("Making request to FKAPI: %s", full_url)
        logger.info("Parameters: %s", params)
        logger.info("Headers: %s", self.headers)

        try:
            response = requests.get(
                full_url,
                params=params,
                headers=self.headers,
                timeout=30,
            )

            logger.info("FKAPI response status: %s", response.status_code)
            logger.info("FKAPI response headers: %s", dict(response.headers))

            response.raise_for_status()
            data = response.json()

            logger.info("FKAPI response data: %s", data)

            # Validate response structure
            if not isinstance(data, dict):
                logger.info("FKAPI returned %s directly, normalizing to dict format", type(data).__name__)
                data = {"results": data} if isinstance(data, list) else {"data": data}

            # Save to cache
            cache.set(cache_key, data, self.cache_timeout)
            logger.debug("Cached response for endpoint: %s", endpoint)

        except requests.exceptions.RequestException:
            logger.exception("Request error to FKAPI endpoint %s", endpoint)
            raise
        except json.JSONDecodeError:
            logger.exception("JSON decode error from FKAPI endpoint %s", endpoint)
            logger.exception("Response content: %s", response.text)
            raise
        except Exception:
            logger.exception("Unexpected error in FKAPI request to %s", endpoint)
            raise

        return data

    def search_clubs(self, query: str) -> list[dict]:
        """Search clubs by name"""
        return self._get("/clubs/search", params={"keyword": query})

    def get_club_seasons(self, club_id: int) -> list[dict]:
        """Get seasons for a club"""
        return self._get("/seasons", params={"club_id": club_id})

    def get_club_kits(self, club_id: int, season_id: int) -> list[dict]:
        """Get kits for a club for a specific season"""
        return self._get(
            "/kits",
            params={
                "club_id": club_id,
                "season_id": season_id,
            },
        )

    def get_kit_details(self, kit_id: int) -> dict:
        """Get complete details of a kit"""
        return self._get(f"/kit-json/{kit_id}")

    def search_kits(self, query: str) -> list[dict]:
        """Search kits by name"""
        logger.info("Searching kits with query: '%s'", query)

        try:
            result = self._get("/kits/search", params={"keyword": query})
        except Exception:
            logger.exception("Error searching kits with query '%s'", query)
            # Return empty list instead of raising to prevent 500 errors
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
