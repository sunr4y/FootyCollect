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

    def test_test_country_view(self):
        """Test test_country_view function."""
        response = self.client.get(reverse("collection:test_country"))

        assert response.status_code == HTTP_OK
        assert "form" in response.context

    def test_test_brand_view(self):
        """Test test_brand_view function."""
        response = self.client.get(reverse("collection:test_brand"))

        assert response.status_code == HTTP_OK
        assert "form" in response.context
