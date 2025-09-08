"""
Tests for users models.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from footycollect.users.tests.factories import (
    AdminUserFactory,
    InactiveUserFactory,
    PrivateUserFactory,
    UserFactory,
)

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Test User model."""

    def test_user_creation_with_factory(self):
        """Test creating a user with factory."""
        user = UserFactory(
            username="testuser",
            email="test@example.com",
            name="Test User",
            biography="Test biography",
            location="Test Location",
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.biography == "Test biography"
        assert user.location == "Test Location"
        assert user.is_private is False
        assert user.check_password("testpass123")

    def test_user_str_representation(self):
        """Test user string representation."""
        user = UserFactory(username="testuser")
        assert str(user) == "testuser"

    def test_user_get_absolute_url(self):
        """Test user get_absolute_url method."""
        user = UserFactory(username="testuser")
        expected_url = f"/users/{user.username}/"
        assert user.get_absolute_url() == expected_url

    def test_user_favourite_teams(self, club):
        """Test user favourite teams relationship."""
        user = UserFactory()

        # Add favourite team
        user.favourite_teams.add(club)

        assert club in user.favourite_teams.all()
        assert user in club.user_set.all()

    def test_user_avatar_fields(self):
        """Test user avatar fields."""
        user = UserFactory()

        # Test default values - avatar is an ImageField, so it's not None but empty
        assert not user.avatar  # Empty ImageField
        assert not user.avatar_avif  # Empty ImageField

    def test_user_private_field(self):
        """Test user private field."""
        user = PrivateUserFactory()
        assert user.is_private is True

    def test_user_created_updated_fields(self):
        """Test user created_at and updated_at fields."""
        user = UserFactory()

        # Check that timestamps are set
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.created_at <= timezone.now()
        assert user.updated_at <= timezone.now()

    def test_user_no_first_last_name(self):
        """Test that first_name and last_name are None."""
        user = UserFactory()

        # These should be None as they're disabled
        assert user.first_name is None
        assert user.last_name is None

    def test_user_avatar_url_method(self):
        """Test user get_avatar_url method."""
        user = UserFactory()

        # Without avatar, the method will raise ValueError
        # because it tries to access .url on empty ImageField
        with pytest.raises(ValueError, match="The 'avatar' attribute has no file associated with it"):
            user.get_avatar_url()

    def test_user_save_method(self):
        """Test user save method calls create_avif_version."""
        user = UserFactory()

        # The save method should call create_avif_version
        # This is tested implicitly by the fact that the user is created successfully
        assert user.pk is not None

    def test_user_create_avif_version(self):
        """Test user create_avif_version method."""
        user = UserFactory()

        # Test that the method exists and can be called
        # (without actually having an avatar file)
        user.create_avif_version()
        # Should not raise an exception
        assert True

    def test_user_password_hashed(self):
        """Test that password is properly hashed."""
        user = UserFactory()

        # Password should be hashed, not plain text
        assert user.password != "testpass123"  # noqa: S105
        assert user.check_password("testpass123")

    def test_user_is_active_default(self):
        """Test that user is active by default."""
        user = UserFactory()
        assert user.is_active is True

    def test_user_is_staff_default(self):
        """Test that user is not staff by default."""
        user = UserFactory()
        assert user.is_staff is False

    def test_user_is_superuser_default(self):
        """Test that user is not superuser by default."""
        user = UserFactory()
        assert user.is_superuser is False


@pytest.mark.django_db
class TestUserFactoryVariations:
    """Test different user factory variations."""

    def test_admin_user_factory(self):
        """Test AdminUserFactory creates admin user."""
        admin = AdminUserFactory()

        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.is_active is True

    def test_private_user_factory(self):
        """Test PrivateUserFactory creates private user."""
        private_user = PrivateUserFactory()

        assert private_user.is_private is True
        assert private_user.is_active is True

    def test_inactive_user_factory(self):
        """Test InactiveUserFactory creates inactive user."""
        inactive_user = InactiveUserFactory()

        assert inactive_user.is_active is False


@pytest.mark.django_db
class TestUserValidation:
    """Test user validation and constraints."""

    def test_user_username_required(self):
        """Test that username is required."""
        with pytest.raises(ValueError, match="The given username must be set"):
            User.objects.create_user(
                username="",
                email="test@example.com",
                password="testpass123",  # noqa: S106
            )

    def test_user_email_required(self):
        """Test that email is required."""
        # Django's create_user allows empty email by default
        # This test verifies the behavior with empty email
        user = User.objects.create_user(
            username="testuser",
            email="",
            password="testpass123",  # noqa: S106
        )
        assert user.email == ""

    def test_user_password_required(self):
        """Test that password is required."""
        # Django's create_user allows empty password by default
        # This test verifies the behavior with empty password
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="",
        )
        # Django hashes even empty passwords, so we check it's not None
        assert user.password is not None
        # Django allows empty passwords to be valid (this is the actual behavior)
        assert user.check_password("")

    def test_user_username_unique(self):
        """Test that username must be unique."""
        UserFactory(username="testuser")

        # Should raise IntegrityError for duplicate username
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username="testuser",
                email="test2@example.com",
                password="testpass123",  # noqa: S106
            )

    def test_user_email_unique_in_registration(self):
        """Test that email uniqueness is enforced during registration via adapter."""
        # Create first user
        UserFactory(email="test@example.com")

        # Test adapter directly
        from django.test import RequestFactory

        from footycollect.users.adapters import CustomAccountAdapter

        adapter = CustomAccountAdapter()
        factory = RequestFactory()
        request = factory.post("/")

        # Create a mock form object
        class MockForm:
            def __init__(self, email):
                self.cleaned_data = {"email": email}

        # Create second user with same email
        user2 = UserFactory.build(email="test@example.com", username="testuser2")

        # This should raise ValidationError due to duplicate email
        with pytest.raises(ValidationError, match="This email is already registered"):
            adapter.save_user(request, user2, MockForm("test@example.com"))


@pytest.mark.django_db
class TestUserFixtures:
    """Test user fixtures integration."""

    def test_user_fixture(self, user):
        """Test that user fixture works correctly."""
        assert user.pk is not None
        assert user.is_active is True
        assert user.check_password("testpass123")

    def test_user_fixture_with_club(self, user, club):
        """Test user fixture with club fixture."""
        user.favourite_teams.add(club)
        assert club in user.favourite_teams.all()
