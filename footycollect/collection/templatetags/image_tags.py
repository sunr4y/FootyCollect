from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def responsive_image(photo, css_class=""):
    original_url = photo.image.url if photo.image else ""
    caption = escape(photo.caption or "")
    css_class_safe = escape(css_class)

    avif_url = ""
    if photo.image_avif:
        try:
            if photo.image_avif.storage.exists(photo.image_avif.name):
                avif_url = photo.image_avif.url
        except (ValueError, AttributeError, NotImplementedError):
            pass

    if avif_url:
        html = f"""
        <picture>
            <source srcset="{avif_url}" type="image/avif">
            <img src="{original_url}" class="{css_class_safe}" alt="{caption}">
        </picture>
        """
    else:
        html = f'<img src="{original_url}" class="{css_class_safe}" alt="{caption}">'

    return mark_safe(html)  # noqa: S308
