from dal import autocomplete
from dal_select2 import widgets as select2_widgets
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_countries import countries

from footycollect.collection.services import FormService
from footycollect.core.models import Brand

from .models import BaseItem, Color, Jersey, Size

MAX_PHOTOS = 10


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class BrandWidget(select2_widgets.ModelSelect2):
    model = Brand
    search_fields = ["name__icontains"]
    max_results = 10
    attrs = {"class": "form-control select2"}

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs)
        attrs.update(
            {
                "data-minimum-input-length": 0,
                "data-placeholder": "Buscar marca...",
            },
        )
        return attrs


class BaseItemForm(forms.ModelForm):
    """Base form for common fields across all item types."""

    is_replica = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input toggle-switch"}),
    )

    design = forms.ChoiceField(
        required=False,
        choices=[("", _("Select design")), *BaseItem.DESIGN_CHOICES],
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "data-component": "design-selector",
            },
        ),
    )

    class Meta:
        model = BaseItem
        fields = [
            "name",
            "item_type",
            "brand",
            "club",
            "season",
            "competitions",
            "condition",
            "detailed_condition",
            "description",
            "is_replica",
            "main_color",
            "secondary_colors",
            "design",
        ]
        widgets = {
            "brand": BrandWidget(),
            "club": forms.Select(),
            "season": forms.Select(),
            "competitions": autocomplete.ModelSelect2Multiple(
                url="core:competition-autocomplete",
                attrs={
                    "data-placeholder": _("Search for competitions..."),
                    "class": "form-control select2",
                    "data-theme": "bootstrap-5",
                    "data-allow-clear": "true",
                    "data-minimum-input-length": 2,
                },
            ),
            "main_color": forms.Select(
                attrs={
                    "class": "form-select",
                    "data-component": "color-selector",
                },
            ),
            "secondary_colors": forms.SelectMultiple(
                attrs={
                    "class": "form-select",
                    "data-component": "color-selector",
                    "data-multiple": "true",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use FormService to get all form data
        try:
            form_service = FormService()
            form_data = form_service.get_common_form_data()

            # Set choices for color fields
            self.fields["main_color"].widget.attrs["data-choices"] = form_data["colors"]["main_colors"]
            self.fields["secondary_colors"].widget.attrs["data-choices"] = form_data["colors"]["secondary_colors"]

            # Set design choices
            self.fields["design"].widget.attrs["data-choices"] = form_data["designs"]

        except (ImportError, RuntimeError):
            # During tests or when database is not ready, use empty lists
            self.fields["main_color"].widget.attrs["data-choices"] = []
            self.fields["secondary_colors"].widget.attrs["data-choices"] = []
            self.fields["design"].widget.attrs["data-choices"] = []

        # Add class to all select fields
        for field in self.fields.values():
            if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs["class"] = "form-select"


class ItemTypeSpecificFormMixin:
    """Mixin for forms that need item type specific data."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get item type from the form's Meta class
        item_type = getattr(self.Meta, "item_type", "jersey")

        # Use FormService to get item type specific data
        try:
            form_service = FormService()
            item_data = form_service.get_item_type_specific_data(item_type)

            # Set size choices if size field exists
            if "size" in self.fields:
                self.fields["size"].widget.attrs["data-choices"] = item_data["sizes"]

        except (ImportError, RuntimeError):
            # During tests or when database is not ready, use empty list
            if "size" in self.fields:
                self.fields["size"].widget.attrs["data-choices"] = []


class ItemTypeForm(forms.Form):
    """Form to select which type of item to create."""

    ITEM_TYPES = [
        ("jersey", _("Jersey")),
        ("shorts", _("Shorts")),
        ("outerwear", _("Outerwear")),
        ("tracksuit", _("Tracksuit")),
        ("pants", _("Pants")),
        ("other", _("Other Item")),
    ]

    item_type = forms.ChoiceField(
        choices=ITEM_TYPES,
        label=_("What type of item do you want to add?"),
        widget=forms.RadioSelect,
        help_text=_("Select the type of item you want to add to your collection"),
    )


class JerseyForm(forms.ModelForm):
    """Form for Jersey items using Service Layer with STI structure."""

    class Meta:
        model = BaseItem
        fields = [
            "name",
            "condition",
            "description",
            "main_color",
            "secondary_colors",
        ]

    def __init__(self, *args, **kwargs):
        # Extract user from kwargs
        self.user = kwargs.pop("user", None)

        # Ensure we always have an instance before calling parent
        if "instance" not in kwargs:
            kwargs["instance"] = BaseItem()
        super().__init__(*args, **kwargs)

    size = forms.ModelChoiceField(
        queryset=Size.objects.all(),
        label=_("Size"),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    brand = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )

    brand_name = forms.CharField(required=False, widget=forms.HiddenInput())

    competitions = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    competition_name = forms.CharField(required=False, widget=forms.HiddenInput())

    club = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )

    club_name = forms.CharField(required=False, widget=forms.HiddenInput())

    season = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )

    season_name = forms.CharField(required=False, widget=forms.HiddenInput())

    condition = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=10,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    detailed_condition = forms.ChoiceField(
        choices=BaseItem.CONDITION_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    is_replica = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input toggle-switch"}),
    )

    main_color = forms.ModelChoiceField(
        queryset=Color.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    secondary_colors = forms.ModelMultipleChoiceField(
        queryset=Color.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select"}),
    )

    design = forms.ChoiceField(
        choices=BaseItem.DESIGN_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    country_code = forms.ChoiceField(
        choices=countries,
        label=_("Country"),
        required=False,
        widget=autocomplete.Select2(
            url="core:country-autocomplete",
            attrs={
                "data-html": True,
                "data-placeholder": _("Select a country..."),
                "class": "form-control select2",
                "data-theme": "bootstrap-5",
                "data-allow-clear": "true",
                "data-minimum-input-length": 0,
                "data-debug": "true",
            },
        ),
    )

    # Jersey-specific fields

    is_fan_version = forms.BooleanField(
        required=False,
        label=_("Fan Version"),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input toggle-switch"}),
    )

    is_signed = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input toggle-switch"}),
    )

    has_nameset = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input toggle-switch"}),
    )

    player_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    is_short_sleeve = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Short Sleeve"),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input toggle-switch"}),
    )

    number = forms.IntegerField(
        min_value=0,
        max_value=99,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def clean_main_color(self):
        """Normalize main color from string name to Color object."""
        main_color_name = self.data.get("main_color")
        if not main_color_name:
            return self.cleaned_data.get("main_color")

        # If it's already a Color object, return it
        if isinstance(main_color_name, Color):
            return main_color_name

        # If it's an ID, try to get the Color object
        try:
            color_id = int(main_color_name)
            return Color.objects.get(id=color_id)
        except (ValueError, TypeError, Color.DoesNotExist):
            pass

        # Otherwise, treat it as a color name and get_or_create
        color_obj, _ = Color.objects.get_or_create(
            name__iexact=main_color_name.strip(),
            defaults={"name": main_color_name.strip().upper()},
        )
        return color_obj

    def clean_secondary_colors(self):
        """Normalize secondary colors from string names to Color objects."""
        # Handle both QueryDict and regular dict
        if hasattr(self.data, "getlist"):
            secondary_colors_names = self.data.getlist("secondary_colors")
        else:
            secondary_colors = self.data.get("secondary_colors")
            if secondary_colors:
                secondary_colors_names = [secondary_colors] if isinstance(secondary_colors, str) else secondary_colors
            else:
                secondary_colors_names = []

        if not secondary_colors_names:
            return self.cleaned_data.get("secondary_colors", [])

        color_objects = []
        for color_name in secondary_colors_names:
            if not color_name:
                continue

            # If it's already a Color object, add it
            if isinstance(color_name, Color):
                color_objects.append(color_name)
                continue

            # If it's an ID, try to get the Color object
            try:
                color_id = int(color_name)
                color_obj = Color.objects.get(id=color_id)
                color_objects.append(color_obj)
                continue
            except (ValueError, TypeError, Color.DoesNotExist):
                pass

            # Otherwise, treat it as a color name and get_or_create
            color_obj, _ = Color.objects.get_or_create(
                name__iexact=color_name.strip(),
                defaults={"name": color_name.strip().upper()},
            )
            color_objects.append(color_obj)

        return color_objects

    def clean(self):
        """Custom validation for the form."""
        cleaned_data = super().clean()

        # If brand is not provided but brand_name is, that's OK
        # The brand will be created in _extract_base_item_data
        brand_id = cleaned_data.get("brand")
        brand_name = self.data.get("brand_name")

        if not brand_id and not brand_name:
            raise forms.ValidationError({"brand": _("Please select a brand or provide a brand name.")})

        return cleaned_data

    def _resolve_brand(self):
        """Resolve or create brand from cleaned_data and request data."""
        import contextlib
        import logging

        from django.utils.text import slugify

        from footycollect.core.models import Brand

        logger = logging.getLogger(__name__)

        brand = None
        brand_id = self.cleaned_data.get("brand")
        if brand_id:
            with contextlib.suppress(Brand.DoesNotExist):
                brand = Brand.objects.get(id=brand_id)
                logger.info("Found brand by ID: %s", brand_id)

        if not brand and self.data.get("brand_name"):
            brand_name = self.data.get("brand_name")
            logger.info("Creating brand from name: %s", brand_name)
            try:
                brand, created = Brand.objects.get_or_create(
                    name=brand_name,
                    defaults={"slug": slugify(brand_name)},
                )
                if created:
                    logger.info("Created new brand: %s", brand_name)
                else:
                    logger.info("Found existing brand: %s", brand_name)
            except (ValueError, TypeError):
                logger.exception("Error creating brand %s", brand_name)
                brand = None

        if not brand:
            raise ValidationError(_("Brand could not be resolved. Please try again."))
        return brand

    def _resolve_club(self):
        """Resolve or create club from cleaned_data and request data."""
        import contextlib
        import logging

        from django.utils.text import slugify

        from footycollect.core.models import Club

        logger = logging.getLogger(__name__)

        club = None
        club_id = self.cleaned_data.get("club")
        if club_id:
            with contextlib.suppress(Club.DoesNotExist):
                club = Club.objects.get(id=club_id)
                logger.info("Found club by ID: %s", club_id)

        if not club and self.data.get("club_name"):
            club_name = self.data.get("club_name")
            logger.info("Creating club from name: %s", club_name)
            try:
                club, created = Club.objects.get_or_create(
                    name=club_name,
                    defaults={"slug": slugify(club_name)},
                )
                if created:
                    logger.info("Created new club: %s", club_name)
                else:
                    logger.info("Found existing club: %s", club_name)
            except (ValueError, TypeError):
                logger.exception("Error creating club %s", club_name)
                club = None

        if not club:
            raise ValidationError(_("Club could not be resolved. Please try again."))
        return club

    def _resolve_season(self):
        """Resolve or create season from cleaned_data and request data."""
        import contextlib
        import logging

        from django.utils.text import slugify

        from footycollect.core.models import Season

        logger = logging.getLogger(__name__)

        season = None
        season_id = self.cleaned_data.get("season")
        if season_id:
            with contextlib.suppress(Season.DoesNotExist):
                season = Season.objects.get(id=season_id)
                logger.info("Found season by ID: %s", season_id)

        if not season and self.data.get("season_name"):
            season_name = self.data.get("season_name")
            logger.info("Creating season from name: %s", season_name)
            try:
                season, created = Season.objects.get_or_create(
                    name=season_name,
                    defaults={"slug": slugify(season_name)},
                )
                if created:
                    logger.info("Created new season: %s", season_name)
                else:
                    logger.info("Found existing season: %s", season_name)
            except (ValueError, TypeError):
                logger.exception("Error creating season %s", season_name)
                season = None

        if not season:
            raise ValidationError(_("Season could not be resolved. Please try again."))
        return season

    def _extract_base_item_data(self):
        """Extract data for BaseItem creation."""
        brand = self._resolve_brand()
        club = self._resolve_club()
        season = self._resolve_season()

        return {
            "name": self.cleaned_data.get("name", ""),
            "club": club,
            "season": season,
            "brand": brand,
            "condition": self.cleaned_data.get("condition"),
            "detailed_condition": self.cleaned_data.get("detailed_condition"),
            "is_replica": self.cleaned_data.get("is_replica", False),
            "description": self.cleaned_data.get("description", ""),
            "main_color": self.cleaned_data.get("main_color"),
            "design": self.cleaned_data.get("design"),
            "user": self.user,
            "item_type": "jersey",
        }

    def _extract_jersey_data(self):
        """Extract data for Jersey creation."""
        return {
            "size": self.cleaned_data.get("size"),
            "is_fan_version": self.cleaned_data.get("is_fan_version", False),
            "is_signed": self.cleaned_data.get("is_signed", False),
            "has_nameset": self.cleaned_data.get("has_nameset", False),
            "player_name": self.cleaned_data.get("player_name", ""),
            "is_short_sleeve": self.cleaned_data.get("is_short_sleeve", False),
            "number": self.cleaned_data.get("number", ""),
        }

    def _extract_many_to_many_data(self):
        """Extract ManyToMany field data."""
        from footycollect.core.models import Competition

        competitions = []
        competitions_data = self.cleaned_data.get("competitions", "")
        if competitions_data:
            if isinstance(competitions_data, str):
                competition_ids = [
                    int(comp_id.strip()) for comp_id in competitions_data.split(",") if comp_id.strip().isdigit()
                ]
            elif isinstance(competitions_data, list):
                competition_ids = [int(comp_id) for comp_id in competitions_data if comp_id]
            else:
                competition_ids = [competitions_data] if competitions_data else []

            if competition_ids:
                competitions = Competition.objects.filter(id__in=competition_ids)

        return {
            "competitions": competitions,
        }

    def save(self, *, commit=True):
        """Save the form data using MTI structure."""
        base_item_data = self._extract_base_item_data()
        jersey_data = self._extract_jersey_data()
        many_to_many_data = self._extract_many_to_many_data()

        if commit:
            # Create BaseItem first
            base_item = BaseItem.objects.create(**base_item_data)

            # Create Jersey linked to BaseItem
            jersey_data["base_item"] = base_item
            Jersey.objects.create(**jersey_data)

            # Handle ManyToMany fields
            if many_to_many_data.get("competitions"):
                base_item.competitions.set(many_to_many_data["competitions"])

            # Handle secondary_colors from cleaned_data
            secondary_colors = self.cleaned_data.get("secondary_colors", [])
            if secondary_colors:
                base_item.secondary_colors.set(secondary_colors)

            return base_item
        # For non-commit case, create instances but don't save
        base_item = BaseItem(**base_item_data)
        jersey_data["base_item"] = base_item
        return Jersey(**jersey_data)


class JerseyFKAPIForm(JerseyForm):
    """Formulario mejorado para crear jerseys con integración de FKAPI"""

    class Meta(JerseyForm.Meta):
        """Meta class for JerseyFKAPIForm - inherits from JerseyForm.Meta"""

    # Additional fields for search (not saved to the model)
    kit_search = forms.CharField(
        required=False,
        label=_("Search Kit"),
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Start typing to search for kits..."),
                "x-model": "kitSearch",
                "x-on:input.debounce.500ms": "searchKits()",
            },
        ),
    )

    kit_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )

    club_search = forms.CharField(
        required=False,
        label=_("Search Club"),
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Or search for a club..."),
                "x-model": "clubSearch",
                "x-on:input.debounce.500ms": "searchClubs()",
                "x-show": "showClubSearch",
            },
        ),
    )

    # Hidden fields to store the names of entities to be created
    brand_name = forms.CharField(required=False, widget=forms.HiddenInput())
    club_name = forms.CharField(required=False, widget=forms.HiddenInput())
    season_name = forms.CharField(required=False, widget=forms.HiddenInput())
    competition_name = forms.CharField(required=False, widget=forms.HiddenInput())

    # Hidden field for the main image URL
    main_img_url = forms.URLField(required=False, widget=forms.HiddenInput())

    # Field to store external image URLs
    external_image_urls = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        # Ensure we always have a valid instance
        if "instance" not in kwargs or kwargs["instance"] is None:
            from footycollect.collection.models import BaseItem

            kwargs["instance"] = BaseItem()

        super().__init__(*args, **kwargs)

        # Ensure instance is properly set
        if self.instance is None:
            from footycollect.collection.models import BaseItem

            self.instance = BaseItem()

        using_api = False
        if (
            "data" in kwargs
            and kwargs["data"]
            and kwargs["data"].get("brand_name")
            or "initial" in kwargs
            and kwargs["initial"]
            and kwargs["initial"].get("brand_name")
        ):
            using_api = True

        if using_api:
            self.fields["brand"].required = False
            self.fields["club"].required = False
            self.fields["season"].required = False
            self.fields["competitions"].required = False
            self.fields["main_color"].required = False
            self.fields["secondary_colors"].required = False

    def clean_main_color(self):
        main_color_name = self.data.get("main_color")
        if not main_color_name:
            return self.cleaned_data.get("main_color")

        color_obj, _ = Color.objects.get_or_create(
            name__iexact=main_color_name.strip(),
            defaults={"name": main_color_name.strip().upper()},
        )
        return color_obj

    def clean_secondary_colors(self):
        # Handle both QueryDict and regular dict
        if hasattr(self.data, "getlist"):
            secondary_colors_names = self.data.getlist("secondary_colors")
        else:
            secondary_colors = self.data.get("secondary_colors")
            if secondary_colors:
                secondary_colors_names = [secondary_colors] if isinstance(secondary_colors, str) else secondary_colors
            else:
                secondary_colors_names = []

        if not secondary_colors_names:
            return self.cleaned_data.get("secondary_colors", [])

        color_objects = []
        for color_name in secondary_colors_names:
            if not color_name:
                continue
            color_obj, _ = Color.objects.get_or_create(
                name__iexact=color_name.strip(),
                defaults={"name": color_name.strip().upper()},
            )
            color_objects.append(color_obj)
        return color_objects

    def clean(self):
        cleaned_data = super().clean()
        using_api = bool(self.data.get("brand_name"))
        # When using the API, ignore validation errors for these fields since
        # they will be handled in the view. Remove any such errors if present.
        if using_api:
            for field in [
                "brand",
                "club",
                "season",
                "competitions",
                "main_color",
                "secondary_colors",
            ]:
                if field in self._errors:
                    del self._errors[field]

        return cleaned_data


class OuterwearForm(ItemTypeSpecificFormMixin, forms.ModelForm):
    class Meta:
        model = BaseItem
        fields = [
            "name",
            "club",
            "season",
            "brand",
            "condition",
            "description",
            "competitions",
            "main_color",
            "secondary_colors",
        ]


class ShortsForm(ItemTypeSpecificFormMixin, forms.ModelForm):
    class Meta:
        model = BaseItem
        fields = [
            "name",
            "club",
            "season",
            "brand",
            "condition",
            "description",
            "competitions",
            "main_color",
            "secondary_colors",
        ]


class TrackSuitForm(ItemTypeSpecificFormMixin, forms.ModelForm):
    class Meta:
        model = BaseItem
        fields = [
            "name",
            "club",
            "season",
            "brand",
            "condition",
            "description",
            "competitions",
            "main_color",
            "secondary_colors",
        ]


class PantsForm(ItemTypeSpecificFormMixin, forms.ModelForm):
    class Meta:
        model = BaseItem
        fields = [
            "name",
            "club",
            "season",
            "brand",
            "condition",
            "description",
            "competitions",
            "main_color",
            "secondary_colors",
        ]


class OtherItemForm(ItemTypeSpecificFormMixin, forms.ModelForm):
    class Meta:
        model = BaseItem
        fields = [
            "name",
            "club",
            "season",
            "brand",
            "condition",
            "description",
            "competitions",
            "main_color",
            "secondary_colors",
        ]


class ItemPhotosForm(forms.Form):
    """Form for uploading multiple photos."""

    photos = MultipleFileField(
        label=_("Upload Photos"),
        required=False,
        widget=MultipleFileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*",
                "multiple": True,
            },
        ),
        help_text=_(
            "You can upload up to 20 photos. First photo will be the main one.",
        ),
    )

    def clean_photos(self):
        photos = self.cleaned_data.get("photos", [])
        # Convert to list if it's a single file
        if not isinstance(photos, list):
            photos = [photos] if photos else []

        if len(photos) > MAX_PHOTOS:
            raise forms.ValidationError(
                _("You can't upload more than %d photos.") % MAX_PHOTOS,
            )
        return photos


class TestCountryForm(forms.Form):
    """Simple form to test Select2 integration with Countries"""

    country = forms.ChoiceField(
        choices=countries,
        widget=autocomplete.Select2(
            url="core:country-autocomplete",
            attrs={
                "data-html": True,
                "data-placeholder": "Selecciona un país...",
            },
        ),
    )


class TestBrandForm(forms.Form):
    """Form simple para probar Select2 con Brand"""

    brand = forms.ModelChoiceField(
        queryset=Brand.objects.none(),  # Will be set in __init__
        widget=autocomplete.ModelSelect2(
            url="core:brand-autocomplete",
            attrs={
                "data-placeholder": "Buscar marca...",
                "data-minimum-input-length": 0,
            },
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the brand queryset (lazy loading)
        try:
            self.fields["brand"].queryset = Brand.objects.all()
        except (ImportError, RuntimeError):
            # During tests or when database is not ready, use empty queryset
            self.fields["brand"].queryset = Brand.objects.none()
