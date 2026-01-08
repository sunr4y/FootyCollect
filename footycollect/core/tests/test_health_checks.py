"""
Tests for health check endpoints.
"""

from http import HTTPStatus
from unittest.mock import Mock, patch

import pytest
from django.db import DatabaseError
from django.test import Client
from django.urls import reverse

HTTP_OK = HTTPStatus.OK
HTTP_SERVICE_UNAVAILABLE = HTTPStatus.SERVICE_UNAVAILABLE


@pytest.mark.django_db
class TestHealthCheck:
    """Test /health/ endpoint."""

    def test_health_check_returns_200(self):
        """Test that /health/ endpoint returns 200 when app is running."""
        client = Client()
        response = client.get(reverse("health"))

        assert response.status_code == HTTP_OK
        assert response["Content-Type"] == "application/json"
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_check_no_authentication_required(self):
        """Test that /health/ endpoint does not require authentication."""
        client = Client()
        response = client.get(reverse("health"))

        assert response.status_code == HTTP_OK

    def test_health_check_lightweight(self):
        """Test that /health/ endpoint is lightweight (no DB queries)."""
        client = Client()
        with patch("footycollect.core.views.connection") as mock_connection:
            response = client.get(reverse("health"))

            assert response.status_code == HTTP_OK
            mock_connection.cursor.assert_not_called()


@pytest.mark.django_db
class TestReadinessCheck:
    """Test /ready/ endpoint."""

    def test_readiness_check_all_services_ready(self):
        """Test that /ready/ endpoint returns 200 when all services are ready."""
        client = Client()

        with (
            patch("footycollect.core.views.connection") as mock_connection,
            patch(
                "django.core.cache.cache",
            ) as mock_cache,
        ):
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = (1,)
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cache.set.return_value = True
            mock_cache.get.return_value = "ok"

            response = client.get(reverse("ready"))

            assert response.status_code == HTTP_OK
            assert response["Content-Type"] == "application/json"
            data = response.json()
            assert data["status"] == "ready"
            assert data["checks"]["database"] is True
            assert data["checks"]["redis"] is True

    def test_readiness_check_database_unavailable(self):
        """Test that /ready/ endpoint returns 503 when database is unavailable."""
        client = Client()

        with (
            patch("footycollect.core.views.connection") as mock_connection,
            patch(
                "django.core.cache.cache",
            ) as mock_cache,
        ):
            mock_connection.cursor.side_effect = DatabaseError("Connection failed")
            mock_cache.set.return_value = True
            mock_cache.get.return_value = "ok"

            response = client.get(reverse("ready"))

            assert response.status_code == HTTP_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "not ready"
            assert data["checks"]["database"] is False
            assert data["checks"]["redis"] is True

    def test_readiness_check_redis_unavailable(self):
        """Test that /ready/ endpoint returns 503 when Redis is unavailable."""
        client = Client()

        with (
            patch("footycollect.core.views.connection") as mock_connection,
            patch(
                "django.core.cache.cache",
            ) as mock_cache,
        ):
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = (1,)
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cache.set.side_effect = Exception("Redis connection failed")

            response = client.get(reverse("ready"))

            assert response.status_code == HTTP_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "not ready"
            assert data["checks"]["database"] is True
            assert data["checks"]["redis"] is False

    def test_readiness_check_both_services_unavailable(self):
        """Test that /ready/ endpoint returns 503 when both services are unavailable."""
        client = Client()

        with (
            patch("footycollect.core.views.connection") as mock_connection,
            patch(
                "django.core.cache.cache",
            ) as mock_cache,
        ):
            mock_connection.cursor.side_effect = DatabaseError("Connection failed")
            mock_cache.set.side_effect = Exception("Redis connection failed")

            response = client.get(reverse("ready"))

            assert response.status_code == HTTP_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "not ready"
            assert data["checks"]["database"] is False
            assert data["checks"]["redis"] is False

    def test_readiness_check_redis_not_configured(self):
        """Test that /ready/ endpoint handles Redis not configured gracefully."""
        client = Client()

        with patch("footycollect.core.views.connection") as mock_connection:
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = (1,)
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

            with patch("django.core.cache.cache") as mock_cache:
                mock_cache.set.side_effect = ImportError("No module named 'django_redis'")

                response = client.get(reverse("ready"))

                assert response.status_code == HTTP_SERVICE_UNAVAILABLE
                data = response.json()
                assert data["status"] == "not ready"
                assert data["checks"]["database"] is True
                assert data["checks"]["redis"] is False

    def test_readiness_check_no_authentication_required(self):
        """Test that /ready/ endpoint does not require authentication."""
        client = Client()

        with (
            patch("footycollect.core.views.connection") as mock_connection,
            patch(
                "django.core.cache.cache",
            ) as mock_cache,
        ):
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = (1,)
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cache.set.return_value = True
            mock_cache.get.return_value = "ok"

            response = client.get(reverse("ready"))

            assert response.status_code == HTTP_OK

    def test_readiness_check_json_format(self):
        """Test that /ready/ endpoint returns JSON format."""
        client = Client()

        with (
            patch("footycollect.core.views.connection") as mock_connection,
            patch(
                "django.core.cache.cache",
            ) as mock_cache,
        ):
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = (1,)
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cache.set.return_value = True
            mock_cache.get.return_value = "ok"

            response = client.get(reverse("ready"))

            assert response["Content-Type"] == "application/json"
            data = response.json()
            assert "status" in data
            assert "checks" in data
            assert "database" in data["checks"]
            assert "redis" in data["checks"]
