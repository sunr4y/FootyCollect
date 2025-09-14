"""
Service for form-related business logic.

This service handles form data preparation and validation
for all item types (jersey, shorts, outerwear, etc.).
"""

from typing import Any

from footycollect.collection.models import BaseItem
from footycollect.collection.services.color_service import ColorService
from footycollect.collection.services.size_service import SizeService


class FormService:
    """
    Service for form-related business logic.

    This service handles form data preparation and validation
    for all item types (jersey, shorts, outerwear, etc.).
    """

    def __init__(self):
        self.color_service = ColorService()
        self.size_service = SizeService()

    def get_form_data_for_item_type(self, item_type: str = "jersey") -> dict[str, Any]:
        """
        Get form data for any item type.

        Args:
            item_type: Type of item (jersey, shorts, outerwear, etc.)

        Returns:
            Dictionary with form data
        """
        return {
            "color_choices": self._get_color_choices(),
            "size_choices": self._get_size_choices_for_item_type(item_type),
            "design_choices": self._get_design_choices(),
            "condition_choices": self._get_condition_choices(),
        }

    def _get_color_choices(self) -> list[dict[str, str | int]]:
        """Get color choices for forms."""
        return self.color_service.get_color_choices_for_forms()

    def _get_size_choices_for_item_type(self, item_type: str) -> list[dict[str, str | int]]:
        """Get size choices for specific item type."""
        sizes_data = self.size_service.get_sizes_for_item_form()
        # Get sizes for the specific item type category
        category = self._get_category_for_item_type(item_type)
        sizes = sizes_data.get(category, [])

        return [
            {
                "value": size["id"],
                "label": size["name"],
                "category": size["category"],
            }
            for size in sizes
        ]

    def _get_category_for_item_type(self, item_type: str) -> str:
        """Get the size category for a specific item type."""
        category_mapping = {
            "jersey": "tops",
            "shorts": "bottoms",
            "outerwear": "tops",
            "track_suit": "tops",
            "pants": "bottoms",
            "other": "other",
        }
        return category_mapping.get(item_type, "other")

    def _get_design_choices(self) -> list[dict[str, str]]:
        """Get design choices for forms."""
        return [{"value": value, "label": label} for value, label in BaseItem.DESIGN_CHOICES]

    def _get_condition_choices(self) -> list[dict[str, str]]:
        """Get condition choices for forms."""
        return [{"value": value, "label": label} for value, label in BaseItem.CONDITION_CHOICES]

    def get_common_form_data(self) -> dict[str, Any]:
        """
        Get common form data shared across all item types.

        Returns:
            Dictionary with common form data
        """
        return {
            "colors": {
                "main_colors": self._get_color_choices(),
                "secondary_colors": self._get_color_choices(),
            },
            "designs": self._get_design_choices(),
            "conditions": self._get_condition_choices(),
        }

    def get_item_type_specific_data(self, item_type: str) -> dict[str, Any]:
        """
        Get item type specific form data.

        Args:
            item_type: Type of item (jersey, shorts, outerwear, etc.)

        Returns:
            Dictionary with item type specific data
        """
        return {
            "sizes": self._get_size_choices_for_item_type(item_type),
            "item_type": item_type,
        }

    def validate_item_type(self, item_type: str) -> bool:
        """
        Validate if item type is supported.

        Args:
            item_type: Type of item to validate

        Returns:
            True if valid, False otherwise
        """
        valid_types = ["jersey", "shorts", "outerwear", "tracksuit", "pants", "other"]
        return item_type in valid_types

    def get_available_item_types(self) -> list[dict[str, str]]:
        """
        Get list of available item types.

        Returns:
            List of item types with labels
        """
        return [
            {"value": "jersey", "label": "Jersey"},
            {"value": "shorts", "label": "Shorts"},
            {"value": "outerwear", "label": "Outerwear"},
            {"value": "tracksuit", "label": "Tracksuit"},
            {"value": "pants", "label": "Pants"},
            {"value": "other", "label": "Other Item"},
        ]
