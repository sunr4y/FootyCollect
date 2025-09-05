from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill
from taggit.models import Tag

from footycollect.core.models import Brand, Club, Competition, Kit, Season
from footycollect.core.utils.images import optimize_image


class Color(models.Model):
    """
    Model to represent colors using hexadecimal values.
    """

    name = models.CharField(max_length=100, unique=True)
    hex_value = models.CharField(
        max_length=7,
        default="#FF0000",
        help_text=_("Hexadecimal color value (e.g., #RRGGBB)."),
    )

    # Color map for default colors
    COLOR_MAP = {
        "WHITE": "#FFFFFF",  # rgb(255, 255, 255)
        "RED": "#FF0000",  # rgb(255, 0, 0)
        "BLUE": "#0000FF",  # rgb(0, 0, 255)
        "BLACK": "#000000",  # rgb(0, 0, 0)
        "YELLOW": "#FFFF00",  # rgb(255, 255, 0)
        "GREEN": "#008000",  # rgb(0, 128, 0)
        "SKY_BLUE": "#87CEEB",  # rgb(135, 206, 235)
        "NAVY": "#000080",  # rgb(0, 0, 128)
        "ORANGE": "#FFA500",  # rgb(255, 165, 0)
        "GRAY": "#808080",  # rgb(128, 128, 128)
        "CLARET": "#7F1734",  # rgb(127, 23, 52)
        "PURPLE": "#800080",  # rgb(128, 0, 128)
        "PINK": "#FFC0CB",  # rgb(255, 192, 203)
        "BROWN": "#964B00",  # rgb(150, 75, 0)
        "GOLD": "#BFAB40",  # rgb(191, 171, 64)
        "SILVER": "#C0C0C0",  # rgb(192, 192, 192)
        "OFF_WHITE": "#F5F5F5",  # rgb(245, 245, 245)
    }

    def __str__(self):
        return self.name


class Photo(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")
    image = models.ImageField(upload_to="item_photos/")
    image_avif = models.ImageField(upload_to="item_photos_avif/", blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    # Temporary field to track orphaned photos
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, null=True)

    # Thumbnail
    thumbnail = ImageSpecField(
        source="image",
        processors=[ResizeToFill(100, 100)],
        format="JPEG",
        options={"quality": 75},
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Photo {self.order} of {self.content_object}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.create_avif_version()

    def create_avif_version(self):
        if not self.image_avif and self.image:
            optimized = optimize_image(self.image)
            if optimized:
                self.image_avif.save(
                    optimized.name,
                    optimized,
                    save=False,
                )
                super().save(update_fields=["image_avif"])

    def get_image_url(self):
        return self.image_avif.url if self.image_avif else self.image.url


class BaseItem(models.Model):
    COLOR_CHOICES = [
        ("WHITE", _("White")),
        ("RED", _("Red")),
        ("BLUE", _("Blue")),
        ("BLACK", _("Black")),
        ("YELLOW", _("Yellow")),
        ("GREEN", _("Green")),
        ("SKY_BLUE", _("Sky blue")),
        ("NAVY", _("Navy")),
        ("ORANGE", _("Orange")),
        ("GRAY", _("Gray")),
        ("CLARET", _("Claret")),
        ("PURPLE", _("Purple")),
        ("PINK", _("Pink")),
        ("BROWN", _("Brown")),
        ("GOLD", _("Gold")),
        ("SILVER", _("Silver")),
        ("OFF_WHITE", _("Off-white")),
    ]
    CONDITION_CHOICES = [
        ("BNWT", _("Brand New With Tags")),
        ("BNWOT", _("Brand New Without Tags")),
        ("EXCELLENT", _("Excellent")),
        ("VERY_GOOD", _("Very Good")),
        ("GOOD", _("Good")),
        ("FAIR", _("Fair")),
        ("POOR", _("Poor")),
    ]
    DESIGN_CHOICES = [
        ("PLAIN", _("Plain")),
        ("STRIPES", _("Stripes")),
        ("GRAPHIC", _("Graphic")),
        ("CHEST_BAND", _("Chest band")),
        ("CONTRASTING_SLEEVES", _("Contrasting sleeves")),
        ("PINSTRIPES", _("Pinstripes")),
        ("HOOPS", _("Hoops")),
        ("SINGLE_STRIPE", _("Single stripe")),
        ("HALF_AND_HALF", _("Half-and-half")),
        ("SASH", _("Sash")),
        ("CHEVRON", _("Chevron")),
        ("CHECKERS", _("Checkers")),
        ("GRADIENT", _("Gradient")),
        ("DIAGONAL", _("Diagonal")),
        ("CROSS", _("Cross")),
        ("QUARTERS", _("Quarters")),
    ]
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, help_text="User who owns this item")
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE, null=True, blank=True)
    competitions = models.ManyToManyField(
        Competition,
        blank=True,
        related_name="%(app_label)s_%(class)s_items",
        help_text="Competitions associated with this item",
    )
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    condition = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        default=10,
    )
    detailed_condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        blank=True,
    )
    description = models.TextField(blank=True)
    is_replica = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_draft = models.BooleanField(default=True)
    design = models.CharField(
        max_length=20,
        choices=DESIGN_CHOICES,
        blank=True,
    )
    main_color = models.ForeignKey(
        Color,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    secondary_colors = models.ManyToManyField(
        Color,
        blank=True,
        related_name="%(app_label)s_%(class)s_secondary",
    )
    country = CountryField(
        blank=True,
        null=True,
        help_text="The country associated with this item",
    )

    photos = GenericRelation(Photo)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.brand} {self.club} Item"

    def get_main_photo(self):
        main_photo = self.photos.order_by("order").first()
        return main_photo.get_image_url() if main_photo else "path/to/placeholder.jpg"


