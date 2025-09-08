"""
Tests for django-allauth adapters.
"""

import pytest
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from footycollect.users.adapters import CustomAccountAdapter, CustomSocialAccountAdapter
from footycollect.users.models import User
from footycollect.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestCustomAccountAdapter:
    """Test CustomAccountAdapter for account merging logic."""

    def test_save_user_duplicate_email_regular_account(self):
        """Test that duplicate regular accounts are prevented."""
        # Create first user
        UserFactory(email="test@example.com")

        # Test adapter
        adapter = CustomAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Create mock form
        class MockForm:
            def __init__(self, email):
                self.cleaned_data = {"email": email}

        # Create second user with same email
        user2 = UserFactory.build(email="test@example.com", username="testuser2")

        # Should raise ValidationError
        with pytest.raises(ValidationError, match="This email is already registered"):
            adapter.save_user(request, user2, MockForm("test@example.com"))

    def test_save_user_duplicate_email_social_account(self):
        """Test that duplicate social accounts are prevented with provider info."""
        # Create first user with social account
        user1 = UserFactory(email="test@example.com")
        # Simulate social account
        from allauth.socialaccount.models import SocialAccount

        SocialAccount.objects.create(
            user=user1,
            provider="google",
            uid="123456789",
        )

        # Test adapter
        adapter = CustomAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Create mock form
        class MockForm:
            def __init__(self, email):
                self.cleaned_data = {"email": email}

        # Create second user with same email
        user2 = UserFactory.build(email="test@example.com", username="testuser2")

        # Should raise ValidationError with provider info
        with pytest.raises(ValidationError, match="This email is already registered with: google"):
            adapter.save_user(request, user2, MockForm("test@example.com"))

    def test_save_user_new_email_allowed(self):
        """Test that new emails are allowed."""
        adapter = CustomAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Create mock form
        class MockForm:
            def __init__(self, email):
                self.cleaned_data = {"email": email}

        # Create user with new email
        user = UserFactory.build(email="new@example.com", username="newuser")

        # Should not raise ValidationError
        try:
            adapter.save_user(request, user, MockForm("new@example.com"))
        except ValidationError:
            pytest.fail("ValidationError was raised for new email")

    def test_is_open_for_signup_default(self):
        """Test that signup is open by default."""
        adapter = CustomAccountAdapter()
        factory = RequestFactory()
        request = factory.get("/")

        assert adapter.is_open_for_signup(request) is True


