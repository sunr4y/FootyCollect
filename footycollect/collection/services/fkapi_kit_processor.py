"""
FKAPI kit data processor for item creation.

Handles fetching kit data from FKAPI, populating form (name, description, colors),
and creating/updating TypeK. Used by ItemFKAPIService.
"""

import logging
from typing import Any

from footycollect.api.client import FKAPIClient
from footycollect.core.models import TypeK

logger = logging.getLogger(__name__)


class FKAPIKitProcessor:
    """Processes kit data from FKAPI and updates form instance."""

    def __init__(self, fkapi_client: FKAPIClient | None = None):
        self.fkapi_client = fkapi_client or FKAPIClient()

    def process_kit_data(self, form, kit_id: str) -> None:
        """Process kit data from FKAPI and update form instance."""
        try:
            kit_data = self.fetch_kit_data(kit_id)
            if not kit_data:
                return

            if not hasattr(form, "fkapi_data"):
                form.fkapi_data = {}
            form.fkapi_data.update(kit_data)

            self._add_kit_id_to_description(form, kit_id)
            self._process_kit_information(form, kit_data)

        except (ValueError, TypeError, KeyError, AttributeError):
            logger.exception("Error processing kit data for kit_id %s", kit_id)
            raise

    def fetch_kit_data(self, kit_id: str) -> dict[str, Any] | None:
        """Fetch kit data from FKAPI."""
        kit_data = self.fkapi_client.get_kit_details(kit_id)
        if kit_data is None:
            logger.warning("FKAPI unavailable for kit_id %s", kit_id)
        return kit_data

    def _add_kit_id_to_description(self, form, kit_id: str) -> None:
        """Add kit ID to description for reference."""
        current_description = form.cleaned_data.get("description", "")
        kit_reference = f"\n\n[Kit ID: {kit_id}]"

        if kit_reference not in current_description:
            form.cleaned_data["description"] = current_description + kit_reference

    def _process_kit_name(self, form, kit_data: dict[str, Any]) -> None:
        """Process kit name from API data."""
        if "name" in kit_data:
            form.cleaned_data["name"] = kit_data["name"]

    def _process_kit_description(self, form, kit_data: dict[str, Any]) -> None:
        """Process kit description from API data."""
        if "description" not in kit_data:
            return
        current_description = form.cleaned_data.get("description", "")
        api_description = kit_data["description"]
        if api_description and api_description not in current_description:
            form.cleaned_data["description"] = f"{current_description}\n\n{api_description}"

    def _process_kit_type(self, kit_data: dict[str, Any]) -> None:
        """Process kit type from API data."""
        type_obj = kit_data.get("type")
        if not type_obj:
            return

        if isinstance(type_obj, str):
            type_name = type_obj
            type_data = {}
        else:
            type_name = type_obj.get("name")
            type_data = type_obj

        if not type_name:
            return

        category = type_data.get("category", "match")
        if category == "jacket":
            logger.info("Skipping TypeK creation for jacket item: %s (handled as outerwear)", type_name)
            return

        logger.info("Processing kit type: %s", type_name)
        try:
            type_k = TypeK.objects.filter(name=type_name).first()
            if not type_k:
                type_k = TypeK.objects.filter(name__iexact=type_name).first()

            if type_k:
                self._update_existing_type_k(type_k, category, type_data, type_name)
            else:
                self._create_new_type_k(type_name, category, type_data)
        except Exception:
            logger.exception("Error creating kit type %s", type_name)

    def _update_existing_type_k(self, type_k: TypeK, category: str, type_data: dict[str, Any], type_name: str) -> None:
        """Update an existing TypeK object."""
        needs_update = False
        if category and type_k.category != category:
            type_k.category = category
            needs_update = True
        if "is_goalkeeper" in type_data and type_k.is_goalkeeper != type_data["is_goalkeeper"]:
            type_k.is_goalkeeper = type_data["is_goalkeeper"]
            needs_update = True

        if needs_update:
            type_k.save()
            logger.info("Updated kit type: %s (ID: %s)", type_name, type_k.id)
        else:
            logger.info("Found existing kit type: %s (ID: %s)", type_name, type_k.id)

    def _create_new_type_k(self, type_name: str, category: str, type_data: dict[str, Any]) -> None:
        """Create a new TypeK object."""
        type_k = TypeK.objects.create(
            name=type_name,
            category=category,
            is_goalkeeper=type_data.get("is_goalkeeper", False),
        )
        logger.info("Created new kit type: %s (ID: %s)", type_name, type_k.id)

    def _process_kit_information(self, form, kit_data: dict[str, Any]) -> None:
        """Process kit information from API data."""
        self._process_kit_name(form, kit_data)
        self._process_kit_description(form, kit_data)
        self._process_kit_type(kit_data)
        if "colors" in kit_data:
            self._process_kit_colors(form, kit_data["colors"])

    def _process_kit_colors(self, form, colors: list[dict[str, Any]]) -> None:
        """
        Process kit colors and set them in form.data (not cleaned_data).

        CRITICAL: Must set in form.data so clean methods can access via self.data
        Only set if not already present in POST data (POST data takes precedence)
        """
        if not colors:
            return

        if hasattr(form.data, "_mutable"):
            form.data._mutable = True  # noqa: SLF001
        else:
            form.data = form.data.copy()

        if not form.data.get("main_color"):
            main_color = colors[0].get("name", "")
            if main_color:
                form.data["main_color"] = main_color
                logger.info("Set main_color in form.data from API: %s", main_color)
        else:
            logger.info("main_color already in form.data: %s (keeping POST value)", form.data.get("main_color"))

        has_secondary_colors = form.data.get("secondary_colors") or (
            hasattr(form.data, "getlist") and form.data.getlist("secondary_colors")
        )
        if not has_secondary_colors:
            if len(colors) > 1:
                secondary_colors = [color.get("name", "") for color in colors[1:] if color.get("name")]
                if secondary_colors:
                    if hasattr(form.data, "setlist"):
                        form.data.setlist("secondary_colors", secondary_colors)
                    else:
                        form.data["secondary_colors"] = secondary_colors
                    logger.info("Set secondary_colors in form.data from API: %s", secondary_colors)
        else:
            existing = (
                form.data.getlist("secondary_colors")
                if hasattr(form.data, "getlist")
                else form.data.get("secondary_colors")
            )
            logger.info("secondary_colors already in form.data: %s (keeping POST value)", existing)
