from dal import autocomplete
from dal_select2 import widgets as select2_widgets
from django import forms
from django.utils.translation import gettext_lazy as _
from django_countries import countries

from footycollect.core.models import Brand

from .models import Jersey
from .models import OtherItem
from .models import Outerwear
from .models import Pants
from .models import Shorts
from .models import Size
from .models import Tracksuit

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

    class Meta:
        model = Jersey
        fields = [
            "brand",
            "club",
            "season",
            "competition",
            "condition",
            "detailed_condition",
            "description",
            "is_replica",
            "country_code",
            "main_color",
            "secondary_colors",
        ]
        widgets = {
            "brand": BrandWidget(),
            "club": forms.Select(),
            "season": forms.Select(),
            "competition": forms.Select(),
            "main_color": forms.Select(
                attrs={
                    "class": "form-select color-select",
                    "data-colors": True,
                },
            ),
            "secondary_colors": autocomplete.Select2Multiple(
                attrs={
                    "class": "form-select color-select",
                    "data-colors": True,
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        queryset=Size.objects.filter(category="tops"),
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
        queryset=Brand.objects.all(),
        widget=autocomplete.ModelSelect2(
            url="core:brand-autocomplete",
            attrs={
                "data-placeholder": "Buscar marca...",
                "data-minimum-input-length": 0,
            },
        ),
    )
