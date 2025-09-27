from django import template

register = template.Library()


@register.filter
def to_hyphens(value):
    """Convert underscores to hyphens for design class names."""
    return value.replace("_", "-")
