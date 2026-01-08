"""
Tests for API views.
"""

import json
from unittest.mock import Mock, patch

import pytest
from django.test import RequestFactory
from django.urls import reverse

from footycollect.api.views import (
    get_club_kits,
    get_club_seasons,
    get_kit_details,
    search_clubs,
    search_kits,
)

# HTTP status codes
HTTP_OK = 200
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503

# Test data constants
EXPECTED_RESULTS_COUNT = 2
HAMMARBY_KIT_ID = 171008
CLUB_ID = 893
SEASON_ID = 691


@pytest.mark.django_db
class TestAPIViews:
    """Test API views functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()

    def test_search_clubs_success(self):
        """Test successful club search."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.search_clubs.return_value = [
                {"id": 893, "name": "Hammarby", "country": "Sweden"},
                {"id": 749, "name": "SK Brann", "country": "Norway"},
            ]

            request = self.factory.get("/api/clubs/search/?keyword=hammarby")
            response = search_clubs(request)

            assert response.status_code == HTTP_OK
            data = json.loads(response.content)
            assert "results" in data
            assert len(data["results"]) == EXPECTED_RESULTS_COUNT
            assert data["results"][0]["name"] == "Hammarby"

    def test_search_clubs_empty_query(self):
        """Test club search with empty query."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.search_clubs.return_value = []

            request = self.factory.get("/api/clubs/search/")
            response = search_clubs(request)

            assert response.status_code == HTTP_OK
            data = json.loads(response.content)
            assert "results" in data
            assert data["results"] == []

    def test_search_clubs_api_error(self):
        """Test club search with API error."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.search_clubs.return_value = []

            request = self.factory.get("/api/clubs/search/?keyword=test")
            response = search_clubs(request)

            assert response.status_code == HTTP_OK
            data = json.loads(response.content)
            assert "results" in data
            assert data["results"] == []

    def test_search_clubs_unexpected_error(self):
        """Test club search with unexpected error."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.search_clubs.return_value = []

            request = self.factory.get("/api/clubs/search/?keyword=test")
            response = search_clubs(request)

            assert response.status_code == HTTP_OK
            data = json.loads(response.content)
            assert "results" in data
            assert data["results"] == []

    def test_get_kit_details_success(self):
        """Test successful kit details retrieval."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_kit_details.return_value = {
                "id": 171008,
                "name": "Hammarby Home 2023-24",
                "club": "Hammarby",
                "season": "2023-24",
                "type": "home",
            }

            request = self.factory.get("/api/kit/171008/")
            response = get_kit_details(request, kit_id=HAMMARBY_KIT_ID)

            assert response.status_code == HTTP_OK
            data = json.loads(response.content)
            assert data["id"] == HAMMARBY_KIT_ID
            assert data["name"] == "Hammarby Home 2023-24"

    def test_get_kit_details_api_error(self):
        """Test kit details with API error."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_kit_details.return_value = None

            request = self.factory.get("/api/kit/999999/")
            response = get_kit_details(request, kit_id=999999)

            assert response.status_code == HTTP_SERVICE_UNAVAILABLE
            data = json.loads(response.content)
            assert "error" in data
            assert "temporarily unavailable" in data["error"]

    def test_get_kit_details_unexpected_error(self):
        """Test kit details with unexpected error."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_kit_details.return_value = None

            request = self.factory.get("/api/kit/171008/")
            response = get_kit_details(request, kit_id=HAMMARBY_KIT_ID)

            assert response.status_code == HTTP_SERVICE_UNAVAILABLE
            data = json.loads(response.content)
            assert "error" in data
            assert "temporarily unavailable" in data["error"]

    def test_search_kits_success(self):
        """Test successful kit search."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.search_kits.return_value = [
                {"id": 171008, "name": "Hammarby Home 2023/24"},
                {"id": 171009, "name": "Hammarby Away 2023/24"},
            ]

            request = self.factory.get("/api/kits/search/?keyword=hammarby")
            response = search_kits(request)

            assert response.status_code == HTTP_OK
            data = json.loads(response.content)
            assert "results" in data
            assert len(data["results"]) == EXPECTED_RESULTS_COUNT

    def test_search_kits_short_query(self):
        """Test kit search with query too short."""
        request = self.factory.get("/api/kits/search/?keyword=ha")
        response = search_kits(request)

        assert response.status_code == HTTP_OK
        data = json.loads(response.content)
        assert "results" in data
        assert data["results"] == []

    def test_search_kits_empty_query(self):
        """Test kit search with empty query."""
        request = self.factory.get("/api/kits/search/")
        response = search_kits(request)

        assert response.status_code == HTTP_OK
        data = json.loads(response.content)
        assert "results" in data
        assert data["results"] == []

    def test_search_kits_api_error(self):
        """Test kit search with API error."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.search_kits.return_value = []

            request = self.factory.get("/api/kits/search/?keyword=hammarby")
            response = search_kits(request)

            assert response.status_code == HTTP_OK
            data = json.loads(response.content)
            assert "results" in data
            assert data["results"] == []

    def test_search_kits_unexpected_error(self):
        """Test kit search with unexpected error."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.search_kits.return_value = []

            request = self.factory.get("/api/kits/search/?keyword=hammarby")
            response = search_kits(request)

            assert response.status_code == HTTP_OK
            data = json.loads(response.content)
            assert "results" in data
            assert data["results"] == []

    def test_get_club_seasons_success(self):
        """Test successful club seasons retrieval."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_club_seasons.return_value = [
                {"id": 691, "name": "2023-24"},
                {"id": 692, "name": "2022-23"},
            ]

            request = self.factory.get("/api/clubs/893/seasons/")
            response = get_club_seasons(request, club_id=CLUB_ID)

            assert response.status_code == HTTP_OK
            data = json.loads(response.content)
            assert "results" in data
            assert len(data["results"]) == EXPECTED_RESULTS_COUNT

    def test_get_club_seasons_api_error(self):
        """Test club seasons with API error."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_club_seasons.return_value = []

            request = self.factory.get("/api/clubs/893/seasons/")
            response = get_club_seasons(request, club_id=CLUB_ID)

            assert response.status_code == HTTP_OK
            data = json.loads(response.content)
            assert "results" in data
            assert data["results"] == []

    def test_get_club_seasons_unexpected_error(self):
        """Test club seasons with unexpected error."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_club_seasons.return_value = []

            request = self.factory.get("/api/clubs/893/seasons/")
            response = get_club_seasons(request, club_id=CLUB_ID)

            assert response.status_code == HTTP_OK
            data = json.loads(response.content)
            assert "results" in data
            assert data["results"] == []

    def test_get_club_kits_success(self):
        """Test successful club kits retrieval."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_club_kits.return_value = [
                {"id": 171008, "name": "Home Kit", "type": "home"},
                {"id": 171009, "name": "Away Kit", "type": "away"},
            ]

            request = self.factory.get("/api/clubs/893/seasons/691/kits/")
            response = get_club_kits(request, club_id=CLUB_ID, season_id=SEASON_ID)

            assert response.status_code == HTTP_OK
            data = json.loads(response.content)
            assert "results" in data
            assert len(data["results"]) == EXPECTED_RESULTS_COUNT

    def test_get_club_kits_api_error(self):
        """Test club kits with API error."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_club_kits.return_value = []

            request = self.factory.get("/api/clubs/893/seasons/691/kits/")
            response = get_club_kits(request, club_id=CLUB_ID, season_id=SEASON_ID)

            assert response.status_code == HTTP_OK
            data = json.loads(response.content)
            assert "results" in data
            assert data["results"] == []

    def test_get_club_kits_unexpected_error(self):
        """Test club kits with unexpected error."""
        with patch("footycollect.api.views.FKAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_club_kits.return_value = []

            request = self.factory.get("/api/clubs/893/seasons/691/kits/")
            response = get_club_kits(request, club_id=CLUB_ID, season_id=SEASON_ID)

            assert response.status_code == HTTP_OK
            data = json.loads(response.content)
            assert "results" in data
            assert data["results"] == []


@pytest.mark.django_db
class TestAPIURLs:
    """Test API URL patterns."""

    def test_search_clubs_url(self):
        """Test search clubs URL pattern."""
        url = reverse("footycollect_api:search_clubs")
        assert url == "/fkapi/clubs/search/"

    def test_kit_details_url(self):
        """Test kit details URL pattern."""
        url = reverse("footycollect_api:kit_details", kwargs={"kit_id": 171008})
        assert url == "/fkapi/kit/171008/"

    def test_search_kits_url(self):
        """Test search kits URL pattern."""
        url = reverse("footycollect_api:search_kits")
        assert url == "/fkapi/kits/search/"

    def test_club_seasons_url(self):
        """Test club seasons URL pattern."""
        url = reverse("footycollect_api:club_seasons", kwargs={"club_id": 893})
        assert url == "/fkapi/clubs/893/seasons/"

    def test_club_season_kits_url(self):
        """Test club season kits URL pattern."""
        url = reverse(
            "footycollect_api:club_season_kits",
            kwargs={"club_id": 893, "season_id": 691},
        )
        assert url == "/fkapi/clubs/893/seasons/691/kits/"
