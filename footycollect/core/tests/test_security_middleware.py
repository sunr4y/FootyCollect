"""
Tests for security middleware: headers and basic behaviour.
"""

from http import HTTPStatus

import pytest
from django.test import Client
from django.urls import reverse

HTTP_OK = HTTPStatus.OK


@pytest.mark.django_db
class TestSecurityMiddleware:
    """Tests for SecurityHeadersMiddleware."""

    def test_security_headers_present_on_health_endpoint(self):
        client = Client()

        response = client.get(reverse("health"))

        assert response.status_code == HTTP_OK
        assert response["X-Content-Type-Options"] == "nosniff"
        assert response["X-Frame-Options"] == "DENY"
        assert response["X-XSS-Protection"] == "1; mode=block"
        assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert response["Permissions-Policy"] == "geolocation=(), microphone=(), camera=()"
