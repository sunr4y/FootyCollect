from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML
from crispy_forms.layout import Layout
from django import forms
from django.contrib.auth import forms as admin_forms
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):  # type: ignore[name-defined]
        model = User


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):  # type: ignore[name-defined]
        model = User
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "name",
            "biography",
            "location",
            "avatar",
            "favourite_teams",
            "is_private",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_private"].label = ""  # Remove default label
        self.fields["is_private"].widget = forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "role": "switch",
            },
        )
        self.helper = FormHelper(self)
        self.helper.form_tag = False  # Don't render form tag
        self.helper.layout = Layout(
            "name",
            "biography",
            "location",
            "avatar",
            "favourite_teams",
            HTML("""
                <div class="form-check form-switch mb-3">
                    <input type="checkbox" name="is_private"
                           class="form-check-input"
                           role="switch"
                           id="id_is_private"
                           {% if form.is_private.value %}checked{% endif %}>
                    <label class="form-check-label" for="id_is_private">
                        Set profile as private
                        <br>
                        <small class="text-muted">
                            Your collection will only be visible to you
                        </small>
                    </label>
                </div>
            """),
        )
