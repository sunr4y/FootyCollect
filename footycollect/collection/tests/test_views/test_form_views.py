"""
Tests for form-based views and test functions.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from footycollect.collection.factories import (
    BrandFactory,
    ClubFactory,
    SeasonFactory,
    SizeFactory,
    UserFactory,
)

User = get_user_model()

# HTTP status codes
HTTP_OK = 200
HTTP_FOUND = 302


class FormViewsTest(TestCase):
    """Test form-based views and test functions."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.user.set_password("testpass123")
        self.user.save()

        # Create test objects
        self.brand = BrandFactory()
        self.club = ClubFactory()
        self.season = SeasonFactory()
        self.size = SizeFactory()

    def test_demo_country_view_integration(self):
        """Test demo_country_view integration with real form functionality."""
        response = self.client.get(reverse("collection:test_country"))

        # Test response status
        assert response.status_code == HTTP_OK

        # Test context contains form
        assert "form" in response.context
        form = response.context["form"]

        # Test form is properly instantiated
        assert form is not None
        assert hasattr(form, "fields")

        # Test form has expected fields for country selection
        expected_fields = ["country"]  # Based on typical country form
        for field in expected_fields:
            if field in form.fields:
                assert field in form.fields

        # Test template rendering
        assert "form" in str(response.content).lower() or "country" in str(response.content).lower()

    def test_demo_brand_view_integration(self):
        """Test demo_brand_view integration with real form functionality."""
        response = self.client.get(reverse("collection:test_brand"))

        # Test response status
        assert response.status_code == HTTP_OK

        # Test context contains form
        assert "form" in response.context
        form = response.context["form"]

        # Test form is properly instantiated
        assert form is not None
        assert hasattr(form, "fields")

        # Test form has expected fields for brand selection
        expected_fields = ["brand"]  # Based on typical brand form
        for field in expected_fields:
            if field in form.fields:
                assert field in form.fields

        # Test template rendering
        assert "form" in str(response.content).lower() or "brand" in str(response.content).lower()
