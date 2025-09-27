"""
Tests for navbar links functionality.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()
HTTP_OK = 200


class NavbarLinksTestCase(TestCase):
    """Test that all navbar links work correctly."""

    def setUp(self):
        """Set up test data."""
        test_password = "testpass123"  # noqa: S105
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=test_password,
        )

    def test_home_link(self):
        """Test that home link works."""
        response = self.client.get(reverse("home"))
        assert response.status_code == HTTP_OK

    def test_about_link(self):
        """Test that about link works."""
        response = self.client.get(reverse("about"))
        assert response.status_code == HTTP_OK

    def test_authenticated_user_links(self):
        """Test links that are only visible to authenticated users."""
        test_password = "testpass123"  # noqa: S105
        self.client.login(username="testuser", password=test_password)

        # Test collection links
        response = self.client.get(reverse("collection:item_create"))
        assert response.status_code == HTTP_OK

        response = self.client.get(reverse("collection:item_list"))
        assert response.status_code == HTTP_OK

        response = self.client.get(reverse("collection:jersey_fkapi_create"))
        assert response.status_code == HTTP_OK

        # Test user profile link
        response = self.client.get(reverse("users:detail", kwargs={"username": "testuser"}))
        assert response.status_code == HTTP_OK

        # Test user update link
        response = self.client.get(reverse("users:update"))
        assert response.status_code == HTTP_OK

    def test_anonymous_user_links(self):
        """Test links that are visible to anonymous users."""
        # Test sign in link
        response = self.client.get(reverse("account_login"))
        assert response.status_code == HTTP_OK

        # Test sign up link (if registration is allowed)
        response = self.client.get(reverse("account_signup"))
        assert response.status_code == HTTP_OK

    def test_navbar_renders_without_errors(self):
        """Test that navbar template renders without errors."""
        # Test for authenticated user
        test_password = "testpass123"  # noqa: S105
        self.client.login(username="testuser", password=test_password)
        response = self.client.get(reverse("home"))
        assert response.status_code == HTTP_OK
        self.assertContains(response, "FootyCollect")
        self.assertContains(response, "Collection")
        self.assertContains(response, "My Profile")

        # Test for anonymous user
        self.client.logout()
        response = self.client.get(reverse("home"))
        assert response.status_code == HTTP_OK
        self.assertContains(response, "FootyCollect")
        self.assertContains(response, "Sign In")
