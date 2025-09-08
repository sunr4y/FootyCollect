from dal import autocomplete
from dal_select2 import widgets as select2_widgets
from django import forms
from django.utils.translation import gettext_lazy as _
from django_countries import countries

from footycollect.core.models import Brand

from .models import BaseItem, Color, Jersey, OtherItem, Outerwear, Pants, Shorts, Size, Tracksuit

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

    country_code = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

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
        model = Jersey
        fields = [
            "brand",
            "club",
            "season",
            "competitions",
            "condition",
            "detailed_condition",
            "description",
            "is_replica",
            "country_code",
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


class JerseyForm(forms.ModelForm):
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

    is_player_version = forms.BooleanField(
        required=False,
        label=_("Player Version"),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input toggle-switch"}),
    )

    is_signed = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input toggle-switch"}),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the size queryset (lazy loading)
        try:
            self.fields["size"].queryset = Size.objects.filter(category="tops")
        except (ImportError, RuntimeError):
            # During tests or when database is not ready, use empty queryset
            self.fields["size"].queryset = Size.objects.none()

        self.fields["player_name"].widget.attrs["class"] = "form-control col-md-8"
        self.fields["number"].widget.attrs["class"] = "form-control col-md-4"

    class Meta(BaseItemForm.Meta):
        model = Jersey
        fields = [
            *BaseItemForm.Meta.fields,
            "size",
            "is_fan_version",
            "is_player_version",
            "is_signed",
            "player_name",
            "number",
            "is_short_sleeve",
            "country_code",
        ]

        widgets = {
            **BaseItemForm.Meta.widgets,
            "player_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Player Name"),
                },
            ),
            "country_code": autocomplete.Select2(
                url="core:country-autocomplete",
                attrs={
                    "data-html": True,
                    "data-placeholder": _("Select a country..."),
                    "class": "form-control select2",
                    "data-debug": "true",
                },
            ),
        }


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
        super().__init__(*args, **kwargs)

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


class OuterwearForm(BaseItemForm):
    class Meta(BaseItemForm.Meta):
        model = Outerwear
        fields = [*BaseItemForm.Meta.fields, "type"]


class ShortsForm(BaseItemForm):
    class Meta(BaseItemForm.Meta):
        model = Shorts
        fields = [*BaseItemForm.Meta.fields, "number", "is_fan_version"]


class TrackSuitForm(BaseItemForm):
    class Meta(BaseItemForm.Meta):
        model = Tracksuit
        fields = [*BaseItemForm.Meta.fields]


class PantsForm(BaseItemForm):
    class Meta(BaseItemForm.Meta):
        model = Pants
        fields = [*BaseItemForm.Meta.fields]


class OtherItemForm(BaseItemForm):
    class Meta(BaseItemForm.Meta):
        model = OtherItem
        fields = [*BaseItemForm.Meta.fields, "type"]


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
