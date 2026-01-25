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
YEAR_LENGTH = 4


class ColorModelChoiceField(forms.ModelChoiceField):
    """ModelChoiceField that accepts color names as strings."""

    def prepare_value(self, value):
        """Ensure value is always converted to ID for template rendering."""
        if hasattr(value, "_meta"):
            return value.pk
        return super().prepare_value(value)

    def to_python(self, value):
        """Override to handle color names in addition to IDs."""
        if value in self.empty_values:
            return None
        # Try normal ModelChoiceField behavior first (ID lookup)
        try:
            return super().to_python(value)
        except ValidationError:
            # If that fails, try as color name
            # Color is already imported at module level
            try:
                return Color.objects.get(name__iexact=str(value).strip())
            except Color.DoesNotExist:
                # Return the string - clean method will create it
                return str(value).strip()


class ColorModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    """ModelMultipleChoiceField that accepts color names as strings."""

    def to_python(self, value):
        """Override to handle color names in addition to IDs.

        IMPORTANT: For API flows, we need to preserve color names as strings
        so that clean_secondary_colors can process them. Only convert to Color
        objects if they are already IDs (numeric strings).
        """
        if value in self.empty_values:
            return []
        if isinstance(value, (list, tuple)):
            result = []
            for v in value:
                if not v:
                    continue
                # If it's already a Color object, keep it
                if isinstance(v, Color):
                    result.append(v)
                    continue
                # If it's a numeric string (ID), try to convert to Color object
                try:
                    color_id = int(v)
                    color_obj = Color.objects.get(id=color_id)
                    result.append(color_obj)
                    continue
                except (ValueError, TypeError, Color.DoesNotExist):
                    pass
                # Otherwise, keep as string - clean_secondary_colors will handle it
                result.append(str(v).strip())
            return result
        # Single value
        if isinstance(value, Color):
            return [value]
        # If it's a numeric string (ID), try to convert to Color object
        try:
            color_id = int(value)
            color_obj = Color.objects.get(id=color_id)
        except (ValueError, TypeError, Color.DoesNotExist):
            pass
        else:
            return [color_obj]
        # Otherwise, keep as string - clean_secondary_colors will handle it
        return [str(value).strip()]


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
        self.user = kwargs.pop("user", None)

        # Ensure we always have an instance before calling parent
        if "instance" not in kwargs:
            kwargs["instance"] = BaseItem()
        super().__init__(*args, **kwargs)

        # When editing an existing item, pre-populate form fields from the instance
        instance = self.instance
        if instance is not None and instance.pk:
            # BaseItem fields
            self.fields["name"].initial = instance.name
            self.fields["condition"].initial = instance.condition
            self.fields["detailed_condition"].initial = instance.detailed_condition
            self.fields["description"].initial = instance.description
            self.fields["is_replica"].initial = instance.is_replica
            self.fields["main_color"].initial = instance.main_color_id
            self.fields["secondary_colors"].initial = list(
                instance.secondary_colors.values_list("id", flat=True),
            )
            self.fields["design"].initial = instance.design
            if instance.country:
                self.fields["country_code"].initial = instance.country

            # Hidden ID + name fields for brand / club / season
            if instance.brand_id:
                self.fields["brand"].initial = instance.brand_id
                self.fields["brand_name"].initial = getattr(instance.brand, "name", "")

            if instance.club_id:
                self.fields["club"].initial = instance.club_id
                self.fields["club_name"].initial = getattr(instance.club, "name", "")

            if instance.season_id:
                self.fields["season"].initial = instance.season_id
                self.fields["season_name"].initial = getattr(instance.season, "name", "")

            # Competitions: store IDs as comma-separated string for the hidden field
            competition_ids = list(instance.competitions.values_list("id", flat=True))
            if competition_ids:
                self.fields["competitions"].initial = ",".join(str(cid) for cid in competition_ids)

            # Jersey-specific fields from the MTI child
            jersey = getattr(instance, "jersey", None)
            if jersey is not None:
                self.fields["size"].initial = jersey.size_id
                self.fields["is_fan_version"].initial = jersey.is_fan_version
                self.fields["is_signed"].initial = jersey.is_signed
                self.fields["has_nameset"].initial = jersey.has_nameset
                self.fields["player_name"].initial = jersey.player_name
                self.fields["is_short_sleeve"].initial = jersey.is_short_sleeve
                self.fields["number"].initial = jersey.number

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

    main_color = ColorModelChoiceField(
        queryset=Color.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    secondary_colors = ColorModelMultipleChoiceField(
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
            # If no secondary colors provided, return empty list
            # Don't use cleaned_data here as it might contain values from to_python
            # that shouldn't be there
            return []

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
            logger.info("Creating season from year: %s", season_name)
            try:
                # Season model uses 'year' field, not 'name'
                # Parse year string (e.g., "2022-23") into first_year and second_year
                if "-" in season_name:
                    parts = season_name.split("-")
                    first_year = parts[0]
                    second_year = parts[1] if len(parts) > 1 else ""
                else:
                    # Single year (e.g., "2022")
                    first_year = season_name[:YEAR_LENGTH] if len(season_name) >= YEAR_LENGTH else season_name
                    second_year = ""

                season, created = Season.objects.get_or_create(
                    year=season_name,  # Use 'year' field, not 'name'
                    defaults={
                        "first_year": first_year,
                        "second_year": second_year,
                    },
                )
                if created:
                    logger.info(
                        "Created new season: %s (year=%s, first=%s, second=%s)",
                        season_name,
                        season.year,
                        season.first_year,
                        season.second_year,
                    )
                else:
                    logger.info("Found existing season: %s (year=%s)", season_name, season.year)
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

        base_data = {
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

        # FIX: Convert country_code string to Country object
        country_code = self.cleaned_data.get("country_code")

        if country_code:
            try:
                base_data["country"] = self._convert_country_code(country_code, club)
            except (ValueError, AttributeError, KeyError, TypeError) as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning("Error converting country_code %s: %s", country_code, str(e))
                if club and club.country:
                    base_data["country"] = club.country
        elif hasattr(self.instance, "country") and self.instance.country:
            base_data["country"] = self.instance.country
        elif club and club.country:
            base_data["country"] = club.country

        return base_data

    def _convert_country_code(self, country_code, club):
        """Convert country_code string to Country object."""
        if isinstance(country_code, str):
            if country_code.upper() in countries:
                return country_code.upper()
            if club and club.country:
                return club.country
        return country_code

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
        import logging

        from footycollect.core.models import Competition

        logger = logging.getLogger(__name__)
        competitions = []
        competitions_data = self.cleaned_data.get("competitions", "")
        logger.debug(
            "_extract_many_to_many_data - competitions_data: %s (type: %s)",
            competitions_data,
            type(competitions_data),
        )

        if competitions_data:
            if isinstance(competitions_data, str):
                competition_ids = [
                    int(comp_id.strip()) for comp_id in competitions_data.split(",") if comp_id.strip().isdigit()
                ]
                logger.debug("_extract_many_to_many_data - parsed competition_ids from string: %s", competition_ids)
            elif isinstance(competitions_data, list):
                competition_ids = [int(comp_id) for comp_id in competitions_data if comp_id]
                logger.debug("_extract_many_to_many_data - parsed competition_ids from list: %s", competition_ids)
            else:
                competition_ids = [competitions_data] if competitions_data else []
                logger.debug("_extract_many_to_many_data - parsed competition_ids from other: %s", competition_ids)

            if competition_ids:
                competitions = Competition.objects.filter(id__in=competition_ids)
                logger.info(
                    "_extract_many_to_many_data - found competitions: %s (count: %s)",
                    [c.name for c in competitions],
                    competitions.count(),
                )
            else:
                logger.warning(
                    "_extract_many_to_many_data - no valid competition_ids extracted from: %s",
                    competitions_data,
                )

        return {
            "competitions": competitions,
        }

    def save(self, *, commit=True):
        """
        Save the form data using MTI structure.

        - If instance has a primary key, update the existing BaseItem + Jersey.
        - If not, create a new BaseItem + Jersey pair.
        """
        # Update existing objects when editing
        if self.instance is not None and self.instance.pk:
            return self._update_existing_item(commit=commit)

        # Creation path for new items
        return self._create_new_item(commit=commit)

    def _update_existing_item(self, *, commit):
        """Update an existing BaseItem and its related Jersey."""
        base_item = self.instance

        # Resolve related entities from the form / hidden fields
        brand = self._resolve_brand()
        club = self._resolve_club()
        season = self._resolve_season()

        # Update base item fields
        base_item.name = self.cleaned_data.get("name", base_item.name)
        base_item.brand = brand
        base_item.club = club
        base_item.season = season
        base_item.condition = self.cleaned_data.get("condition", base_item.condition)
        base_item.detailed_condition = self.cleaned_data.get(
            "detailed_condition",
            base_item.detailed_condition,
        )
        base_item.description = self.cleaned_data.get("description", base_item.description)
        base_item.is_replica = self.cleaned_data.get("is_replica", base_item.is_replica)
        base_item.main_color = self.cleaned_data.get("main_color", base_item.main_color)
        base_item.design = self.cleaned_data.get("design", base_item.design)

        # Country comes from a separate form field
        country_code = self.cleaned_data.get("country_code")
        if country_code:
            base_item.country = country_code

        if commit:
            base_item.save()
            self._update_many_to_many_relations(base_item)
            self._update_jersey_fields(base_item)

        return base_item

    def _update_many_to_many_relations(self, base_item):
        """Update ManyToMany relations for competitions and secondary colors."""
        many_to_many_data = self._extract_many_to_many_data()
        if many_to_many_data.get("competitions"):
            base_item.competitions.set(many_to_many_data["competitions"])

        secondary_colors = self.cleaned_data.get("secondary_colors", [])
        if secondary_colors:
            base_item.secondary_colors.set(secondary_colors)
        else:
            base_item.secondary_colors.clear()

    def _update_jersey_fields(self, base_item):
        """Update Jersey-specific fields."""
        jersey = getattr(base_item, "jersey", None)
        if jersey is None:
            return

        jersey.size = self.cleaned_data.get("size", jersey.size)
        jersey.is_fan_version = self.cleaned_data.get("is_fan_version", jersey.is_fan_version)
        jersey.is_signed = self.cleaned_data.get("is_signed", jersey.is_signed)
        jersey.has_nameset = self.cleaned_data.get("has_nameset", jersey.has_nameset)
        jersey.player_name = self.cleaned_data.get("player_name", jersey.player_name)
        jersey.is_short_sleeve = self.cleaned_data.get("is_short_sleeve", jersey.is_short_sleeve)
        jersey.number = self.cleaned_data.get("number", jersey.number)
        jersey.save()

    def _create_new_item(self, *, commit):
        """Create a new BaseItem and Jersey pair."""
        import logging

        logger = logging.getLogger(__name__)

        base_item_data = self._extract_base_item_data()
        jersey_data = self._extract_jersey_data()
        many_to_many_data = self._extract_many_to_many_data()

        if not commit:
            # For non-commit case, create instances but don't save
            base_item = BaseItem(**base_item_data)
            jersey_data["base_item"] = base_item
            return Jersey(**jersey_data)

        # Create BaseItem with ALL fields
        logger.debug("Creating BaseItem with data: %s", base_item_data)
        base_item = BaseItem.objects.create(**base_item_data)
        logger.debug("Created BaseItem %s", base_item.id)

        # Remove any 'id' from jersey_data and create Jersey
        jersey_data.pop("id", None)
        logger.debug("Creating Jersey with base_item=%s", base_item.id)
        jersey = Jersey.objects.create(base_item=base_item, **jersey_data)
        logger.debug("Created Jersey %s", jersey.pk)

        # Verify they're linked
        if jersey.base_item.id != base_item.id:
            logger.error("ERROR: Jersey %s not linked to BaseItem %s", jersey.pk, base_item.id)

        # Set ManyToMany relations
        self._set_many_to_many_on_create(base_item, many_to_many_data, logger)

        # Create or get Kit for this jersey
        try:
            self._create_kit_for_jersey(base_item, jersey)
        except (ValueError, TypeError, AttributeError):
            logger.exception("Error creating Kit")

        return base_item

    def _set_many_to_many_on_create(self, base_item, many_to_many_data, logger):
        """Set ManyToMany relations when creating a new item."""
        if many_to_many_data.get("competitions"):
            competitions_list = many_to_many_data["competitions"]
            base_item.competitions.set(competitions_list)
            logger.info(
                "Set competitions on BaseItem %s: %s (count: %s)",
                base_item.id,
                [c.name for c in competitions_list],
                len(competitions_list),
            )

        secondary_colors = self.cleaned_data.get("secondary_colors", [])
        if secondary_colors:
            base_item.secondary_colors.set(secondary_colors)
            logger.debug("Set secondary_colors: %s", [c.name for c in secondary_colors])

    def _create_kit_for_jersey(self, base_item, jersey):
        """Create and link Kit to jersey."""
        import logging

        from footycollect.collection.services.kit_service import KitService

        logger = logging.getLogger(__name__)
        kit_service = KitService()
        kit_id = self.cleaned_data.get("kit_id")
        fkapi_data = getattr(self, "fkapi_data", {})

        kit = kit_service.get_or_create_kit_for_jersey(
            base_item=base_item,
            jersey=jersey,
            fkapi_data=fkapi_data,
            kit_id=kit_id,
        )

        jersey.kit = kit
        jersey.save()
        logger.info("Successfully created/linked Kit %s to Jersey %s", kit.id, jersey.pk)


class JerseyFKAPIForm(JerseyForm):
    """Enhanced form for creating jerseys with FKAPI integration."""

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
    name = forms.CharField(
        max_length=255,
        required=False,  # Make optional for FKAPI flow
        help_text="Auto-generated from kit if not provided",
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
    main_img_url = forms.URLField(required=False, widget=forms.HiddenInput(), assume_scheme="https")

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

    def _get_main_color_name(self, value):
        """Extract main color name from form data."""
        import logging

        logger = logging.getLogger(__name__)

        main_color_name = self.data.get("main_color")
        logger.debug("clean_main_color - from self.data: %s", main_color_name)

        if not main_color_name and hasattr(self.data, "getlist"):
            color_list = self.data.getlist("main_color")
            if color_list:
                main_color_name = color_list[0]
                logger.debug("clean_main_color - from getlist: %s", main_color_name)

        if not main_color_name:
            main_color_name = self.initial.get("main_color")
            logger.debug("clean_main_color - from initial: %s", main_color_name)

        if not main_color_name and value:
            try:
                color_obj = Color.objects.get(pk=value)
                logger.debug("clean_main_color - found Color by ID: %s", color_obj)
            except (Color.DoesNotExist, ValueError, TypeError):
                pass
            else:
                return color_obj, None

        return None, main_color_name

    def clean_main_color(self):
        """Convert main_color string to Color object."""
        import logging

        logger = logging.getLogger(__name__)

        value = self.cleaned_data.get("main_color")

        if value and hasattr(value, "name"):
            logger.debug("clean_main_color - already Color object: %s", value)
            return value

        color_obj, main_color_name = self._get_main_color_name(value)
        if color_obj:
            return color_obj

        if not main_color_name:
            logger.debug("clean_main_color - no value found, returning None")
            return None

        try:
            color_obj, created = Color.objects.get_or_create(
                name__iexact=main_color_name.strip(),
                defaults={"name": main_color_name.strip().upper()},
            )
            logger.info("clean_main_color - returning Color: %s (created=%s)", color_obj, created)
        except (ValueError, TypeError):
            logger.exception("clean_main_color - error")
            return None
        else:
            return color_obj

    def _get_secondary_colors_names(self):
        """Extract secondary color names from form data.

        Tries multiple sources in order: getlist, direct get, cleaned_data, initial.
        """
        import logging

        logger = logging.getLogger(__name__)

        # Try each source in order of preference
        result = self._get_colors_from_getlist(logger)
        if result:
            return result

        result = self._get_colors_from_direct_get(logger)
        if result:
            return result

        result = self._get_colors_from_cleaned_data(logger)
        if result:
            return result

        result = self._get_colors_from_initial(logger)
        if result:
            return result

        return []

    def _get_colors_from_getlist(self, logger):
        """Try to get colors using getlist for multiple values."""
        if not hasattr(self.data, "getlist"):
            return None
        names = self.data.getlist("secondary_colors")
        if not names:
            return None
        result = [str(n).strip() for n in names if n]
        if result:
            logger.debug("clean_secondary_colors - from getlist: %s", names)
        return result or None

    def _get_colors_from_direct_get(self, logger):
        """Try to get colors using direct get (single value or list)."""
        colors = self.data.get("secondary_colors")
        if not colors:
            return None
        names = colors if isinstance(colors, list) else [colors]
        result = [str(n).strip() for n in names if n]
        if result:
            logger.debug("clean_secondary_colors - from get: %s", result)
        return result or None

    def _get_colors_from_cleaned_data(self, logger):
        """Try to get colors from cleaned_data (from to_python)."""
        if not hasattr(self, "cleaned_data") or not self.cleaned_data:
            return None
        colors = self.cleaned_data.get("secondary_colors")
        if not colors:
            return None
        result = []
        items = colors if isinstance(colors, list) else [colors]
        for c in items:
            if isinstance(c, str):
                result.append(c.strip())
            elif isinstance(c, Color):
                result.append(c.name)
        if result:
            logger.debug("clean_secondary_colors - from cleaned_data: %s", result)
        return result or None

    def _get_colors_from_initial(self, logger):
        """Try to get colors from initial data."""
        colors = self.initial.get("secondary_colors")
        if not colors:
            return None
        names = colors if isinstance(colors, list) else [colors]
        result = [str(n).strip() for n in names if n]
        if result:
            logger.debug("clean_secondary_colors - from initial: %s", result)
        return result or None

    def _convert_color_names_to_objects(self, color_names):
        """Convert color name strings to Color objects."""
        import logging

        logger = logging.getLogger(__name__)

        color_objects = []
        for color_name in color_names:
            if not color_name:
                continue

            # If it's already a Color object, add it
            if isinstance(color_name, Color):
                color_objects.append(color_name)
                continue

            # If it's an ID (numeric string), try to get the Color object
            try:
                color_id = int(color_name)
                color_obj = Color.objects.get(id=color_id)
                color_objects.append(color_obj)
                logger.debug("clean_secondary_colors - found Color by ID: %s", color_obj.name)
                continue
            except (ValueError, TypeError, Color.DoesNotExist):
                pass

            # Otherwise, treat it as a color name and get_or_create
            try:
                color_obj, created = Color.objects.get_or_create(
                    name__iexact=str(color_name).strip(),
                    defaults={"name": str(color_name).strip().upper()},
                )
                color_objects.append(color_obj)
                logger.debug("clean_secondary_colors - added Color: %s (created=%s)", color_obj.name, created)
            except (ValueError, TypeError):
                logger.exception("clean_secondary_colors - error for %s", color_name)

        return color_objects

    def clean_secondary_colors(self):
        """Convert secondary_colors strings to Color objects."""
        import logging

        logger = logging.getLogger(__name__)

        secondary_colors_names = self._get_secondary_colors_names()

        if not secondary_colors_names:
            logger.debug("clean_secondary_colors - no values found, returning []")
            return []

        color_objects = self._convert_color_names_to_objects(secondary_colors_names)
        logger.debug("clean_secondary_colors - returning %s colors", len(color_objects))
        return color_objects

    def clean_country_code(self):
        """Validate and return country code."""
        import logging

        logger = logging.getLogger(__name__)

        country_code = self.data.get("country_code")
        logger.debug("clean_country_code - from self.data: %s", country_code)

        if not country_code:
            country_code = self.initial.get("country_code")
            logger.debug("clean_country_code - from initial: %s", country_code)

        if country_code:
            # Validate it's a valid country code
            try:
                from django_countries import countries

                if country_code.upper() in dict(countries):
                    logger.debug("clean_country_code - valid: %s", country_code.upper())
                    return country_code.upper()
                logger.warning("clean_country_code - invalid code: %s", country_code)
            except (ValueError, AttributeError, ImportError):
                logger.exception("clean_country_code - error")

        return country_code

    def clean(self):
        import logging

        logger = logging.getLogger(__name__)
        logger.debug("=== JerseyFKAPIForm.clean() CALLED ===")
        data_keys = list(self.data.keys()) if hasattr(self.data, "keys") else "N/A"
        logger.debug("self.data keys: %s", data_keys)
        logger.debug("country_code in data: %s", self.data.get("country_code"))
        cleaned_data = super().clean()
        using_api = bool(self.data.get("brand_name"))
        logger.debug("using_api: %s", using_api)
        logger.debug("cleaned_data keys: %s", list(cleaned_data.keys()))
        logger.debug("country_code in cleaned_data: %s", cleaned_data.get("country_code"))
        logger.debug("main_color in cleaned_data: %s", cleaned_data.get("main_color"))
        logger.debug(
            "secondary_colors in cleaned_data: %s",
            cleaned_data.get("secondary_colors"),
        )
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
