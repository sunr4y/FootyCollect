from django.contrib.auth import get_user_model
from django.test import TestCase

from footycollect.core.models import Club
from footycollect.users.forms import (
    UserAdminChangeForm,
    UserAdminCreationForm,
    UserSignupForm,
    UserSocialSignupForm,
    UserUpdateForm,
)

User = get_user_model()

# Constants for test values
TEST_PASSWORD = "testpass123"


class TestUserAdminChangeForm(TestCase):
    """Test cases for UserAdminChangeForm."""

    def test_user_admin_change_form_meta(self):
        """Test UserAdminChangeForm Meta class."""
        form = UserAdminChangeForm()
        assert form.Meta.model == User

    def test_user_admin_change_form_inheritance(self):
        """Test UserAdminChangeForm inheritance."""
        from django.contrib.auth import forms as admin_forms

        assert issubclass(UserAdminChangeForm, admin_forms.UserChangeForm)


class TestUserAdminCreationForm(TestCase):
    """Test cases for UserAdminCreationForm."""

    def test_user_admin_creation_form_meta(self):
        """Test UserAdminCreationForm Meta class."""
        form = UserAdminCreationForm()
        assert form.Meta.model == User

    def test_user_admin_creation_form_inheritance(self):
        """Test UserAdminCreationForm inheritance."""
        from django.contrib.auth import forms as admin_forms

        assert issubclass(UserAdminCreationForm, admin_forms.UserCreationForm)

    def test_user_admin_creation_form_error_messages(self):
        """Test UserAdminCreationForm error messages."""
        form = UserAdminCreationForm()
        assert "username" in form.Meta.error_messages
        assert form.Meta.error_messages["username"]["unique"] == "This username has already been taken."

    def test_user_admin_creation_form_valid_data(self):
        """Test UserAdminCreationForm with valid data."""
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password1": "testpass123",
            "password2": "testpass123",
        }
        form = UserAdminCreationForm(data=form_data)
        assert form.is_valid()

    def test_user_admin_creation_form_invalid_data(self):
        """Test UserAdminCreationForm with invalid data."""
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password1": "testpass123",
            "password2": "differentpass",
        }
        form = UserAdminCreationForm(data=form_data)
        assert not form.is_valid()


class TestUserSignupForm(TestCase):
    """Test cases for UserSignupForm."""

    def test_user_signup_form_inheritance(self):
        """Test UserSignupForm inheritance."""
        from allauth.account.forms import SignupForm

        assert issubclass(UserSignupForm, SignupForm)


class TestUserSocialSignupForm(TestCase):
    """Test cases for UserSocialSignupForm."""

    def test_user_social_signup_form_inheritance(self):
        """Test UserSocialSignupForm inheritance."""
        from allauth.socialaccount.forms import SignupForm as SocialSignupForm

        assert issubclass(UserSocialSignupForm, SocialSignupForm)


class TestUserUpdateForm(TestCase):
    """Test cases for UserUpdateForm."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.club = Club.objects.create(name="FC Barcelona")

    def test_user_update_form_meta(self):
        """Test UserUpdateForm Meta class."""
        form = UserUpdateForm()
        assert form.Meta.model == User
        expected_fields = [
            "name",
            "biography",
            "location",
            "avatar",
            "favourite_teams",
            "is_private",
        ]
        assert form.Meta.fields == expected_fields

    def test_user_update_form_init(self):
        """Test UserUpdateForm __init__ method."""
        form = UserUpdateForm()

        # Check is_private field configuration
        assert form.fields["is_private"].label == ""
        assert isinstance(form.fields["is_private"].widget, form.fields["is_private"].widget.__class__)

        # Check widget attributes
        widget_attrs = form.fields["is_private"].widget.attrs
        assert widget_attrs["class"] == "form-check-input"
        assert widget_attrs["role"] == "switch"

    def test_user_update_form_helper_configuration(self):
        """Test UserUpdateForm helper configuration."""
        form = UserUpdateForm()

        # Check helper configuration
        assert not form.helper.form_tag
        assert form.helper.layout is not None

    def test_user_update_form_valid_data(self):
        """Test UserUpdateForm with valid data."""
        form_data = {
            "name": "John Doe",
            "biography": "Test biography",
            "location": "Test City",
            "favourite_teams": [self.club.id],
            "is_private": True,
        }
        form = UserUpdateForm(data=form_data, instance=self.user)
        assert form.is_valid()

    def test_user_update_form_save(self):
        """Test UserUpdateForm save method."""
        form_data = {
            "name": "John Doe",
            "biography": "Test biography",
            "location": "Test City",
            "favourite_teams": [self.club.id],
            "is_private": True,
        }
        form = UserUpdateForm(data=form_data, instance=self.user)
        assert form.is_valid()

        updated_user = form.save()

        assert updated_user.name == "John Doe"
        assert updated_user.biography == "Test biography"
        assert updated_user.location == "Test City"
        assert updated_user.is_private
        assert self.club in updated_user.favourite_teams.all()

    def test_user_update_form_empty_data(self):
        """Test UserUpdateForm with empty data."""
        form = UserUpdateForm(data={}, instance=self.user)
        assert form.is_valid()

    def test_user_update_form_partial_data(self):
        """Test UserUpdateForm with partial data."""
        form_data = {
            "name": "John Doe",
            "is_private": False,
        }
        form = UserUpdateForm(data=form_data, instance=self.user)
        assert form.is_valid()

        updated_user = form.save()

        assert updated_user.name == "John Doe"
        assert not updated_user.is_private

    def test_user_update_form_favourite_teams_multiple(self):
        """Test UserUpdateForm with multiple favourite teams."""
        club2, _ = Club.objects.get_or_create(
            name="Test Club Unique",
            defaults={"slug": "test-club-unique", "country": "ES"},
        )

        form_data = {
            "name": "John Doe",
            "favourite_teams": [self.club.id, club2.id],
        }
        form = UserUpdateForm(data=form_data, instance=self.user)
        assert form.is_valid()

        updated_user = form.save()

        assert self.club in updated_user.favourite_teams.all()
        assert club2 in updated_user.favourite_teams.all()

    def test_user_update_form_favourite_teams_empty(self):
        """Test UserUpdateForm with empty favourite teams."""
        form_data = {
            "name": "John Doe",
            "favourite_teams": [],
        }
        form = UserUpdateForm(data=form_data, instance=self.user)
        assert form.is_valid()

        updated_user = form.save()

        assert updated_user.favourite_teams.count() == 0
