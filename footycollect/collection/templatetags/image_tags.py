# ruff: noqa: S308
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def responsive_image(photo, css_class=""):
    avif_url = photo.image_avif.url if photo.image_avif else ""
    original_url = photo.image.url

    html = f"""
    <picture>
        <source srcset="{avif_url}" type="image/avif">
        <img src="{original_url}" class="{css_class}" alt="{photo.caption}">
    </picture>
    """
    return mark_safe(html)
