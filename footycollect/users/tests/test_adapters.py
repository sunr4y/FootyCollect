"""
Tests for user adapters.
"""

from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase

from footycollect.users.adapters import CustomAccountAdapter, CustomSocialAccountAdapter
from footycollect.users.models import User


class TestCustomAccountAdapter(TestCase):
    """Test cases for CustomAccountAdapter."""

    def setUp(self):
        """Set up test data."""
        self.adapter = CustomAccountAdapter()
        self.factory = RequestFactory()

    def test_is_open_for_signup_true(self):
        """Test is_open_for_signup returns True when ACCOUNT_ALLOW_REGISTRATION is True."""
        allow_registration = True
        with patch("footycollect.users.adapters.settings.ACCOUNT_ALLOW_REGISTRATION", allow_registration):
            request = self.factory.get("/")
            result = self.adapter.is_open_for_signup(request)
            assert result is True

    def test_is_open_for_signup_false(self):
        """Test is_open_for_signup returns False when ACCOUNT_ALLOW_REGISTRATION is False."""
        allow_registration = False
        with patch("footycollect.users.adapters.settings.ACCOUNT_ALLOW_REGISTRATION", allow_registration):
            request = self.factory.get("/")
            result = self.adapter.is_open_for_signup(request)
            assert result is False

    def test_save_user_new_email(self):
        """Test save_user with new email."""
        request = self.factory.post("/")
        user = User()
        form = Mock()
        form.cleaned_data = {"email": "new@example.com"}

        with patch("footycollect.users.adapters.User.objects.filter") as mock_filter:
            mock_filter.return_value.exists.return_value = False

            with patch.object(user, "save") as mock_save:
                result = self.adapter.save_user(request, user, form, commit=True)

                assert result == user
                mock_save.assert_called_once()

    def test_save_user_existing_email_social(self):
        """Test save_user with existing email that has social accounts."""
        request = self.factory.post("/")
        user = User()
        form = Mock()
        form.cleaned_data = {"email": "existing@example.com"}

        existing_user = Mock()
        existing_user.socialaccount_set.exists.return_value = True
        existing_user.socialaccount_set.values_list.return_value = ["google", "facebook"]

        with patch("footycollect.users.adapters.User.objects.filter") as mock_filter:
            mock_filter.return_value.exists.return_value = True
            with patch("footycollect.users.adapters.User.objects.get") as mock_get:
                mock_get.return_value = existing_user

                with pytest.raises(ValidationError) as context:
                    self.adapter.save_user(request, user, form, commit=True)

                assert "google, facebook" in str(context.value)

    def test_save_user_existing_email_regular(self):
        """Test save_user with existing email that is regular account."""
        request = self.factory.post("/")
        user = User()
        form = Mock()
        form.cleaned_data = {"email": "existing@example.com"}

        existing_user = Mock()
        existing_user.socialaccount_set.exists.return_value = False

        with patch("footycollect.users.adapters.User.objects.filter") as mock_filter:
            mock_filter.return_value.exists.return_value = True
            with patch("footycollect.users.adapters.User.objects.get") as mock_get:
                mock_get.return_value = existing_user

                with pytest.raises(ValidationError) as context:
                    self.adapter.save_user(request, user, form, commit=True)

                assert "already registered" in str(context.value)

    def test_send_password_reset_mail_social_user(self):
        """Test send_password_reset_mail for social user."""
        request = self.factory.post("/")
        user = Mock()
        user.socialaccount_set.exists.return_value = True
        user.socialaccount_set.values_list.return_value = ["google"]

        with patch("footycollect.users.adapters.messages.error") as mock_error:
            self.adapter.send_password_reset_mail(request, "test@example.com", [user])

            mock_error.assert_called_once()
            assert "google" in str(mock_error.call_args[0][1])

    def test_send_password_reset_mail_regular_user(self):
        """Test send_password_reset_mail for regular user."""
        request = self.factory.post("/")
        user = Mock()
        user.socialaccount_set.exists.return_value = False

        with patch("footycollect.users.adapters.super") as mock_super:
            self.adapter.send_password_reset_mail(request, "test@example.com", [user])

            mock_super.assert_called_once()


