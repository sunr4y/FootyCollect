import uuid
from pathlib import Path

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from footycollect.core.models import Club
from footycollect.core.utils.images import optimize_image
from footycollect.users.validators import validate_avatar


def avatar_file_name(instance, filename):
    # Get extension
    ext = Path(filename).suffix
    # Generate UUID-based filename
    new_name = f"{uuid.uuid4().hex[:10]}{ext}"
    return str(Path("avatars") / new_name)


class User(AbstractUser):
    """
    Default custom user model for footycollect.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    name = models.CharField(_("Name and last name"), blank=True, max_length=255)
    biography = models.TextField(_("Biography"), blank=True)
    location = models.CharField(_("Location"), max_length=100, blank=True)
    avatar = models.ImageField(
        _("Avatar"),
        upload_to=avatar_file_name,
        blank=True,
        validators=[validate_avatar],
    )
    avatar_avif = models.ImageField(upload_to="avatars_avif/", blank=True, null=True)
    favourite_teams = models.ManyToManyField(Club, blank=True)
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(
        _("Created at"),
        default=timezone.now,
        editable=False,
    )
    updated_at = models.DateTimeField(
        _("Updated at"),
        default=timezone.now,
        editable=False,
    )

    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.create_avif_version()

    def create_avif_version(self):
        if not self.avatar_avif and self.avatar:
            optimized = optimize_image(self.avatar)
            if optimized:
                self.avatar_avif.save(
                    optimized.name,
                    optimized,
                    save=False,
                )
                super().save(update_fields=["avatar_avif"])

    def get_avatar_url(self):
        return self.avatar_avif.url if self.avatar_avif else self.avatar.url
