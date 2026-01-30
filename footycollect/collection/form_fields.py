from dal_select2 import widgets as select2_widgets
from django import forms
from django.core.exceptions import ValidationError

from footycollect.core.models import Brand

from .models import Color


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
        try:
            return super().to_python(value)
        except ValidationError:
            try:
                return Color.objects.get(name__iexact=str(value).strip())
            except Color.DoesNotExist:
                return str(value).strip()


class ColorModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    """ModelMultipleChoiceField that accepts color names as strings."""

    def to_python(self, value):
        """Override to handle color names in addition to IDs."""
        if value in self.empty_values:
            return []
        if isinstance(value, (list, tuple)):
            result = []
            for v in value:
                if not v:
                    continue
                if isinstance(v, Color):
                    result.append(v)
                    continue
                try:
                    color_id = int(v)
                    color_obj = Color.objects.get(id=color_id)
                    result.append(color_obj)
                    continue
                except (ValueError, TypeError, Color.DoesNotExist):
                    pass
                result.append(str(v).strip())
            return result
        if isinstance(value, Color):
            return [value]
        try:
            color_id = int(value)
            color_obj = Color.objects.get(id=color_id)
        except (ValueError, TypeError, Color.DoesNotExist):
            pass
        else:
            return [color_obj]
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
                "data-placeholder": "Search for brand...",
            },
        )
        return attrs


__all__ = [
    "ColorModelChoiceField",
    "ColorModelMultipleChoiceField",
    "MultipleFileInput",
    "MultipleFileField",
    "BrandWidget",
]
