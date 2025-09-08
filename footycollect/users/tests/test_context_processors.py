"""
Tests for user context processors.
"""

from django.test import RequestFactory, override_settings

from footycollect.users.context_processors import allauth_settings


class TestAllauthSettingsContextProcessor:
    """Test allauth settings context processor."""

    def test_allauth_settings_context(self):
        """Test that allauth settings are exposed in context."""
        factory = RequestFactory()
        request = factory.get("/")

        context = allauth_settings(request)

        assert "ACCOUNT_ALLOW_REGISTRATION" in context
        assert isinstance(context["ACCOUNT_ALLOW_REGISTRATION"], bool)

    @override_settings(ACCOUNT_ALLOW_REGISTRATION=True)
    def test_allauth_settings_registration_enabled(self):
        """Test context when registration is enabled."""
        factory = RequestFactory()
        request = factory.get("/")

        context = allauth_settings(request)

        assert context["ACCOUNT_ALLOW_REGISTRATION"] is True

    @override_settings(ACCOUNT_ALLOW_REGISTRATION=False)
    def test_allauth_settings_registration_disabled(self):
        """Test context when registration is disabled."""
        factory = RequestFactory()
        request = factory.get("/")

        context = allauth_settings(request)

        assert context["ACCOUNT_ALLOW_REGISTRATION"] is False
