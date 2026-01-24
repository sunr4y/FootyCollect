from django.core.validators import RegexValidator
from django.db import models
from django_countries.fields import CountryField


class Season(models.Model):
    id_fka = models.IntegerField(null=True, blank=True)
    year = models.CharField(max_length=9, unique=True)
    first_year = models.CharField(max_length=4)
    second_year = models.CharField(max_length=4, blank=True)

    def __str__(self):
        return self.year


class TypeK(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=20,
        choices=[
            ("match", "Game"),
            ("prematch", "Pre-match"),
            ("preseason", "Pre-season"),
            ("training", "Training"),
            ("travel", "Travel"),
        ],
        default="match",
        db_index=True,
        help_text="Category for kit type classification. Note: 'jacket' items are handled as outerwear, not kits.",
    )
    is_goalkeeper = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if this is a goalkeeper kit (GK, Goalkeeper, Portero)",
    )

    class Meta:
        ordering = ["category", "is_goalkeeper", "name"]
        indexes = [
            models.Index(fields=["category", "is_goalkeeper"]),
        ]

    def __str__(self):
        return self.name

    def get_category_display_name(self):
        """Get user-friendly category name for frontend display."""
        category_names = {
            "match": "Game",
            "prematch": "Pre-match",
            "preseason": "Pre-season",
            "training": "Training",
            "travel": "Travel",
        }
        return category_names.get(self.category, self.category)


class Competition(models.Model):
    id_fka = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=150)
    logo = models.URLField(blank=True)
    logo_dark = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Club(models.Model):
    id_fka = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=500)
    country = CountryField(
        blank=True,
        null=True,
        help_text="The country associated with this item",
    )
    # Custom slug field that allows special characters
    # (The Django default slug field does not allow special characters)
    slug = models.CharField(
        unique=True,
        db_index=True,
        max_length=150,
        validators=[
            RegexValidator(
                regex=r"^[-a-zA-Z0-9_ăâîșțĂÂÎȘȚ]+$",
                message="Enter a valid 'slug' consisting of letters, \
                numbers, underscores, hyphens, or Romanian characters.",
                code="invalid_slug",
            ),
        ],
    )
    logo = models.URLField(blank=True)
    logo_dark = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Brand(models.Model):
    id_fka = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=150)
    logo = models.URLField(blank=True)
    logo_dark = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Kit(models.Model):
    id_fka = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=100)
    # Custom slug field that allows special characters
    # (The Django default slug field does not allow special characters)
    slug = models.CharField(
        unique=True,
        db_index=True,
        max_length=150,
        validators=[
            RegexValidator(
                regex=r"^[-a-zA-Z0-9_ăâîșțĂÂÎȘȚ]+$",
                message="Enter a valid 'slug' consisting of letters, \
                numbers, underscores, hyphens, or Romanian characters.",
            ),
        ],
    )
    team = models.ForeignKey(Club, on_delete=models.CASCADE, null=True, blank=True)
    season = models.ForeignKey(Season, on_delete=models.CASCADE, null=True, blank=True)
    competition = models.ManyToManyField(Competition, blank=True)
    type = models.ForeignKey(TypeK, on_delete=models.CASCADE, null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True, blank=True)
    main_img_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def generate_slug(self):
        return self.name.lower().replace(" ", "-")
