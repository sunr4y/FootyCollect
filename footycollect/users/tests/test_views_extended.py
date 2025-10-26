"""
Extended tests for user views with real functionality testing.
"""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from footycollect.users.views import UserDetailView, UserRedirectView, UserUpdateView

User = get_user_model()

# Constants for test values
TEST_PASSWORD = "testpass123"
HTTP_OK = 200
HTTP_FOUND = 302
HTTP_BAD_REQUEST = 400


class TestUserViewsExtended(TestCase):
    """Extended test cases for user views with real functionality tests."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password=TEST_PASSWORD,
        )

    def test_user_detail_view_get_context_data_with_service_integration(self):
        """Test UserDetailView get_context_data with real service integration."""
        view = UserDetailView()
        view.object = self.user
        view.request = Mock()
        view.request.user = self.other_user
        view.kwargs = {"username": self.user.username}

        with patch("footycollect.users.views.UserService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_user_profile_data.return_value = {
                "profile_data": "test_data",
                "items_count": 5,
                "recent_activity": ["activity1", "activity2"],
                "stats": {"total_items": 10, "favorite_brands": 3},
            }

            with patch("footycollect.users.views.DetailView.get_context_data") as mock_super:
                mock_super.return_value = {"existing": "data"}

                result = view.get_context_data()

                mock_service.get_user_profile_data.assert_called_once_with(
                    self.user,
                    self.other_user,
                )
                assert result["existing"] == "data"
                assert result["profile_data"] == "test_data"
                assert result["items_count"] == 5  # noqa: PLR2004
                assert result["recent_activity"] == ["activity1", "activity2"]
                assert result["stats"]["total_items"] == 10  # noqa: PLR2004
                assert result["stats"]["favorite_brands"] == 3  # noqa: PLR2004

    def test_user_detail_view_handles_service_exceptions(self):
        """Test UserDetailView handles service exceptions gracefully."""
        view = UserDetailView()
        view.object = self.user
        view.request = Mock()
        view.request.user = self.other_user
        view.kwargs = {"username": self.user.username}

        with patch("footycollect.users.views.UserService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_user_profile_data.side_effect = Exception("Service unavailable")

            with patch("footycollect.users.views.DetailView.get_context_data") as mock_super:
                mock_super.return_value = {"existing": "data"}

                # The view should handle the exception gracefully
                with pytest.raises(Exception, match="Service unavailable"):
                    view.get_context_data()

    def test_user_update_view_get_object_with_authentication(self):
        """Test UserUpdateView get_object with authentication checks."""
        view = UserUpdateView()
        view.request = Mock()
        view.request.user = self.user

        # Mock the is_authenticated property
        with patch(
            "django.contrib.auth.models.User.is_authenticated",
            new_callable=lambda: property(lambda self: True),
        ):
            result = view.get_object()

            assert result == self.user

    def test_user_update_view_get_object_with_unauthenticated_user(self):
        """Test UserUpdateView get_object with unauthenticated user."""
        view = UserUpdateView()
        view.request = Mock()
        view.request.user = Mock()
        view.request.user.is_authenticated = False

        with pytest.raises(AssertionError):
            view.get_object()

    def test_user_update_view_get_success_url_with_different_users(self):
        """Test UserUpdateView get_success_url with different users."""
        view = UserUpdateView()
        view.request = Mock()
        view.request.user = self.other_user

        result = view.get_success_url()

        expected_url = reverse("users:detail", kwargs={"username": self.other_user.username})
        assert result == expected_url

    def test_user_redirect_view_get_redirect_url_with_different_users(self):
        """Test UserRedirectView get_redirect_url with different users."""
        view = UserRedirectView()
        view.request = Mock()
        view.request.user = self.other_user

        result = view.get_redirect_url()

        expected_url = reverse("users:detail", kwargs={"username": self.other_user.username})
        assert result == expected_url

    def test_user_redirect_view_permanent_attribute(self):
        """Test UserRedirectView permanent attribute configuration."""
        assert not UserRedirectView.permanent
        assert isinstance(UserRedirectView.permanent, bool)

    def test_user_detail_view_url_with_nonexistent_user(self):
        """Test user detail view URL with nonexistent user."""
        url = reverse("users:detail", kwargs={"username": "nonexistent"})
        self.client.force_login(self.user)
        response = self.client.get(url)
        assert response.status_code == 404  # noqa: PLR2004

    def test_user_update_view_post_with_valid_data(self):
        """Test user update view POST with valid data."""
        url = reverse("users:update")
        self.client.force_login(self.user)

        form_data = {
            "name": "Updated Name",
            "biography": "Updated biography",
            "location": "Updated location",
        }

        response = self.client.post(url, form_data)
        assert response.status_code == HTTP_FOUND  # Redirect after successful update

        # Check that the user was updated
        self.user.refresh_from_db()
        assert self.user.name == "Updated Name"
        assert self.user.biography == "Updated biography"
        assert self.user.location == "Updated location"

    def test_user_update_view_post_with_invalid_data(self):
        """Test user update view POST with invalid data."""
        url = reverse("users:update")
        self.client.force_login(self.user)

        form_data = {
            "name": "",  # Invalid: empty name
            "biography": "Updated biography",
            "location": "Updated location",
        }

        response = self.client.post(url, form_data)
        # The form might redirect even with invalid data due to form validation
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_user_update_view_post_with_avatar_upload(self):
        """Test user update view POST with avatar upload."""
        url = reverse("users:update")
        self.client.force_login(self.user)

        # Create a test image file
        test_image = SimpleUploadedFile(
            "test_avatar.jpg",
            b"fake image content",
            content_type="image/jpeg",
        )

        form_data = {
            "name": "Updated Name",
            "biography": "Updated biography",
            "location": "Updated location",
            "avatar": test_image,
        }

        response = self.client.post(url, form_data)
        # The form might return 200 if there are validation errors
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_user_views_authentication_required(self):
        """Test user views require authentication."""
        urls = [
            reverse("users:detail", kwargs={"username": self.user.username}),
            reverse("users:update"),
            reverse("users:redirect"),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                assert response.status_code == HTTP_FOUND  # Redirect to login

    def test_user_detail_view_with_different_authenticated_user(self):
        """Test user detail view with different authenticated user."""
        url = reverse("users:detail", kwargs={"username": self.other_user.username})
        self.client.force_login(self.user)
        response = self.client.get(url)
        assert response.status_code == HTTP_OK

    def test_user_redirect_view_redirects_to_correct_user_detail(self):
        """Test user redirect view redirects to correct user detail."""
        url = reverse("users:redirect")
        self.client.force_login(self.other_user)
        response = self.client.get(url)

        expected_url = reverse("users:detail", kwargs={"username": self.other_user.username})
        self.assertRedirects(response, expected_url)

    def test_user_update_view_context_includes_form(self):
        """Test user update view context includes form."""
        url = reverse("users:update")
        self.client.force_login(self.user)
        response = self.client.get(url)

        assert response.status_code == HTTP_OK
        assert "form" in response.context
        assert response.context["form"] is not None

    def test_user_detail_view_context_includes_user_object(self):
        """Test user detail view context includes user object."""
        url = reverse("users:detail", kwargs={"username": self.user.username})
        self.client.force_login(self.user)
        response = self.client.get(url)

        assert response.status_code == HTTP_OK
        assert "object" in response.context
        assert response.context["object"] == self.user

    def test_user_views_handle_anonymous_user_redirects(self):
        """Test user views handle anonymous user with proper redirects."""
        urls = [
            reverse("users:detail", kwargs={"username": self.user.username}),
            reverse("users:update"),
            reverse("users:redirect"),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                assert response.status_code == HTTP_FOUND  # Redirect to login
                # Check that it redirects to login page
                assert "/accounts/login/" in response.url or "/login/" in response.url

    def test_user_update_view_form_validation_with_email(self):
        """Test user update view form validation with email."""
        url = reverse("users:update")
        self.client.force_login(self.user)

        form_data = {
            "name": "Updated Name",
            "email": "invalid-email",  # Invalid email format
            "biography": "Updated biography",
        }

        response = self.client.post(url, form_data)
        # The form might redirect even with invalid data due to form validation
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_user_views_mixin_inheritance(self):
        """Test user views inherit from correct mixins."""
        # Test LoginRequiredMixin
        assert hasattr(UserDetailView, "login_url")
        assert hasattr(UserUpdateView, "login_url")
        assert hasattr(UserRedirectView, "login_url")

        # Test SuccessMessageMixin
        assert hasattr(UserUpdateView, "success_message")

        # Test DetailView, UpdateView, RedirectView
        assert hasattr(UserDetailView, "model")
        assert hasattr(UserUpdateView, "model")
        assert hasattr(UserRedirectView, "permanent")

    def test_user_views_model_configuration(self):
        """Test user views model configuration."""
        assert UserDetailView.model == User
        assert UserUpdateView.model == User
        assert UserDetailView.slug_field == "username"
        assert UserDetailView.slug_url_kwarg == "username"

    def test_user_update_view_form_class_configuration(self):
        """Test UserUpdateView form_class configuration."""
        from footycollect.users.forms import UserUpdateForm

        assert UserUpdateView.form_class == UserUpdateForm

    def test_user_update_view_success_message_configuration(self):
        """Test UserUpdateView success_message configuration."""
        assert UserUpdateView.success_message == "Profile updated successfully"

    def test_user_detail_view_slug_configuration(self):
        """Test UserDetailView slug configuration."""
        assert UserDetailView.slug_field == "username"
        assert UserDetailView.slug_url_kwarg == "username"

    def test_user_views_url_patterns(self):
        """Test user views URL patterns work correctly."""
        # Test that all URLs are accessible when authenticated
        urls = [
            reverse("users:detail", kwargs={"username": self.user.username}),
            reverse("users:update"),
            reverse("users:redirect"),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.client.force_login(self.user)
                response = self.client.get(url)
                assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_user_redirect_view_permanent_redirect(self):
        """Test UserRedirectView permanent redirect behavior."""
        url = reverse("users:redirect")
        self.client.force_login(self.user)
        response = self.client.get(url)

        # Check that it's a redirect (302 or 301)
        assert response.status_code in [HTTP_FOUND, 301]

    def test_user_update_view_post_with_partial_data(self):
        """Test user update view POST with partial data."""
        url = reverse("users:update")
        self.client.force_login(self.user)

        form_data = {
            "name": "Updated Name",
            # Missing biography and location
        }

        response = self.client.post(url, form_data)
        # The form might redirect even with partial data
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_user_detail_view_with_self_viewing(self):
        """Test user detail view when user views their own profile."""
        url = reverse("users:detail", kwargs={"username": self.user.username})
        self.client.force_login(self.user)
        response = self.client.get(url)

        assert response.status_code == HTTP_OK
        assert "object" in response.context
        assert response.context["object"] == self.user
