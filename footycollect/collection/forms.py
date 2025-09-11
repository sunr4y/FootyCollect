from dal import autocomplete
from dal_select2 import widgets as select2_widgets
from django import forms
from django.utils.translation import gettext_lazy as _
from django_countries import countries

from footycollect.core.models import Brand, Club, Season

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
            "competitions": forms.SelectMultiple(),
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

        # Prepare color choices for the color selector component (lazy loading)
        try:
            color_choices = [
                {
                    "value": color.id,
                    "label": color.name,
                    "hex_value": color.hex_value,
                }
                for color in Color.objects.all()
            ]
        except (ImportError, RuntimeError):
            # During tests or when database is not ready, use empty list
            color_choices = []

        # Set choices for color fields
        self.fields["main_color"].widget.attrs["data-choices"] = color_choices
        self.fields["secondary_colors"].widget.attrs["data-choices"] = color_choices

        # Prepare design choices
        design_choices = []
        for value, label in BaseItem.DESIGN_CHOICES:
            design_choices.append(
                {
                    "value": value,
                    "label": label,
                },
            )
        self.fields["design"].widget.attrs["data-choices"] = design_choices

        # Add class to all select fields
        for field in self.fields.values():
            if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs["class"] = "form-select"


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


class JerseyForm(forms.Form):
    """Form for Jersey items using MTI structure."""

    # BaseItem fields
    name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    brand = forms.ModelChoiceField(
        queryset=Brand.objects.all(),
        required=True,
        widget=BrandWidget(),
    )

    club = forms.ModelChoiceField(
        queryset=Club.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    season = forms.ModelChoiceField(
        queryset=Season.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

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
    size = forms.ModelChoiceField(
        queryset=Size.objects.none(),  # Will be set in __init__
        label=_("Size"),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

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

    def __init__(self, *args, **kwargs):
        # Remove instance and user from kwargs for BaseForm
        instance = kwargs.pop("instance", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.instance = instance

        # Set the size queryset (lazy loading)
        try:
            self.fields["size"].queryset = Size.objects.filter(category="tops")
        except (ImportError, RuntimeError):
            # During tests or when database is not ready, use empty queryset
            self.fields["size"].queryset = Size.objects.none()

        self.fields["player_name"].widget.attrs["class"] = "form-control col-md-8"
        self.fields["number"].widget.attrs["class"] = "form-control col-md-4"

    def _extract_base_item_data(self):
        """Extract data for BaseItem creation."""
        base_item_fields = [
            "name",
            "item_type",
            "user",
            "brand",
            "club",
            "season",
            "condition",
            "detailed_condition",
            "description",
            "is_replica",
            "main_color",
            "design",
            "country",
        ]

        base_item_data = {}
        for field in base_item_fields:
            if field in self.cleaned_data:
                base_item_data[field] = self.cleaned_data[field]

        # Ensure user is set
        if self.user:
            base_item_data["user"] = self.user

        # Handle country_code mapping
        country_code = self.cleaned_data.get("country_code")
        if country_code:
            base_item_data["country"] = country_code

        # Set item_type
        base_item_data["item_type"] = "jersey"

        return base_item_data

    def _extract_jersey_data(self):
        """Extract data for Jersey creation."""
        jersey_fields = [
            "size",
            "kit",
            "is_fan_version",
            "is_signed",
            "has_nameset",
            "player_name",
            "number",
            "is_short_sleeve",
        ]

        jersey_data = {}
        for field in jersey_fields:
            if field in self.cleaned_data:
                jersey_data[field] = self.cleaned_data[field]

        return jersey_data

    def _extract_many_to_many_data(self):
        """Extract ManyToMany fields data."""
        many_to_many_fields = ["competitions", "secondary_colors"]
        many_to_many_data = {}
        for field in many_to_many_fields:
            if field in self.cleaned_data:
                many_to_many_data[field] = self.cleaned_data[field]
        return many_to_many_data

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
            jersey = Jersey.objects.create(**jersey_data)

            # Handle ManyToMany fields
            if "competitions" in many_to_many_data:
                base_item.competitions.set(many_to_many_data["competitions"])
            if "secondary_colors" in many_to_many_data:
                base_item.secondary_colors.set(many_to_many_data["secondary_colors"])

            return jersey
        # For non-commit case, create instances but don't save
        base_item = BaseItem(**base_item_data)
        jersey_data["base_item"] = base_item
        return Jersey(**jersey_data)


class JerseyFKAPIForm(JerseyForm):
    """Formulario mejorado para crear jerseys con integración de FKAPI"""

    # Campos adicionales para búsqueda (no se guardan en el modelo)
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

    # Campo para almacenar URLs de imágenes externas
    external_image_urls = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        # Remove instance from kwargs for BaseForm
        instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)
        self.instance = instance

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
        secondary_colors_names = self.data.getlist("secondary_colors")
        if not secondary_colors_names and self.data.get("secondary_colors"):
            secondary_colors_names = [self.data.get("secondary_colors")]

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


# TODO: Implement OuterwearForm with MTI structure
# class OuterwearForm(forms.Form):
#     pass


# TODO: Implement ShortsForm with MTI structure
# class ShortsForm(forms.Form):
#     pass


# TODO: Implement TrackSuitForm with MTI structure
# class TrackSuitForm(forms.Form):
#     pass


# TODO: Implement PantsForm with MTI structure
# class PantsForm(forms.Form):
#     pass


# TODO: Implement OtherItemForm with MTI structure
# class OtherItemForm(forms.Form):
#     pass


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
        # Convertir a lista si es un solo archivo
        if not isinstance(photos, list):
            photos = [photos] if photos else []

        if len(photos) > MAX_PHOTOS:
            raise forms.ValidationError(
                _("You can't upload more than %d photos.") % MAX_PHOTOS,
            )
        return photos


class TestCountryForm(forms.Form):
    """Form simple para probar la integración de Select2 con Countries"""

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
