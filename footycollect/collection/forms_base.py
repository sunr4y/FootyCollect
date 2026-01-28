from dal import autocomplete
from django import forms
from django.utils.translation import gettext_lazy as _

from footycollect.collection.services import FormService

from .form_fields import BrandWidget
from .models import BaseItem


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

        try:
            form_service = FormService()
            form_data = form_service.get_common_form_data()

            self.fields["main_color"].widget.attrs["data-choices"] = form_data["colors"]["main_colors"]
            self.fields["secondary_colors"].widget.attrs["data-choices"] = form_data["colors"]["secondary_colors"]
            self.fields["design"].widget.attrs["data-choices"] = form_data["designs"]

        except (ImportError, RuntimeError):
            self.fields["main_color"].widget.attrs["data-choices"] = []
            self.fields["secondary_colors"].widget.attrs["data-choices"] = []
            self.fields["design"].widget.attrs["data-choices"] = []

        for field in self.fields.values():
            if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs["class"] = "form-select"


class ItemTypeSpecificFormMixin:
    """Mixin for forms that need item type specific data."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        item_type = getattr(self.Meta, "item_type", "jersey")

        try:
            form_service = FormService()
            item_data = form_service.get_item_type_specific_data(item_type)

            if "size" in self.fields:
                self.fields["size"].widget.attrs["data-choices"] = item_data["sizes"]

        except (ImportError, RuntimeError):
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


__all__ = [
    "BaseItemForm",
    "ItemTypeSpecificFormMixin",
    "ItemTypeForm",
]
