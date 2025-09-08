"""Module for all Form Tests."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.translation import gettext_lazy as _

from footycollect.users.forms import (
    UserAdminChangeForm,
    UserAdminCreationForm,
    UserSignupForm,
    UserSocialSignupForm,
    UserUpdateForm,
)
from footycollect.users.models import User


@pytest.mark.django_db
class TestUserAdminCreationForm:
    """Test class for all tests related to the UserAdminCreationForm."""

    def test_username_validation_error_msg(self, user: User):
        """
        Tests UserAdminCreation Form's unique validator functions correctly by testing:
            1) A new user with an existing username cannot be added.
            2) Only 1 error is raised by the UserCreation Form
            3) The desired error message is raised
        """
        # The user already exists, hence cannot be created.
        form = UserAdminCreationForm(
            {
                "username": user.username,
                "password1": user.password,
                "password2": user.password,
            },
        )

        assert not form.is_valid()
        assert len(form.errors) == 1
        assert "username" in form.errors
        assert form.errors["username"][0] == _("This username has already been taken.")

    def test_valid_user_creation(self):
        """Test that valid user creation works."""
        form = UserAdminCreationForm(
            {
                "username": "newuser",
                "password1": "testpass123",
                "password2": "testpass123",
            },
        )

        assert form.is_valid()
        user = form.save()
        assert user.username == "newuser"
        assert user.check_password("testpass123")

    def test_password_mismatch(self):
        """Test that password mismatch is caught."""
        form = UserAdminCreationForm(
            {
                "username": "newuser",
                "password1": "testpass123",
                "password2": "differentpass",
            },
        )

        assert not form.is_valid()
        assert "password2" in form.errors


@pytest.mark.django_db
class TestUserAdminChangeForm:
    """Test class for UserAdminChangeForm."""

    def test_form_initialization(self, user: User):
        """Test that form initializes correctly with user data."""
        form = UserAdminChangeForm(instance=user)

        assert form.instance == user
        assert form.initial["username"] == user.username
        assert form.initial["email"] == user.email

    def test_form_save(self, user: User):
        """Test that form saves changes correctly."""
        # Get all required fields from the form
        form = UserAdminChangeForm(instance=user)
        required_fields = {}

        # Fill in all required fields with current values
        for field_name, field in form.fields.items():
            if field.required:
                if hasattr(user, field_name):
                    required_fields[field_name] = getattr(user, field_name)
                elif field_name == "is_active":
                    required_fields[field_name] = True
                elif field_name in ("is_staff", "is_superuser"):
                    required_fields[field_name] = False

        # Update some fields
        required_fields.update(
            {
                "email": "newemail@example.com",
                "name": "New Name",
            },
        )

        form = UserAdminChangeForm(required_fields, instance=user)
        assert form.is_valid()
        updated_user = form.save()
        assert updated_user.email == "newemail@example.com"
        assert updated_user.name == "New Name"


@pytest.mark.django_db
class TestUserSignupForm:
    """Test class for UserSignupForm."""

    def test_form_inheritance(self):
        """Test that UserSignupForm inherits from SignupForm."""
        form = UserSignupForm()
        assert isinstance(form, UserSignupForm)

    def test_form_fields(self):
        """Test that form has expected fields."""
        form = UserSignupForm()
        # SignupForm typically has username, email, password1, password2
        expected_fields = ["username", "email", "password1", "password2"]
        for field in expected_fields:
            assert field in form.fields


@pytest.mark.django_db
class TestUserSocialSignupForm:
    """Test class for UserSocialSignupForm."""

    def test_form_inheritance(self):
        """Test that UserSocialSignupForm inherits from SocialSignupForm."""
        # UserSocialSignupForm requires sociallogin parameter
        from unittest.mock import Mock

        mock_sociallogin = Mock()
        form = UserSocialSignupForm(sociallogin=mock_sociallogin)
        assert isinstance(form, UserSocialSignupForm)


@pytest.mark.django_db
class TestUserUpdateForm:
    """Test class for UserUpdateForm."""

    def test_form_fields(self):
        """Test that form has correct fields."""
        form = UserUpdateForm()
        expected_fields = [
            "name",
            "biography",
            "location",
            "avatar",
            "favourite_teams",
            "is_private",
        ]
        for field in expected_fields:
            assert field in form.fields

    def test_form_initialization(self, user: User):
        """Test that form initializes correctly with user data."""
        form = UserUpdateForm(instance=user)

        assert form.instance == user
        assert form.initial["name"] == user.name
        assert form.initial["biography"] == user.biography
        assert form.initial["location"] == user.location
        assert form.initial["is_private"] == user.is_private

    def test_form_save(self, user: User):
        """Test that form saves changes correctly."""
        form = UserUpdateForm(
            {
                "name": "Updated Name",
                "biography": "Updated biography",
                "location": "Updated Location",
                "is_private": True,
            },
            instance=user,
        )

        assert form.is_valid()
        updated_user = form.save()
        assert updated_user.name == "Updated Name"
        assert updated_user.biography == "Updated biography"
        assert updated_user.location == "Updated Location"
        assert updated_user.is_private is True

    def test_avatar_upload(self, user: User):
        """Test that avatar upload works."""
        # Use real test image
        from pathlib import Path

        test_image_path = Path(__file__).parent / "test_images" / "test_avatar.jpg"

        with test_image_path.open("rb") as f:
            test_image = SimpleUploadedFile(
                "test_avatar.jpg",
                f.read(),
                content_type="image/jpeg",
            )

        form = UserUpdateForm(
            {
                "name": user.name,
                "biography": user.biography,
                "location": user.location,
                "is_private": user.is_private,
            },
            {
                "avatar": test_image,
            },
            instance=user,
        )

        assert form.is_valid()
        updated_user = form.save()
        assert updated_user.avatar.name is not None

    def test_is_private_widget_configuration(self):
        """Test that is_private field has correct widget configuration."""
        form = UserUpdateForm()

        is_private_field = form.fields["is_private"]
        assert is_private_field.label == ""  # Label should be empty
        assert hasattr(is_private_field.widget, "attrs")
        assert "class" in is_private_field.widget.attrs
        assert "role" in is_private_field.widget.attrs
        assert is_private_field.widget.attrs["class"] == "form-check-input"
        assert is_private_field.widget.attrs["role"] == "switch"

    def test_form_helper_configuration(self):
        """Test that form helper is configured correctly."""
        form = UserUpdateForm()

        assert hasattr(form, "helper")
        assert form.helper.form_tag is False  # Should not render form tag
        assert hasattr(form.helper, "layout")
