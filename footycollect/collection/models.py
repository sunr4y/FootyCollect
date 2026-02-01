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
        update_fields = kwargs.get("update_fields")
        is_new = self.pk is None

        if not is_new:
            try:
                old_photo = Photo.objects.get(pk=self.pk)
                old_image = old_photo.image
            except Photo.DoesNotExist:
                old_image = None
        else:
            old_image = None

        super().save(*args, **kwargs)

        should_process = False
        if update_fields:
            if "image_avif" in update_fields:
                should_process = False
            elif "image" in update_fields:
                should_process = True
        elif (is_new and self.image) or (old_image != self.image and self.image):
            should_process = True

        if should_process and not self.image_avif:
            from .tasks import process_photo_to_avif

            process_photo_to_avif.delay(self.pk)

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
        if self.image_avif:
            # Check if the AVIF file actually exists
            try:
                if self.image_avif.storage.exists(self.image_avif.name):
                    return self.image_avif.url
            except (ValueError, AttributeError, NotImplementedError):
                # If storage doesn't support exists() or field is empty, fall back to original
                pass
        return self.image.url if self.image else ""

    def delete(self, *args, **kwargs):
        """Override delete to remove files from storage."""
        # Store file names before deletion
        image_name = self.image.name if self.image else None
        avif_name = self.image_avif.name if self.image_avif else None
        image_storage = self.image.storage if self.image else None
        avif_storage = self.image_avif.storage if self.image_avif else None

        # Call parent delete to remove from database
        super().delete(*args, **kwargs)

        # Remove files from storage
        if image_name and image_storage:
            try:
                if image_storage.exists(image_name):
                    image_storage.delete(image_name)
            except (OSError, NotImplementedError):
                pass

        if avif_name and avif_storage:
            try:
                if avif_storage.exists(avif_name):
                    avif_storage.delete(avif_name)
            except (OSError, NotImplementedError):
                pass


# Custom manager for BaseItem
class BaseItemManager(models.Manager):
    def public(self):
        return self.filter(is_private=False, is_draft=False)

    def private(self):
        return self.filter(is_private=True)

    def drafts(self):
        return self.filter(is_draft=True)


# Custom manager for MTI models (Jersey, Shorts, etc.)
class MTIManager(models.Manager):
    def public(self):
        return self.filter(base_item__is_private=False, base_item__is_draft=False)

    def private(self):
        return self.filter(base_item__is_private=True)

    def drafts(self):
        return self.filter(base_item__is_draft=True)


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

    # Item type choices for MTI
    ITEM_TYPE_CHOICES = [
        ("jersey", _("Jersey")),
        ("shorts", _("Shorts")),
        ("outerwear", _("Outerwear")),
        ("tracksuit", _("Tracksuit")),
        ("pants", _("Pants")),
        ("other", _("Other")),
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

    # Core fields for MTI
    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
        help_text=_("Type of item"),
    )
    name = models.CharField(
        max_length=200,
        help_text=_("Name or title of the item"),
    )

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        help_text="User who owns this item",
        db_index=True,
    )
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, db_index=True)
    club = models.ForeignKey(Club, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
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
        db_index=True,
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
    is_processing_photos = models.BooleanField(default=False, db_index=True)
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

    # Manager
    objects = BaseItemManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["item_type"]),
            models.Index(fields=["club"]),
            models.Index(fields=["brand"]),
            models.Index(fields=["created_at"]),
            # Composite indexes for common query patterns
            models.Index(fields=["user", "item_type"], name="baseitem_user_item_type_idx"),
            models.Index(fields=["user", "is_private", "is_draft"], name="baseitem_user_visibility_idx"),
            models.Index(fields=["user", "created_at"], name="baseitem_user_created_idx"),
            models.Index(fields=["club", "season"], name="baseitem_club_season_idx"),
        ]

    def __str__(self):
        try:
            brand_name = self.brand.name if self.brand else "Unknown Brand"
        except (AttributeError, ValueError):
            brand_name = "Unknown Brand"

        try:
            club_name = self.club.name if self.club else "Unknown Club"
        except (AttributeError, ValueError):
            club_name = "Unknown Club"

        return f"{brand_name} {club_name} {self.get_item_type_display()}"

    def get_main_photo(self):
        main_photo = self.photos.order_by("order").first()
        return main_photo.get_image_url() if main_photo else "path/to/placeholder.jpg"

    def get_specific_item(self):
        """
        Get the specific item instance (Jersey, Shorts, etc.) associated with this BaseItem.
        """
        # Use a mapping to reduce return statements
        item_mappings = {
            "jersey": "jersey",
            "shorts": "shorts",
            "outerwear": "outerwear",
            "tracksuit": "tracksuit",
            "pants": "pants",
            "other": "otheritem",
        }

        attr_name = item_mappings.get(self.item_type)
        if attr_name and hasattr(self, attr_name):
            return getattr(self, attr_name)
        return None


