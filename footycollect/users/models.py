from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from footycollect.core.models import Team


class User(AbstractUser):
    """
    Default custom user model for footycollect.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    biography = models.TextField(_("Biography"), blank=True)
    location = models.CharField(_("Location"), max_length=100, blank=True)
    avatar = models.ImageField(_("Avatar"), upload_to="avatars/", blank=True)
    favourite_teams = models.ManyToManyField(Team, blank=True)

    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})