class Size(models.Model):
    CATEGORY_CHOICES = [
        ("tops", "Tops"),
        ("bottoms", "Bottoms"),
        ("other", "Other"),
    ]
    name = models.CharField(max_length=20)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)

    def __str__(self):
        return f"{self.get_category_display()} - {self.name}"


class Jersey(BaseItem):
    kit = models.ForeignKey(Kit, on_delete=models.CASCADE, null=True, blank=True)
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    is_fan_version = models.BooleanField(default=True)
    is_signed = models.BooleanField(default=False)
    has_nameset = models.BooleanField(default=False)
    player_name = models.CharField(max_length=100, blank=True)
    number = models.PositiveIntegerField(null=True, blank=True)
    is_short_sleeve = models.BooleanField(default=True)


class Shorts(BaseItem):
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    number = models.PositiveIntegerField(null=True, blank=True)
    is_fan_version = models.BooleanField(default=True)


class Outerwear(BaseItem):
    TYPE_CHOICES = [
        ("hoodie", "Hoodie"),
        ("jacket", "Jacket"),
        ("windbreaker", "Windbreaker"),
        ("crewneck", "Crewneck"),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    size = models.ForeignKey(Size, on_delete=models.CASCADE)


class Tracksuit(BaseItem):
    size = models.ForeignKey(Size, on_delete=models.CASCADE)


class Pants(BaseItem):
    size = models.ForeignKey(Size, on_delete=models.CASCADE)


class OtherItem(BaseItem):
    TYPE_CHOICES = [
        ("pin", "Pin"),
        ("hat", "Hat"),
        ("cap", "Cap"),
        ("socks", "Socks"),
        ("other", "Other"),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)


# Custom manager for BaseItem
class BaseItemManager(models.Manager):
    def public(self):
        return self.filter(is_private=False, is_draft=False)

    def private(self):
        return self.filter(is_private=True)

    def drafts(self):
        return self.filter(is_draft=True)


# Apply the custom manager to all models inheriting from BaseItem
for model in [Jersey, Shorts, Outerwear, Tracksuit, Pants, OtherItem]:
    model.add_to_class("objects", BaseItemManager())
