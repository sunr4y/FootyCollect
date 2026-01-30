from __future__ import annotations

import typing

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

if typing.TYPE_CHECKING:
    from allauth.socialaccount.models import SocialLogin
    from django.http import HttpRequest

    from footycollect.users.models import User

User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def save_user(
        self,
        request: HttpRequest,
        user: User,
        form: typing.Any,
        *,  # Force kwargs for boolean argument
        commit: bool = True,
    ) -> User:
        user = super().save_user(request, user, form, commit=False)
        email = form.cleaned_data.get("email")

        if User.objects.filter(email=email).exists():
            existing_user = User.objects.get(email=email)

            # Check if existing user has social accounts
            if existing_user.socialaccount_set.exists():
                providers = existing_user.socialaccount_set.values_list(
                    "provider",
                    flat=True,
                )
                msg = _(
                    "This email is already registered with: %(providers)s. Please login using that method.",
                )
                raise ValidationError(msg % {"providers": ", ".join(providers)})
            # Existing user is a regular account (not social)
            # This prevents duplicate regular accounts with same email
            msg = _(
                "This email is already registered. Please use a different email or try to login.",
            )
            raise ValidationError(msg)

        if commit:
            user.save()
        return user

    def send_password_reset_mail(
        self,
        request: HttpRequest,
        email: str,
        users: list[User],
    ) -> None:
        user = users[0]
        if user.socialaccount_set.exists():
            providers = user.socialaccount_set.values_list("provider", flat=True)
            msg = _(
                "This account was created with: %(providers)s. Please use that method to login.",
            )
            messages.error(request, msg % {"providers": ", ".join(providers)})
            return
        super().send_password_reset_mail(request, email, users)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
    ) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def pre_social_login(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
    ) -> None:
        user = sociallogin.user
        if user.id:
            return

        try:
            existing_user = User.objects.get(email=user.email)

            # Update user info from social account if empty
            if not existing_user.name:
                if name := sociallogin.account.extra_data.get("name"):
                    existing_user.name = name
                elif first_name := sociallogin.account.extra_data.get("first_name"):
                    existing_user.name = first_name
                    if last_name := sociallogin.account.extra_data.get("last_name"):
                        existing_user.name += f" {last_name}"
                existing_user.save()

            sociallogin.connect(request, existing_user)
            msg = _(
                "Social account linked to %(email)s. You can now login using both methods.",
            )
            messages.success(request, msg % {"email": existing_user.email})
        except User.DoesNotExist:
            pass

    def populate_user(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
        data: dict[str, typing.Any],
    ) -> User:
        """
        Populates user information from social provider info.

        See: https://docs.allauth.org/en/latest/socialaccount/advanced.html#creating-and-populating-user-instances
        """
        user = super().populate_user(request, sociallogin, data)
        if not user.name:
            if name := data.get("name"):
                user.name = name
            elif first_name := data.get("first_name"):
                user.name = first_name
                if last_name := data.get("last_name"):
                    user.name += f" {last_name}"

        # Obtain the email from the user
        if email := data.get("email"):
            # Extract the part of the email before the @
            username = email.split("@")[0]

            # Ensure the username is unique
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user.username = username
        return user
