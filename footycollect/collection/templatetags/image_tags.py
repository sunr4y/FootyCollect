# ruff: noqa: S308
from pathlib import Path

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def responsive_image(photo, css_class=""):
    original_url = photo.image.url if photo.image else ""

    # Only include AVIF source if the file actually exists
    avif_url = ""
    if photo.image_avif:
        try:
            if Path(photo.image_avif.path).exists():
                avif_url = photo.image_avif.url
        except (ValueError, AttributeError):
            pass

    if avif_url:
        html = f"""
        <picture>
            <source srcset="{avif_url}" type="image/avif">
            <img src="{original_url}" class="{css_class}" alt="{photo.caption}">
        </picture>
        """
    else:
        html = f'<img src="{original_url}" class="{css_class}" alt="{photo.caption}">'

    return mark_safe(html)
