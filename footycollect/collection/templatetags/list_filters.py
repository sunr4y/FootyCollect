import json

from django import template

register = template.Library()


@register.filter
def contains(value, arg):
    """Check if value is in arg (list/iterable)."""
    if not value or not arg:
        return False
    try:
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
