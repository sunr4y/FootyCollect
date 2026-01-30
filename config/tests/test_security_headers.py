import pytest
from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from config.middleware import SecurityHeadersMiddleware


class TestSecurityHeadersMiddleware:
    def test_adds_referrer_policy_when_set(self):
        middleware = SecurityHeadersMiddleware(get_response=lambda r: HttpResponse())
        request = RequestFactory().get("/")
        with override_settings(REFERRER_POLICY="strict-origin-when-cross-origin"):
            response = middleware(request)
        assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_adds_permissions_policy_when_set(self):
        middleware = SecurityHeadersMiddleware(get_response=lambda r: HttpResponse())
        request = RequestFactory().get("/")
        with override_settings(PERMISSIONS_POLICY="geolocation=(), camera=()"):
            response = middleware(request)
        assert response["Permissions-Policy"] == "geolocation=(), camera=()"

    def test_skips_referrer_policy_when_unset(self):
        middleware = SecurityHeadersMiddleware(get_response=lambda r: HttpResponse())
        request = RequestFactory().get("/")
        with override_settings(REFERRER_POLICY=None):
            response = middleware(request)
        assert "Referrer-Policy" not in response

    def test_skips_permissions_policy_when_unset(self):
        middleware = SecurityHeadersMiddleware(get_response=lambda r: HttpResponse())
        request = RequestFactory().get("/")
        with override_settings(PERMISSIONS_POLICY=None):
            response = middleware(request)
        assert "Permissions-Policy" not in response


class TestSecuritySettings:
    def test_session_cookie_httponly(self):
        assert settings.SESSION_COOKIE_HTTPONLY is True

    def test_csrf_cookie_httponly(self):
        assert settings.CSRF_COOKIE_HTTPONLY is True

    def test_session_cookie_samesite(self):
        assert settings.SESSION_COOKIE_SAMESITE in ("Lax", "Strict", "None")

    def test_csrf_cookie_samesite(self):
        assert settings.CSRF_COOKIE_SAMESITE in ("Lax", "Strict", "None")

    def test_x_frame_options_deny(self):
        assert settings.X_FRAME_OPTIONS == "DENY"

    def test_secure_content_type_nosniff(self):
        assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True

    def test_referrer_and_permissions_policy_defined(self):
        assert getattr(settings, "REFERRER_POLICY", None)
        assert getattr(settings, "PERMISSIONS_POLICY", None)


@pytest.mark.django_db
class TestSecurityHeadersInResponse:
    def test_response_has_security_headers(self, client):
        response = client.get("/")
        assert "Referrer-Policy" in response
        assert "Permissions-Policy" in response
