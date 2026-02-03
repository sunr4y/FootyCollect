import json

from django import template

from footycollect.collection.utils_i18n import get_color_display_name

register = template.Library()


@register.filter
def color_display(name):
    return get_color_display_name(name)


@register.filter
def contains(value, arg):
    """Check if value is in arg (list/iterable or comma-separated string)."""
    if not value or not arg:
        return False
    try:
        # If arg is a string, treat it as comma-separated values
        if isinstance(arg, str):
            arg_list = [item.strip() for item in arg.split(",") if item.strip()]
            return str(value) in arg_list
        # If arg is iterable (list, tuple, etc.), convert to list of strings
        return str(value) in [str(item) for item in arg]
    except (TypeError, ValueError):
        return False


@register.filter
def parse_json(value):
    """Parse JSON string to Python object, or return value if already parsed."""
    if value is None:
        return []
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, bool):
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    return []
