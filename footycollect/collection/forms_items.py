from django import forms

from footycollect.collection.forms_base import ItemTypeSpecificFormMixin
from footycollect.collection.models import BaseItem


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


__all__ = [
    "OtherItemForm",
    "OuterwearForm",
    "PantsForm",
    "ShortsForm",
    "TrackSuitForm",
]
