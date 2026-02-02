from dal import autocomplete
from django import forms
from django.utils.translation import gettext_lazy as _
from django_countries import countries

from footycollect.core.models import Brand

from .form_fields import (
    BrandWidget,
    ColorModelChoiceField,
    ColorModelMultipleChoiceField,
    MultipleFileField,
    MultipleFileInput,
)
from .forms_base import (
    BaseItemForm,
    ItemTypeForm,
    ItemTypeSpecificFormMixin,
)
from .forms_items import (
    OtherItemForm,
    OuterwearForm,
    PantsForm,
    ShortsForm,
    TrackSuitForm,
)
from .forms_jersey_base import JerseyForm
from .forms_jersey_fkapi import JerseyFKAPIForm

MAX_PHOTOS = 10


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
                "data-placeholder": "Select a country...",
            },
        ),
    )


class TestBrandForm(forms.Form):
    """Form simple to test Select2 with Brand"""

    brand = forms.ModelChoiceField(
        queryset=Brand.objects.none(),  # Will be set in __init__
        widget=autocomplete.ModelSelect2(
            url="core:brand-autocomplete",
            attrs={
                "data-placeholder": "Search for brand...",
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


__all__ = [
    "MAX_PHOTOS",
    "BaseItemForm",
    "BrandWidget",
    "ColorModelChoiceField",
    "ColorModelMultipleChoiceField",
    "ItemPhotosForm",
    "ItemTypeForm",
    "ItemTypeSpecificFormMixin",
    "JerseyFKAPIForm",
    "JerseyForm",
    "MultipleFileField",
    "MultipleFileInput",
    "OtherItemForm",
    "OuterwearForm",
    "PantsForm",
    "ShortsForm",
    "TestBrandForm",
    "TestCountryForm",
    "TrackSuitForm",
]