class TestCustomSocialAccountAdapter(TestCase):
    """Test cases for CustomSocialAccountAdapter."""

    def setUp(self):
        """Set up test data."""
        self.adapter = CustomSocialAccountAdapter()
        self.factory = RequestFactory()

    def test_is_open_for_signup_true(self):
        """Test is_open_for_signup returns True when ACCOUNT_ALLOW_REGISTRATION is True."""
        allow_registration = True
        with patch("footycollect.users.adapters.settings.ACCOUNT_ALLOW_REGISTRATION", allow_registration):
            request = self.factory.get("/")
            sociallogin = Mock()
            result = self.adapter.is_open_for_signup(request, sociallogin)
            assert result is True

    def test_is_open_for_signup_false(self):
        """Test is_open_for_signup returns False when ACCOUNT_ALLOW_REGISTRATION is False."""
        allow_registration = False
        with patch("footycollect.users.adapters.settings.ACCOUNT_ALLOW_REGISTRATION", allow_registration):
            request = self.factory.get("/")
            sociallogin = Mock()
            result = self.adapter.is_open_for_signup(request, sociallogin)
            assert result is False

    def test_pre_social_login_existing_user(self):
        """Test pre_social_login with existing user."""
        request = self.factory.get("/")
        sociallogin = Mock()
        sociallogin.user = Mock()
        sociallogin.user.id = None
        sociallogin.user.email = "existing@example.com"
        sociallogin.account.extra_data = {"name": "John Doe"}

        existing_user = Mock()
        existing_user.name = ""
        existing_user.email = "existing@example.com"

        patch_get = patch("footycollect.users.adapters.User.objects.get", return_value=existing_user)
        patch_connect = patch.object(sociallogin, "connect")
        patch_success = patch("footycollect.users.adapters.messages.success")
        with patch_get, patch_connect as mock_connect, patch_success as mock_success:
            self.adapter.pre_social_login(request, sociallogin)

            assert existing_user.name == "John Doe"
            mock_connect.assert_called_once_with(request, existing_user)
            mock_success.assert_called_once()

    def test_pre_social_login_existing_user_with_name(self):
        """Test pre_social_login with existing user that already has name."""
        request = self.factory.get("/")
        sociallogin = Mock()
        sociallogin.user = Mock()
        sociallogin.user.id = None
        sociallogin.user.email = "existing@example.com"
        sociallogin.account.extra_data = {"name": "John Doe"}

        existing_user = Mock()
        existing_user.name = "Jane Doe"
        existing_user.email = "existing@example.com"
        with (
            patch("footycollect.users.adapters.User.objects.get") as mock_get,
            patch.object(sociallogin, "connect") as mock_connect,
            patch("footycollect.users.adapters.messages.success") as mock_success,
        ):
            mock_get.return_value = existing_user

            self.adapter.pre_social_login(request, sociallogin)

            assert existing_user.name == "Jane Doe"  # Should not change
            mock_connect.assert_called_once_with(request, existing_user)
            mock_success.assert_called_once()

    def test_pre_social_login_existing_user_first_last_name(self):
        """Test pre_social_login with existing user using first_name and last_name."""
        request = self.factory.get("/")
        sociallogin = Mock()
        sociallogin.user = Mock()
        sociallogin.user.id = None
        sociallogin.user.email = "existing@example.com"
        sociallogin.account.extra_data = {"first_name": "John", "last_name": "Doe"}

        existing_user = Mock()
        existing_user.name = ""
        existing_user.email = "existing@example.com"

        mock_get_patcher = patch("footycollect.users.adapters.User.objects.get")
        mock_connect_patcher = patch.object(sociallogin, "connect")
        mock_success_patcher = patch("footycollect.users.adapters.messages.success")
        mock_get = mock_get_patcher.start()
        mock_connect = mock_connect_patcher.start()
        mock_success = mock_success_patcher.start()
        try:
            mock_get.return_value = existing_user

            self.adapter.pre_social_login(request, sociallogin)

            assert existing_user.name == "John Doe"
            mock_connect.assert_called_once_with(request, existing_user)
            mock_success.assert_called_once()
        finally:
            mock_get_patcher.stop()
            mock_connect_patcher.stop()
            mock_success_patcher.stop()

    def test_pre_social_login_no_existing_user(self):
        """Test pre_social_login with no existing user."""
        request = self.factory.get("/")
        sociallogin = Mock()
        sociallogin.user = Mock()
        sociallogin.user.id = None
        sociallogin.user.email = "new@example.com"

        with patch("footycollect.users.adapters.User.objects.get") as mock_get:
            mock_get.side_effect = User.DoesNotExist()

            # Should not raise an exception
            self.adapter.pre_social_login(request, sociallogin)

    def test_pre_social_login_existing_user_id(self):
        """Test pre_social_login with user that already has id."""
        request = self.factory.get("/")
        sociallogin = Mock()
        sociallogin.user = Mock()
        sociallogin.user.id = 1

        # Should return early
        self.adapter.pre_social_login(request, sociallogin)

    def test_populate_user_with_name(self):
        """Test populate_user with name in data."""
        request = self.factory.get("/")
        sociallogin = Mock()
        data = {"name": "John Doe", "email": "john@example.com"}

        user = Mock()
        user.name = ""

        with patch("footycollect.users.adapters.super") as mock_super:
            mock_super.return_value.populate_user.return_value = user

            with patch("footycollect.users.adapters.User.objects.filter") as mock_filter:
                mock_filter.return_value.exists.return_value = False

                result = self.adapter.populate_user(request, sociallogin, data)

                assert result == user
                assert user.name == "John Doe"
                assert user.username == "john"

    def test_populate_user_with_first_last_name(self):
        """Test populate_user with first_name and last_name in data."""
        request = self.factory.get("/")
        sociallogin = Mock()
        data = {"first_name": "John", "last_name": "Doe", "email": "john@example.com"}

        user = Mock()
        user.name = ""

        with patch("footycollect.users.adapters.super") as mock_super:
            mock_super.return_value.populate_user.return_value = user

            with patch("footycollect.users.adapters.User.objects.filter") as mock_filter:
                mock_filter.return_value.exists.return_value = False

                result = self.adapter.populate_user(request, sociallogin, data)

                assert result == user
                assert user.name == "John Doe"
                assert user.username == "john"

    def test_populate_user_username_collision(self):
        """Test populate_user with username collision."""
        request = self.factory.get("/")
        sociallogin = Mock()
        data = {"name": "John Doe", "email": "john@example.com"}

        user = Mock()
        user.name = ""

        with patch("footycollect.users.adapters.super") as mock_super:
            mock_super.return_value.populate_user.return_value = user

            with patch("footycollect.users.adapters.User.objects.filter") as mock_filter:
                # First call returns True (username exists), second call returns False
                mock_filter.return_value.exists.side_effect = [True, False]

                result = self.adapter.populate_user(request, sociallogin, data)

                assert result == user
                assert user.name == "John Doe"
                assert user.username == "john1"

    def test_populate_user_no_email(self):
        """Test populate_user with no email in data."""
        request = self.factory.get("/")
        sociallogin = Mock()
        data = {"name": "John Doe"}

        user = Mock()
        user.name = ""

        with patch("footycollect.users.adapters.super") as mock_super:
            mock_super.return_value.populate_user.return_value = user

            result = self.adapter.populate_user(request, sociallogin, data)

            assert result == user
            assert user.name == "John Doe"
            # Username should not be set if no email
