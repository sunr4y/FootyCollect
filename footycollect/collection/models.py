from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django_countries.fields import CountryField
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill
from taggit.models import Tag

from footycollect.core.models import Brand
from footycollect.core.models import Club
from footycollect.core.models import Competition
from footycollect.core.models import Kit
from footycollect.core.models import Season
from footycollect.core.utils.images import optimize_image


class Photo(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    item = GenericForeignKey("content_type", "object_id")
    image = models.ImageField(upload_to="item_photos/")
    image_avif = models.ImageField(upload_to="item_photos_avif/", blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField()

    # Thumbnail
    thumbnail = ImageSpecField(
        source="image",
        processors=[ResizeToFill(100, 100)],
        format="JPEG",
        options={"quality": 60},
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Photo {self.order} of {self.item}"

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
        ("BLACK", "Black"),
        ("BROWN", "Brown"),
        ("GREY", "Grey"),
        ("BEIGE", "Beige"),
        ("PINK", "Pink"),
        ("PURPLE", "Purple"),
        ("RED", "Red"),
        ("YELLOW", "Yellow"),
        ("BLUE", "Blue"),
        ("GREEN", "Green"),
        ("ORANGE", "Orange"),
        ("WHITE", "White"),
        ("SILVER", "Silver"),
        ("GOLD", "Gold"),
        ("VARIOUS", "Various"),
        ("KHAKI", "Khaki"),
        ("TURQUOISE", "Turquoise"),
        ("CREAM", "Cream"),
        ("APRICOT", "Apricot"),
        ("CORAL", "Coral"),
        ("BURGUNDY", "Burgundy"),
        ("ROSE", "Rose"),
        ("LILAC", "Lilac"),
        ("LIGHT_BLUE", "Light Blue"),
        ("NAVY", "Navy"),
        ("DARK_GREEN", "Dark Green"),
        ("MUSTARD", "Mustard"),
        ("MINT", "Mint"),
    ]
    CONDITION_CHOICES = [
        ("BNWT", "Brand New With Tags"),
        ("BNWOT", "Brand New Without Tags"),
        ("EXCELLENT", "Excellent"),
        ("VERY_GOOD", "Very Good"),
        ("GOOD", "Good"),
        ("FAIR", "Fair"),
        ("POOR", "Poor"),
    ]

    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    competition = models.ForeignKey(
        Competition,
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
    main_color = models.CharField(max_length=20, choices=COLOR_CHOICES)
    secondary_colors = ArrayField(
        models.CharField(max_length=20, choices=COLOR_CHOICES),
        size=3,
        blank=True,
        null=True,
    )
    country = CountryField(
        blank=True,
        null=True,
        help_text="The country associated with this item",
    )

    photos = GenericRelation(Photo)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.brand} {self.club} Item"

    def get_main_photo(self):
        main_photo = self.photos.order_by("order").first()
        return main_photo.get_image_url() if main_photo else "path/to/placeholder.jpg"


class Size(models.Model):
    CATEGORY_CHOICES = [
        ("shirt", "Shirt"),
        ("shorts", "Shorts"),
        ("jacket", "Jacket"),
    ]
    name = models.CharField(max_length=20)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)

    def __str__(self):
        return f"{self.get_category_display()} - {self.name}"


class Jersey(BaseItem):
    kit = models.ForeignKey(Kit, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    is_fan_version = models.BooleanField(default=True)
    is_signed = models.BooleanField(default=False)
    has_nameset = models.BooleanField(default=False)
    player_name = models.CharField(max_length=100, blank=True)
    number = models.PositiveIntegerField(null=True, blank=True)
    is_short_sleeve = models.BooleanField(default=True)


class Shorts(BaseItem):
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
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
