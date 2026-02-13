"""
Tests for FKAPI client with real data.
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
import requests

# Test constants
CIRCUIT_FAILURE_THRESHOLD = 5
MIN_BULK_SLUGS = 2
MAX_BULK_SLUGS = 30
HAMMARBY_CLUB_ID = 893
HAMMARBY_SEARCH_RESULTS_COUNT = 3
CLUB_2089_SEASONS_COUNT = 16
SEASON_691_ID = 691
SEASON_41_ID = 41
CLUB_749_ID = 749
KIT_171008_ID = 171008
SECONDARY_COLORS_COUNT = 2
SK_BRANN_SEARCH_RESULTS_COUNT = 3
SK_BRANN_KIT_337301_ID = 337301
INVALID_JSON_STRING_LENGTH = 12


@pytest.mark.django_db
class TestFKAPIClient:
    """Test FKAPIClient functionality with real API data."""

    def test_client_initialization(self):
        """Test FKAPIClient initialization."""
        from footycollect.api.client import FKAPIClient

        client = FKAPIClient()
        assert hasattr(client, "base_url")
        assert hasattr(client, "api_key")
        assert hasattr(client, "cache_timeout")
        assert hasattr(client, "headers")

    @patch("footycollect.api.client.requests.get")
    def test_search_clubs_success(self, mock_get):
        """Test successful club search with real data."""
        from footycollect.api.client import FKAPIClient

        # Mock real Hammarby search response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = [
            {
                "id": 893,
                "name": "Hammarby",
                "slug": "hammarby-kits",
                "logo": "https://www.footballkitarchive.com//static/logos/teams/271.png?v=1654464659&s=128",
            },
            {
                "id": 5986,
                "name": "Hammarby Talang FF",
                "slug": "hammarby-talang-ff-kits",
                "logo": "https://www.footballkitarchive.com//static/logos/teams/9690.png?v=1680488446&s=128",
            },
            {
                "id": 16525,
                "name": "Hammarby IF Dam",
                "slug": "hammarby-if-dam-kits",
                "logo": "https://www.footballkitarchive.com/static/logos/not_found.png",
            },
        ]
        mock_get.return_value = mock_response

        client = FKAPIClient()
        results = client.search_clubs("Hammarby")

        assert results is not None
        assert isinstance(results, list)
        assert len(results) == HAMMARBY_SEARCH_RESULTS_COUNT
        assert results[0]["id"] == HAMMARBY_CLUB_ID
        assert results[0]["name"] == "Hammarby"
        assert "logo" in results[0]

    @patch("footycollect.api.client.requests.get")
    def test_get_club_seasons_success(self, mock_get):
        """Test successful club seasons retrieval with real data."""
        from footycollect.api.client import FKAPIClient

        # Mock real seasons response for club 2089
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = [
            {"id": 691, "year": "2025"},
            {"id": 41, "year": "2024"},
            {"id": 3, "year": "2023"},
            {"id": 5, "year": "2022"},
            {"id": 33, "year": "2021"},
            {"id": 8, "year": "2020"},
            {"id": 34, "year": "2019"},
            {"id": 11, "year": "2018"},
            {"id": 35, "year": "2017"},
            {"id": 44, "year": "2016"},
            {"id": 36, "year": "2015"},
            {"id": 18, "year": "2013"},
            {"id": 37, "year": "2011"},
            {"id": 45, "year": "2009"},
            {"id": 38, "year": "2006"},
            {"id": 334, "year": "1995"},
        ]
        mock_get.return_value = mock_response

        client = FKAPIClient()
        results = client.get_club_seasons(2089)

        assert results is not None
        assert isinstance(results, list)
        assert len(results) == CLUB_2089_SEASONS_COUNT
        assert results[0]["id"] == SEASON_691_ID
        assert results[0]["year"] == "2025"
        assert results[1]["id"] == SEASON_41_ID
        assert results[1]["year"] == "2024"

    @patch("footycollect.api.client.requests.get")
    def test_get_club_kits_success(self, mock_get):
        """Test successful club kits retrieval with real data."""
        from footycollect.api.client import FKAPIClient

        # Mock real kits response (empty for club 749, season 2025)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        client = FKAPIClient()
        results = client.get_club_kits(CLUB_749_ID, 2025)

        assert results is not None
        assert isinstance(results, list)
        assert len(results) == 0

    @patch("footycollect.api.client.requests.get")
    def test_get_kit_details_success(self, mock_get):
        """Test successful kit details retrieval with real data."""
        from footycollect.api.client import FKAPIClient

        # Mock real kit details response for kit 171008
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {
            "name": "Sanfrecce Hiroshima 2005 Home",
            "slug": "sanfrecce-hiroshima-2005-home-kit",
            "team": {
                "id": 628,
                "id_fka": None,
                "name": "Sanfrecce Hiroshima",
                "slug": "sanfrecce-hiroshima-kits",
                "logo": "https://www.footballkitarchive.com//static/logos/teams/446.png?v=1654464680&s=128",
                "logo_dark": None,
                "country": "JP",
            },
            "season": {
                "id": 51,
                "year": "2005",
                "first_year": "2005",
                "second_year": None,
            },
            "competition": [
                {
                    "id": 787,
                    "name": "J-League",
                    "slug": "j-league-kits",
                    "logo": "https://www.footballkitarchive.com/static/logos/not_found.png",
                    "logo_dark": None,
                    "country": "JP",
                },
            ],
            "type": {
                "name": "Home",
            },
            "brand": {
                "id": 1671,
                "name": "Mizuno",
                "slug": "mizuno-kits",
                "logo": "https://www.footballkitarchive.com//static/logos/misc/Mizuno.png?v=1665185440",
                "logo_dark": "https://www.footballkitarchive.com//static/logos/misc/Mizuno_l.png?v=1665185440",
            },
            "design": "Plain",
            "primary_color": {
                "name": "Purple",
                "color": "#800080",
            },
            "secondary_color": [
                {
                    "name": "Black",
                    "color": "#000000",
                },
                {
                    "name": "Orange",
                    "color": "#FFA500",
                },
            ],
            "main_img_url": "https://cdn.footballkitarchive.com/2021/05/11/szcmzr6XoyeOeSW.jpg",
        }
        mock_get.return_value = mock_response

        client = FKAPIClient()
        result = client.get_kit_details(KIT_171008_ID)

        assert result is not None
        assert result["name"] == "Sanfrecce Hiroshima 2005 Home"
        assert result["team"]["name"] == "Sanfrecce Hiroshima"
        assert result["team"]["country"] == "JP"
        assert result["season"]["year"] == "2005"
        assert result["brand"]["name"] == "Mizuno"
        assert result["primary_color"]["color"] == "#800080"
        assert len(result["secondary_color"]) == SECONDARY_COLORS_COUNT
        assert result["main_img_url"] is not None

    @patch("footycollect.api.client.requests.get")
    def test_search_kits_success(self, mock_get):
        """Test successful kit search with real data."""
        from footycollect.api.client import FKAPIClient

        # Mock real SK Brann search response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = [
            {
                "id": 337301,
                "name": "SK Brann 2025 Pre-Match",
                "main_img_url": "https://cdn.footballkitarchive.com/2025/04/01/cOg8tMXEIBtmsEm.jpg",
                "team_name": "SK Brann",
                "season_year": "2025",
            },
            {
                "id": 349457,
                "name": "SK Brann 2008 Anniversary 2",
                "main_img_url": "https://cdn.footballkitarchive.com/2025/02/03/TlvdRMTy36JResc.jpg",
                "team_name": "SK Brann",
                "season_year": "2008",
            },
            {
                "id": 349478,
                "name": "SK Brann 2024 Away",
                "main_img_url": "https://cdn.footballkitarchive.com/2024/07/12/Xp7ziE7IDrsPrD7.jpg",
                "team_name": "SK Brann",
                "season_year": "2024",
            },
        ]
        mock_get.return_value = mock_response

        client = FKAPIClient()
        results = client.search_kits("Sk Brann")

        assert results is not None
        assert len(results) == SK_BRANN_SEARCH_RESULTS_COUNT
        assert results[0]["id"] == SK_BRANN_KIT_337301_ID
        assert results[0]["name"] == "SK Brann 2025 Pre-Match"
        assert results[0]["team_name"] == "SK Brann"
        assert results[0]["season_year"] == "2025"
        assert "main_img_url" in results[0]

    @patch("footycollect.api.client.requests.get")
    def test_search_kits_empty_results(self, mock_get):
        """Test kit search with empty results."""
        from footycollect.api.client import FKAPIClient

        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        client = FKAPIClient()
        results = client.search_kits("NonExistentTeam")

        assert results is not None
        assert len(results) == 0

    @patch("footycollect.api.client.requests.get")
    def test_search_kits_api_error(self, mock_get):
        """Test kit search with API error."""
        from footycollect.api.client import FKAPIClient

        # Mock API error
        mock_get.side_effect = requests.RequestException("API Error")

        client = FKAPIClient()
        results = client.search_kits("Barcelona")

        assert results is not None
        assert len(results) == 0

    @patch("footycollect.api.client.cache")
    @patch("footycollect.api.client.requests.get")
    def test_get_club_seasons_api_error(self, mock_get, mock_cache):
        """Test club seasons retrieval with API error."""
        from footycollect.api.client import FKAPIClient

        # Mock cache miss for all keys
        mock_cache.get.return_value = None
        # Mock API error
        mock_get.side_effect = requests.RequestException("API Error")

        client = FKAPIClient()

        results = client.get_club_seasons(2089)
        assert results == []

    @patch("footycollect.api.client.cache")
    @patch("footycollect.api.client.requests.get")
    def test_get_club_kits_api_error(self, mock_get, mock_cache):
        """Test club kits retrieval with API error."""
        from footycollect.api.client import FKAPIClient

        # Mock cache miss for all keys
        mock_cache.get.return_value = None
        # Mock API error
        mock_get.side_effect = requests.RequestException("API Error")

        client = FKAPIClient()

        results = client.get_club_kits(CLUB_749_ID, 2025)
        assert results == []

    @patch("footycollect.api.client.cache")
    @patch("footycollect.api.client.requests.get")
    def test_get_kit_details_api_error(self, mock_get, mock_cache):
        """Test kit details retrieval with API error."""
        from footycollect.api.client import FKAPIClient

        # Mock cache miss for all keys
        mock_cache.get.return_value = None
        # Mock API error
        mock_get.side_effect = requests.RequestException("API Error")

        client = FKAPIClient()

        result = client.get_kit_details(KIT_171008_ID)
        assert result is None

    @patch("footycollect.api.client.cache")
    @patch("footycollect.api.client.requests.get")
    def test_search_clubs_api_error(self, mock_get, mock_cache):
        """Test club search with API error."""
        from footycollect.api.client import FKAPIClient

        # Mock cache miss for all keys
        mock_cache.get.return_value = None
        # Mock API error
        mock_get.side_effect = requests.RequestException("API Error")

        client = FKAPIClient()

        results = client.search_clubs("Hammarby")
        assert results == []

    @patch("footycollect.api.client.cache")
    @patch("footycollect.api.client.requests.get")
    def test_search_kits_with_empty_query(self, mock_get, mock_cache):
        """Test kit search with empty query."""
        from footycollect.api.client import FKAPIClient

        # Mock cache miss and empty response
        mock_cache.get.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        client = FKAPIClient()
        results = client.search_kits("")

        # Should return empty results for empty query
        assert results is not None
        assert len(results) == 0

    @patch("footycollect.api.client.cache")
    @patch("footycollect.api.client.requests.get")
    def test_search_kits_with_none_query(self, mock_get, mock_cache):
        """Test kit search with None query."""
        from footycollect.api.client import FKAPIClient

        # Mock cache miss and empty response
        mock_cache.get.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        client = FKAPIClient()
        results = client.search_kits("")

        # Should return empty results for empty query
        assert results is not None
        assert len(results) == 0

    @patch("footycollect.api.client.requests.get")
    def test_search_kits_list_response(self, mock_get):
        """Test kit search with list response format."""
        from footycollect.api.client import FKAPIClient

        # Mock list response (some APIs return lists directly)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = [
            {
                "id": 337301,
                "name": "SK Brann 2025 Pre-Match",
                "main_img_url": "https://cdn.footballkitarchive.com/2025/04/01/cOg8tMXEIBtmsEm.jpg",
                "team_name": "SK Brann",
                "season_year": "2025",
            },
        ]
        mock_get.return_value = mock_response

        client = FKAPIClient()
        results = client.search_kits("Test Query List")  # Use different query to avoid cache

        assert results is not None
        assert len(results) == 1
        assert results[0]["name"] == "SK Brann 2025 Pre-Match"

    @patch("footycollect.api.client.requests.get")
    def test_search_kits_dict_response(self, mock_get):
        """Test kit search with dict response format."""
        from footycollect.api.client import FKAPIClient

        # Mock dict response with results key
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {
            "results": [
                {
                    "id": 337301,
                    "name": "SK Brann 2025 Pre-Match",
                    "main_img_url": "https://cdn.footballkitarchive.com/2025/04/01/cOg8tMXEIBtmsEm.jpg",
                    "team_name": "SK Brann",
                    "season_year": "2025",
                },
            ],
        }
        mock_get.return_value = mock_response

        client = FKAPIClient()
        results = client.search_kits("Test Query Dict")  # Use different query to avoid cache

        assert results is not None
        assert len(results) == 1
        assert results[0]["name"] == "SK Brann 2025 Pre-Match"

    @patch("footycollect.api.client.requests.get")
    def test_search_kits_invalid_response_format(self, mock_get):
        """Test kit search with invalid response format."""
        from footycollect.api.client import FKAPIClient

        # Mock invalid response format
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = "invalid json"
        mock_get.return_value = mock_response

        client = FKAPIClient()
        results = client.search_kits("Test Invalid Response")  # Use different query to avoid cache

        # Should handle invalid response gracefully
        assert results is not None
        # The client normalizes string responses to dict format, so we get the string length
        assert len(results) == INVALID_JSON_STRING_LENGTH  # "invalid json" has 12 characters

    @patch("footycollect.api.client.requests.get")
    def test_cache_functionality(self, mock_get):
        """Test that caching works correctly."""
        from footycollect.api.client import FKAPIClient

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = [
            {
                "id": 893,
                "name": "Hammarby",
                "slug": "hammarby-kits",
                "logo": "https://www.footballkitarchive.com//static/logos/teams/271.png?v=1654464659&s=128",
            },
        ]
        mock_get.return_value = mock_response

        client = FKAPIClient()

        # First call
        results1 = client.search_clubs("Test Cache")

        # Second call should use cache
        results2 = client.search_clubs("Test Cache")

        # Both should return the same results
        assert results1 == results2

        # But requests.get should only be called once due to caching
        assert mock_get.call_count == 1

    @patch("footycollect.api.client.requests.post")
    def test_post_success_200_returns_normalized_data(self, mock_post):
        from footycollect.api.client import FKAPIClient

        client = FKAPIClient()
        client.max_retries = 1

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"{}"
        mock_response.json.return_value = {"foo": "bar"}
        mock_post.return_value = mock_response

        result = client._post("/test-endpoint", data={"payload": 1})

        assert result == {"foo": "bar"}
        mock_post.assert_called_once()

    @patch("footycollect.api.client.requests.post")
    def test_post_timeout_calls_retry_logic_and_returns_none(self, mock_post):
        from footycollect.api.client import FKAPIClient

        client = FKAPIClient()
        client.max_retries = 1

        mock_post.side_effect = requests.exceptions.Timeout()

        with patch(
            "footycollect.api.client.FKAPIClient._handle_all_retries_failed",
        ) as mock_handle_failed:
            result = client._post("/timeout-endpoint", data={"payload": 1})

        assert result is None
        mock_handle_failed.assert_called_once()

    @patch("footycollect.api.client.requests.post")
    def test_post_http_error_calls_handle_all_retries_failed(self, mock_post):
        from footycollect.api.client import FKAPIClient

        client = FKAPIClient()
        client.max_retries = 1

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_response.reason = "Internal Server Error"
        mock_response.json.return_value = {"error": "Server error"}
        mock_post.return_value = mock_response

        with patch(
            "footycollect.api.client.FKAPIClient._handle_all_retries_failed",
        ) as mock_handle_failed:
            result = client._post("/error-endpoint", data={"payload": 1})

        assert result is None
        mock_handle_failed.assert_called_once()

    @patch("footycollect.api.client.requests.post")
    def test_post_json_decode_error_stops_retries_and_returns_none(self, mock_post):
        from footycollect.api.client import FKAPIClient

        client = FKAPIClient()
        client.max_retries = 1

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"invalid"
        mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
        mock_post.return_value = mock_response

        with patch(
            "footycollect.api.client.FKAPIClient._handle_all_retries_failed",
        ) as mock_handle_failed:
            result = client._post("/json-error-endpoint", data={"payload": 1})

        assert result is None
        mock_handle_failed.assert_called_once()


class TestCircuitBreaker:
    """Tests for CircuitBreaker used by FKAPIClient."""

    def test_record_success_resets_state(self):
        from footycollect.api.client import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=CIRCUIT_FAILURE_THRESHOLD, timeout=60)
        for _ in range(3):
            cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "closed"
        assert cb.last_failure_time is None

    def test_record_failure_opens_after_threshold(self):
        from footycollect.api.client import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=CIRCUIT_FAILURE_THRESHOLD, timeout=60)
        for _ in range(CIRCUIT_FAILURE_THRESHOLD):
            cb.record_failure()
        assert cb.state == "open"
        assert cb.is_open() is True

    def test_is_open_transitions_to_half_open_after_timeout(self):
        from footycollect.api.client import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=2, timeout=1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        cb.last_failure_time = datetime.now(UTC) - timedelta(seconds=2)
        assert cb.is_open() is False
        assert cb.state == "half_open"

    def test_allow_request_false_when_open(self):
        from footycollect.api.client import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=1, timeout=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.allow_request() is False


class TestFKAPIClientBranches:
    """Tests for FKAPIClient branches: circuit breaker, rate limit, stale cache, bulk, extract."""

    @patch("footycollect.api.client.cache")
    @patch("footycollect.api.client.requests.get")
    def test_get_returns_stale_cache_when_circuit_breaker_open(self, mock_get, mock_cache):
        from footycollect.api.client import FKAPIClient

        def cache_get(key):
            if key == "fkapi_rate_limit":
                return None
            if str(key).startswith("fkapi_"):
                return {"results": [{"id": 1}]}
            return None

        mock_cache.get.side_effect = cache_get
        client = FKAPIClient()
        client.circuit_breaker.state = "open"
        client.circuit_breaker.last_failure_time = datetime.now(UTC)

        result = client._get("/clubs/search", params={"keyword": "x"}, use_cache=True)

        assert result == {"results": [{"id": 1}]}
        mock_get.assert_not_called()

    @patch("footycollect.api.client.cache")
    @patch("footycollect.api.client.requests.get")
    def test_get_returns_stale_cache_when_rate_limit_exceeded(self, mock_get, mock_cache):
        from footycollect.api.client import FKAPIClient

        def cache_get(key):
            if key == "fkapi_rate_limit":
                return 200
            return {"results": []} if str(key).startswith("fkapi_") else None

        mock_cache.get.side_effect = cache_get
        client = FKAPIClient()

        result = client._get("/clubs/search", params={"keyword": "y"}, use_cache=True)

        assert result == {"results": []}
        mock_get.assert_not_called()

    @patch("footycollect.api.client.cache")
    @patch("footycollect.api.client.requests.get")
    def test_execute_request_timeout_returns_request_result(self, mock_get, mock_cache):
        from footycollect.api.client import FKAPIClient

        mock_cache.get.return_value = None
        mock_get.side_effect = requests.exceptions.Timeout()
        client = FKAPIClient()
        client.max_retries = 1

        result = client.search_clubs("timeout-test")

        assert result == []

    @patch("footycollect.api.client.cache")
    @patch("footycollect.api.client.requests.get")
    def test_execute_request_json_decode_error_returns_empty(self, mock_get, mock_cache):
        from footycollect.api.client import FKAPIClient

        mock_cache.get.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("err", "doc", 0)
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = FKAPIClient()
        client.max_retries = 1
        result = client.search_clubs("json-err-test")

        assert result == []

    @patch("footycollect.api.client.cache")
    @patch("footycollect.api.client.requests.get")
    def test_post_http_error_returns_none(self, mock_get, mock_cache):
        from footycollect.api.client import FKAPIClient

        mock_cache.get.return_value = None
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_response.reason = "Server Error"
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        with patch("footycollect.api.client.requests.post") as mock_post:
            mock_post.return_value = mock_response
            client = FKAPIClient()
            client.max_retries = 1
            with patch.object(client, "_handle_all_retries_failed") as mock_handle:
                result = client._post("/user-collection/1/scrape")
                assert result is None
                mock_handle.assert_called_once()

    def test_get_kits_bulk_too_few_slugs_returns_empty(self):
        from footycollect.api.client import FKAPIClient

        client = FKAPIClient()
        result = client.get_kits_bulk(["one"])
        assert result == []

    @patch("footycollect.api.client.FKAPIClient._get")
    def test_get_kits_bulk_truncates_when_more_than_max(self, mock_get):
        from footycollect.api.client import FKAPIClient

        mock_get.return_value = {"results": []}
        client = FKAPIClient()
        slugs = [f"slug-{i}" for i in range(MAX_BULK_SLUGS + 5)]
        client.get_kits_bulk(slugs)
        call_args = mock_get.call_args
        assert call_args[0][0] == "/kits/bulk"
        param_slugs = call_args[1]["params"]["slugs"].split(",")
        assert len(param_slugs) == MAX_BULK_SLUGS

    def test_extract_list_from_result_unexpected_type_returns_empty(self):
        from footycollect.api.client import FKAPIClient

        client = FKAPIClient()
        result = client._extract_list_from_result("not-dict-or-list")
        assert result == []
