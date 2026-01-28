"""
Mixin for processing color values from POST data.

This mixin provides methods to extract and process color values
from request.POST data.
"""

import logging

logger = logging.getLogger(__name__)


class ColorProcessingMixin:
    """Mixin for color processing functionality."""

    def _get_post_color_values(self):
        """Extract color values from POST data."""
        main_color_post = self.request.POST.get("main_color")
        secondary_colors_post = (
            self.request.POST.getlist("secondary_colors") if hasattr(self.request.POST, "getlist") else []
        )
        if not secondary_colors_post:
            secondary_colors_post = self.request.POST.get("secondary_colors")
            if secondary_colors_post and isinstance(secondary_colors_post, str):
                secondary_colors_post = [c.strip() for c in secondary_colors_post.split(",") if c.strip()]
        return main_color_post, secondary_colors_post

    def _is_string_list(self, value):
        """Check if value is a list of strings."""
        if not value:
            return False
        try:
            if hasattr(value, "__getitem__") and len(value) > 0:
                return isinstance(value[0], str)
        except (TypeError, IndexError, AttributeError):
            pass
        return False

    def _get_secondary_colors_from_sources(self, secondary_colors_post, form):
        """Get secondary colors from POST or form data."""
        if secondary_colors_post:
            return secondary_colors_post
        if hasattr(form.data, "getlist"):
            return form.data.getlist("secondary_colors")
        return form.data.get("secondary_colors", [])

    def _convert_secondary_colors_to_objects(self, secondary_colors_val):
        """Convert secondary colors list to Color objects."""
        from footycollect.collection.models import Color

        if isinstance(secondary_colors_val, str):
            secondary_colors_val = [c.strip() for c in secondary_colors_val.split(",") if c.strip()]

        color_objects = []
        for color in secondary_colors_val:
            if isinstance(color, str):
                color_obj, _created = Color.objects.get_or_create(
                    name__iexact=color.strip(),
                    defaults={"name": color.strip().upper()},
                )
                color_objects.append(color_obj)
            elif isinstance(color, Color):
                color_objects.append(color)
        return color_objects
