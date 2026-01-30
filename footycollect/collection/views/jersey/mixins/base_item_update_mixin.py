"""
Mixin for updating BaseItem with country and color data.

This mixin provides methods to update BaseItem instances with
country, main_color, and secondary_colors from form data or POST.
"""

import logging

from footycollect.collection.models import Color

logger = logging.getLogger(__name__)


class BaseItemUpdateMixin:
    """Mixin for BaseItem update functionality."""

    def _update_base_item_country(self, base_item, country_code_post, form):
        """Update BaseItem country if missing."""
        if base_item.country:
            return False

        logger.info("BaseItem has no country, trying to set it...")
        country_code = country_code_post
        logger.info("country_code from stored POST: %s", country_code)
        if not country_code:
            country_code = form.cleaned_data.get("country_code")
            logger.info("country_code from cleaned_data: %s", country_code)
        has_fkapi_data = hasattr(self, "fkapi_data") and self.fkapi_data and "team_country" in self.fkapi_data
        if not country_code and has_fkapi_data:
            country_code = self.fkapi_data["team_country"]
            logger.info("country_code from fkapi_data: %s", country_code)

        if not country_code:
            logger.warning("No country_code found in any source")
            return False

        try:
            base_item.country = country_code
            logger.info("Set country on BaseItem: %s", country_code)
        except (ValueError, TypeError, AttributeError):
            logger.exception("Error setting country")
            return False
        else:
            return True

    def _update_base_item_main_color(self, base_item, main_color_post, form):
        """Update BaseItem main_color if missing."""
        if base_item.main_color:
            return False

        logger.info("BaseItem has no main_color, trying to set it...")
        main_color = form.cleaned_data.get("main_color")
        logger.info("main_color from cleaned_data: %s", main_color)
        if not main_color and main_color_post:
            main_color_str = main_color_post
            logger.info("main_color_str from stored POST: %s", main_color_str)
            if main_color_str:
                try:
                    color_obj, _created = Color.objects.get_or_create(
                        name__iexact=main_color_str.strip(),
                        defaults={"name": main_color_str.strip().upper()},
                    )
                    main_color = color_obj
                    logger.info("Created/found Color object: %s (ID: %s)", color_obj.name, color_obj.id)
                except (ValueError, TypeError):
                    logger.exception("Error creating/finding main Color")

        if not main_color:
            logger.warning("No main_color found in any source")
            return False

        base_item.main_color = main_color
        logger.info("Set main_color on BaseItem: %s", main_color.name)
        return True

    def _process_secondary_colors_from_post(self, secondary_colors_post):
        """Process secondary colors from POST data into Color objects."""
        if not secondary_colors_post:
            return []

        secondary_colors_raw = secondary_colors_post
        logger.info(
            "secondary_colors_raw from stored POST: %s (type: %s)",
            secondary_colors_raw,
            type(secondary_colors_raw),
        )

        if isinstance(secondary_colors_raw, str):
            secondary_colors_raw = [c.strip() for c in secondary_colors_raw.split(",") if c.strip()]
        elif not isinstance(secondary_colors_raw, list):
            secondary_colors_raw = []

        logger.info("Processed secondary_colors_raw: %s", secondary_colors_raw)
        if not secondary_colors_raw:
            return []

        color_objects = []
        for color_str in secondary_colors_raw:
            if isinstance(color_str, str) and color_str.strip():
                try:
                    color_obj, _created = Color.objects.get_or_create(
                        name__iexact=color_str.strip(),
                        defaults={"name": color_str.strip().upper()},
                    )
                    color_objects.append(color_obj)
                    logger.info("Created/found Color object: %s (ID: %s)", color_obj.name, color_obj.id)
                except (ValueError, TypeError):
                    logger.exception("Error creating/finding secondary Color")
        return color_objects

    def _update_base_item_secondary_colors(self, base_item, secondary_colors_post, form):
        """Update BaseItem secondary_colors if missing."""
        if base_item.secondary_colors.exists():
            return False

        logger.info("BaseItem has no secondary_colors, trying to set them...")
        secondary_colors = form.cleaned_data.get("secondary_colors", [])
        logger.info("secondary_colors from cleaned_data: %s", secondary_colors)

        if not secondary_colors and secondary_colors_post:
            secondary_colors = self._process_secondary_colors_from_post(secondary_colors_post)

        if not secondary_colors:
            logger.warning("No secondary_colors found in any source")
            return False

        base_item.secondary_colors.set(secondary_colors)
        logger.info("Set secondary_colors on BaseItem: %s", [c.name for c in secondary_colors])
        return True