class Size(models.Model):
    CATEGORY_CHOICES = [
        ("tops", "Tops"),
        ("bottoms", "Bottoms"),
        ("other", "Other"),
    ]
    name = models.CharField(max_length=20)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)

    def __str__(self):
        return self.name


class Jersey(models.Model):
    """
    Jersey model using Multi-Table Inheritance.

    This model has a OneToOneField relationship with BaseItem,
    containing only Jersey-specific fields.
    """

    base_item = models.OneToOneField(
        BaseItem,
        on_delete=models.CASCADE,
        related_name="jersey",
        primary_key=True,
    )

    # Jersey-specific fields
    kit = models.ForeignKey(Kit, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    size = models.ForeignKey(Size, on_delete=models.CASCADE, db_index=True)
    is_fan_version = models.BooleanField(default=True)
    is_signed = models.BooleanField(default=False)
    has_nameset = models.BooleanField(default=False)
    player_name = models.CharField(max_length=100, blank=True)
    number = models.PositiveIntegerField(null=True, blank=True)
    is_short_sleeve = models.BooleanField(default=True)

    objects = MTIManager()

    class Meta:
        indexes = [
            models.Index(fields=["size"], name="jersey_size_idx"),
            models.Index(fields=["kit"], name="jersey_kit_idx"),
        ]

    def __str__(self):
        return f"Jersey: {self.base_item}"

    def save(self, *args, **kwargs):
        # Ensure the base_item has the correct item_type
        if not self.base_item.item_type:
            self.base_item.item_type = "jersey"
        # Auto-generate name using builder
        self.base_item.name = self.build_name()
        self.base_item.save()
        super().save(*args, **kwargs)

    def _build_base_name(self) -> str:
        """Build the base name (club + type)."""
        parts = []
        if self.base_item.club:
            parts.append(self.base_item.club.name)
        if self.kit and self.kit.type:
            parts.append(self.kit.type.name)
        return " ".join(parts) if parts else ""

    def _build_player_part(self) -> str:
        """Build the player name/number part."""
        if not (self.player_name or self.number):
            return ""
        if self.player_name and self.number:
            return f"{self.player_name}#{self.number}"
        if self.player_name:
            return self.player_name
        return f"#{self.number}"

    def _build_version_part(self) -> str:
        """Build the version part (Fan/Player Version)."""
        from django.utils.translation import gettext_lazy as _

        version = _("Fan Version") if self.is_fan_version else _("Player Version")
        return f" - {version}"

    def build_name(self) -> str:
        """
        Build the full name for the jersey following the pattern:

        CLUB_NAME + TYPE_K + SEASON + "-" + SIZE +
        ('-' + PLAYER_NAME#PLAYER_NUMBER if exists) +
        FAN_VERSION/PLAYER_VERSION + LONG_SLEEVE (if is_short_sleeve=False) +
        '-' + SIGNED (if is_signed=True)

        Example: "Real Betis Home 2020-21 - XS - Joaquin#17 - Player Version - Signed"

        This name is automatically saved to base_item.name when the jersey is saved.

        Returns:
            str: The constructed name for the jersey
        """
        from django.utils.translation import gettext_lazy as _

        name = self._build_base_name()
        if not name:
            return self.base_item.name

        if self.base_item.season:
            name += f" {self.base_item.season.year}"

        if self.size:
            name += f" - {self.size.name}"

        player_part = self._build_player_part()
        if player_part:
            name += f" - {player_part}"

        name += self._build_version_part()

        if not self.is_short_sleeve:
            name += f" {_('Long Sleeve')}"

        if self.is_signed:
            name += f" - {_('Signed')}"

        return name

    def get_display_name_with_type(self) -> str:
        """
        Get display name for detail view: CLUB_NAME + TYPE_K only.
        Used in detail view to show name + typek without size, season, version, etc.
        The season is displayed separately below the title.
        """
        parts = []
        if self.base_item.club:
            parts.append(self.base_item.club.name)
        if self.kit and self.kit.type:
            parts.append(self.kit.type.name)
        if not parts:
            return self.base_item.name
        return " ".join(parts)


class Shorts(models.Model):
    """
    Shorts model using Multi-Table Inheritance.
    """

    base_item = models.OneToOneField(
        BaseItem,
        on_delete=models.CASCADE,
        related_name="shorts",
        primary_key=True,
    )

    # Shorts-specific fields
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    number = models.PositiveIntegerField(null=True, blank=True)
    is_fan_version = models.BooleanField(default=True)

    def __str__(self):
        return f"Shorts: {self.base_item}"

    def save(self, *args, **kwargs):
        if not self.base_item.item_type:
            self.base_item.item_type = "shorts"
            self.base_item.save()
        super().save(*args, **kwargs)


class Outerwear(models.Model):
    """
    Outerwear model using Multi-Table Inheritance.
    """

    TYPE_CHOICES = [
        ("hoodie", "Hoodie"),
        ("jacket", "Jacket"),
        ("windbreaker", "Windbreaker"),
        ("crewneck", "Crewneck"),
    ]

    base_item = models.OneToOneField(
        BaseItem,
        on_delete=models.CASCADE,
        related_name="outerwear",
        primary_key=True,
    )

    # Outerwear-specific fields
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    size = models.ForeignKey(Size, on_delete=models.CASCADE)

    def __str__(self):
        return f"Outerwear: {self.base_item}"

    def save(self, *args, **kwargs):
        if not self.base_item.item_type:
            self.base_item.item_type = "outerwear"
            self.base_item.save()
        super().save(*args, **kwargs)


class Tracksuit(models.Model):
    """
    Tracksuit model using Multi-Table Inheritance.
    """

    base_item = models.OneToOneField(
        BaseItem,
        on_delete=models.CASCADE,
        related_name="tracksuit",
        primary_key=True,
    )

    # Tracksuit-specific fields
    size = models.ForeignKey(Size, on_delete=models.CASCADE)

    def __str__(self):
        return f"Tracksuit: {self.base_item}"

    def save(self, *args, **kwargs):
        if not self.base_item.item_type:
            self.base_item.item_type = "tracksuit"
            self.base_item.save()
        super().save(*args, **kwargs)


class Pants(models.Model):
    """
    Pants model using Multi-Table Inheritance.
    """

    base_item = models.OneToOneField(
        BaseItem,
        on_delete=models.CASCADE,
        related_name="pants",
        primary_key=True,
    )

    # Pants-specific fields
    size = models.ForeignKey(Size, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Pants"

    def __str__(self):
        return f"Pants: {self.base_item}"

    def save(self, *args, **kwargs):
        if not self.base_item.item_type:
            self.base_item.item_type = "pants"
            self.base_item.save()
        super().save(*args, **kwargs)


class OtherItem(models.Model):
    """
    OtherItem model using Multi-Table Inheritance.
    """

    TYPE_CHOICES = [
        ("pin", "Pin"),
        ("hat", "Hat"),
        ("cap", "Cap"),
        ("socks", "Socks"),
        ("other", "Other"),
    ]

    base_item = models.OneToOneField(
        BaseItem,
        on_delete=models.CASCADE,
        related_name="otheritem",
        primary_key=True,
    )

    # OtherItem-specific fields
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    def __str__(self):
        return f"Other Item: {self.base_item}"

    def save(self, *args, **kwargs):
        if not self.base_item.item_type:
            self.base_item.item_type = "other"
            self.base_item.save()
        super().save(*args, **kwargs)