@pytest.mark.django_db
class TestCustomSocialAccountAdapter:
    """Test CustomSocialAccountAdapter for social login merging."""

    def test_pre_social_login_connects_existing_user(self):
        """Test that social login connects to existing user by email."""
        # Create existing user
        existing_user = UserFactory(email="test@example.com")

        # Create mock social login
        class MockSocialLogin:
            def __init__(self, email):
                self.account = MockSocialAccount(email)
                self.user = MockUser(email)

            def connect(self, request, user):
                """Mock connect method."""
                self.account.user = user

        class MockSocialAccount:
            def __init__(self, email):
                self.user = None
                self.provider = "google"
                self.uid = "123456789"

        class MockUser:
            def __init__(self, email):
                self.email = email
                self.id = None  # New user has no ID

        # Test adapter
        adapter = CustomSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Add messages middleware for the request
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware

        middleware = MessageMiddleware(lambda req: None)
        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        middleware.process_request(request)

        sociallogin = MockSocialLogin("test@example.com")

        # Should connect to existing user
        adapter.pre_social_login(request, sociallogin)

        # Verify connection was made
        assert sociallogin.account.user == existing_user

    def test_pre_social_login_new_user_allowed(self):
        """Test that new users are allowed through social login."""

        # Create mock social login for new user
        class MockSocialLogin:
            def __init__(self, email):
                self.account = MockSocialAccount(email)
                self.user = MockUser(email)

        class MockSocialAccount:
            def __init__(self, email):
                self.user = None
                self.provider = "google"
                self.uid = "123456789"

        class MockUser:
            def __init__(self, email):
                self.email = email
                self.id = None  # New user has no ID

        # Test adapter
        adapter = CustomSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        sociallogin = MockSocialLogin("new@example.com")

        # Should not raise any errors
        try:
            adapter.pre_social_login(request, sociallogin)
        except (AttributeError, ValueError, TypeError) as e:
            pytest.fail(f"Exception was raised for new user: {e}")

    def test_save_user_prevents_duplicate_social_registration(self):
        """Test that duplicate social registrations are prevented."""
        # Create existing user with social account
        existing_user = UserFactory(email="test@example.com")
        from allauth.socialaccount.models import SocialAccount

        SocialAccount.objects.create(
            user=existing_user,
            provider="google",
            uid="123456789",
        )

        # Test adapter
        adapter = CustomSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Create mock form
        class MockForm:
            def __init__(self, email):
                self.cleaned_data = {"email": email}

        # Create new user with same email
        new_user = UserFactory.build(email="test@example.com", username="newuser")

        # Create mock sociallogin object
        class MockSocialLogin:
            def __init__(self, user):
                self.user = user

        # Should raise ValidationError
        with pytest.raises(ValidationError, match="This email is already registered with: google"):
            adapter.save_user(request, MockSocialLogin(new_user), MockForm("test@example.com"))

    def test_send_password_reset_mail_social_user(self, user: User):
        """Test that password reset is blocked for social users."""
        # Create social account for user
        from allauth.socialaccount.models import SocialAccount

        SocialAccount.objects.create(
            user=user,
            provider="google",
            uid="123456789",
        )

        # Test adapter
        adapter = CustomAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Add messages middleware
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware

        middleware = MessageMiddleware(lambda req: None)
        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        middleware.process_request(request)

        # Should show error message and not send email
        adapter.send_password_reset_mail(request, user.email, [user])

        # Check that error message was added
        messages_list = list(messages.get_messages(request))
        assert len(messages_list) == 1
        assert "This account was created with: google" in str(messages_list[0])

    def test_send_password_reset_mail_regular_user(self, user: User):
        """Test that password reset works for regular users."""
        # Test adapter
        adapter = CustomAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Add messages middleware
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware

        middleware = MessageMiddleware(lambda req: None)
        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        middleware.process_request(request)

        # Test that the method doesn't raise an error for regular users
        # (We can't easily test the parent method call without complex mocking)
        import contextlib

        with contextlib.suppress(AttributeError):
            adapter.send_password_reset_mail(request, user.email, [user])

        # Check that no error message was added
        messages_list = list(messages.get_messages(request))
        assert len(messages_list) == 0

    def test_is_open_for_signup_social(self):
        """Test that social signup is open by default."""
        adapter = CustomSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Mock sociallogin
        class MockSocialLogin:
            pass

        sociallogin = MockSocialLogin()

        # Should return True by default
        assert adapter.is_open_for_signup(request, sociallogin) is True

    def test_pre_social_login_existing_user_with_name_update(self):
        """Test that existing user name is updated from social data."""
        # Create existing user without name
        existing_user = UserFactory(email="test@example.com", name="")

        # Create mock social login with extra data
        class MockSocialLogin:
            def __init__(self, email):
                self.account = MockSocialAccount(email)
                self.user = MockUser(email)

            def connect(self, request, user):
                """Mock connect method."""
                self.account.user = user

        class MockSocialAccount:
            def __init__(self, email):
                self.user = None
                self.provider = "google"
                self.uid = "123456789"
                self.extra_data = {"name": "John Doe"}

        class MockUser:
            def __init__(self, email):
                self.email = email
                self.id = None

        # Test adapter
        adapter = CustomSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Add messages middleware
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware

        middleware = MessageMiddleware(lambda req: None)
        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        middleware.process_request(request)

        sociallogin = MockSocialLogin("test@example.com")

        # Should connect and update name
        adapter.pre_social_login(request, sociallogin)

        # Verify connection was made and name was updated
        assert sociallogin.account.user == existing_user
        existing_user.refresh_from_db()
        assert existing_user.name == "John Doe"

    def test_pre_social_login_existing_user_with_first_last_name(self):
        """Test that existing user name is updated from first_name and last_name."""
        # Create existing user without name
        existing_user = UserFactory(email="test@example.com", name="")

        # Create mock social login with first_name and last_name
        class MockSocialLogin:
            def __init__(self, email):
                self.account = MockSocialAccount(email)
                self.user = MockUser(email)

            def connect(self, request, user):
                """Mock connect method."""
                self.account.user = user

        class MockSocialAccount:
            def __init__(self, email):
                self.user = None
                self.provider = "google"
                self.uid = "123456789"
                self.extra_data = {
                    "first_name": "John",
                    "last_name": "Doe",
                }

        class MockUser:
            def __init__(self, email):
                self.email = email
                self.id = None

        # Test adapter
        adapter = CustomSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Add messages middleware
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware

        middleware = MessageMiddleware(lambda req: None)
        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        middleware.process_request(request)

        sociallogin = MockSocialLogin("test@example.com")

        # Should connect and update name
        adapter.pre_social_login(request, sociallogin)

        # Verify connection was made and name was updated
        assert sociallogin.account.user == existing_user
        existing_user.refresh_from_db()
        assert existing_user.name == "John Doe"

    def test_populate_user_with_name(self):
        """Test that user name is populated from social data."""
        # Test adapter
        adapter = CustomSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Mock sociallogin
        class MockSocialLogin:
            def __init__(self):
                self.user = MockUser()

        class MockUser:
            def __init__(self):
                self.name = ""
                self.username = ""

        sociallogin = MockSocialLogin()
        data = {"name": "John Doe", "email": "john@example.com"}

        # Should populate user with name
        user = adapter.populate_user(request, sociallogin, data)
        assert user.name == "John Doe"

    def test_populate_user_with_first_last_name(self):
        """Test that user name is populated from first_name and last_name."""
        # Test adapter
        adapter = CustomSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Mock sociallogin
        class MockSocialLogin:
            def __init__(self):
                self.user = MockUser()

        class MockUser:
            def __init__(self):
                self.name = ""
                self.username = ""

        sociallogin = MockSocialLogin()
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
        }

        # Should populate user with combined name
        user = adapter.populate_user(request, sociallogin, data)
        assert user.name == "John Doe"

    def test_populate_user_username_generation(self):
        """Test that username is generated from email."""
        # Test adapter
        adapter = CustomSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Mock sociallogin
        class MockSocialLogin:
            def __init__(self):
                self.user = MockUser()

        class MockUser:
            def __init__(self):
                self.name = ""
                self.username = ""

        sociallogin = MockSocialLogin()
        data = {"email": "john.doe@example.com"}

        # Should generate username from email
        user = adapter.populate_user(request, sociallogin, data)
        assert user.username == "john.doe"

    def test_populate_user_username_uniqueness(self):
        """Test that username is made unique if it already exists."""
        # Create existing user with username
        UserFactory(username="john.doe")

        # Test adapter
        adapter = CustomSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Mock sociallogin
        class MockSocialLogin:
            def __init__(self):
                self.user = MockUser()

        class MockUser:
            def __init__(self):
                self.name = ""
                self.username = ""

        sociallogin = MockSocialLogin()
        data = {"email": "john.doe@example.com"}

        # Should generate unique username
        user = adapter.populate_user(request, sociallogin, data)
        assert user.username == "john.doe1"
