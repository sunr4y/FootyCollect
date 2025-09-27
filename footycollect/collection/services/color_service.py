"""
Service for color-related business logic.

This service handles complex business operations related to colors,
including color management and statistics.
"""

from django.db.models import QuerySet

from footycollect.collection.models import Color
from footycollect.collection.repositories import ColorRepository


class ColorService:
    """
    Service for color-related business logic.

    This service handles complex operations related to color management,
    including color creation, statistics, and validation.
    """

    def __init__(self):
        self.color_repository = ColorRepository()

    def initialize_default_colors(self) -> int:
        """
        Initialize default colors from COLOR_MAP.

        Returns:
            Number of colors created
        """
        return self.color_repository.create_default_colors()

    def get_colors_for_item_form(self) -> dict[str, list[dict[str, str]]]:
        """
        Get colors organized for item forms.

        Returns:
            Dictionary with colors organized by category
        """
        default_colors = self.color_repository.get_default_colors()

        return {
            "main_colors": [
                {"value": color.name, "label": color.name, "hex_value": color.hex_value} for color in default_colors
            ],
            "secondary_colors": [
                {"value": color.name, "label": color.name, "hex_value": color.hex_value} for color in default_colors
            ],
        }

    def get_color_statistics(self) -> dict[str, any]:
        """
        Get comprehensive color statistics.

        Returns:
            Dictionary with color usage statistics
        """
        return self.color_repository.get_color_statistics()

    def get_popular_colors(self, limit: int = 10) -> QuerySet[Color]:
        """
        Get most popular colors based on usage.

        Args:
            limit: Maximum number of colors to return

        Returns:
            QuerySet of popular colors
        """
        return self.color_repository.get_popular_colors(limit)

    def get_colors_used_in_collection(self) -> QuerySet[Color]:
        """
        Get colors that are actually used in the collection.

        Returns:
            QuerySet of colors used in items
        """
        return self.color_repository.get_colors_used_in_items()

    def search_colors(self, query: str) -> QuerySet[Color]:
        """
        Search colors by name or hex value.

        Args:
            query: Search query

        Returns:
            QuerySet of matching colors
        """
        # Search by name
        name_results = self.color_repository.get_colors_by_name(query)

        # Search by hex value
        hex_results = self.color_repository.get_colors_by_hex(query)

        # Combine results and remove duplicates
        return (name_results | hex_results).distinct()

    def get_color_by_hex(self, hex_value: str) -> Color | None:
        """
        Get a color by its hex value.

        Args:
            hex_value: Hexadecimal color value

        Returns:
            Color instance or None if not found
        """
        colors = self.color_repository.get_colors_by_hex(hex_value)
        return colors.first() if colors.exists() else None

    def get_color_by_name(self, name: str) -> Color | None:
        """
        Get a color by its name.

        Args:
            name: Color name

        Returns:
            Color instance or None if not found
        """
        return self.color_repository.get_by_field("name", name)

    def create_custom_color(self, name: str, hex_value: str) -> Color:
        """
        Create a custom color.

        Args:
            name: Color name
            hex_value: Hexadecimal color value

        Returns:
            Created color instance

        Raises:
            ValueError: If color data is invalid
        """
        # Validate hex value format
        if not self._is_valid_hex(hex_value):
            error_msg = "Invalid hex value format"
            raise ValueError(error_msg)

        # Check if color already exists
        existing_color = self.get_color_by_hex(hex_value)
        if existing_color:
            error_msg = "Color with this hex value already exists"
            raise ValueError(error_msg)

        return self.color_repository.create(name=name, hex_value=hex_value)

    def get_colors_for_api(self) -> list[dict[str, str]]:
        """
        Get colors formatted for API responses.

        Returns:
            List of color dictionaries
        """
        colors = self.color_repository.get_all()
        return [
            {
                "id": color.id,
                "name": color.name,
                "hex_value": color.hex_value,
            }
            for color in colors
        ]

    def get_color_usage_analytics(self) -> dict[str, any]:
        """
        Get detailed color usage analytics.

        Returns:
            Dictionary with detailed color analytics
        """
        stats = self.get_color_statistics()

        # Add additional analytics
        total_colors = self.color_repository.count()
        used_colors = self.get_colors_used_in_collection().count()

        return {
            **stats,
            "total_colors": total_colors,
            "used_colors": used_colors,
            "unused_colors": total_colors - used_colors,
            "usage_percentage": (used_colors / total_colors * 100) if total_colors > 0 else 0,
        }

    def _is_valid_hex(self, hex_value: str) -> bool:
        """
        Validate hex color value format.

        Args:
            hex_value: Hexadecimal color value

        Returns:
            True if valid, False otherwise
        """
        import re

        pattern = r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
        return bool(re.match(pattern, hex_value))

    def get_color_choices_for_forms(self) -> list[dict[str, str | int]]:
        """
        Get color choices formatted for forms.

        Returns:
            List of color choices with value, label, and hex_value
        """
        colors = self.color_repository.get_all()

        return [
            {
                "value": color.id,
                "label": color.name,
                "hex_value": color.hex_value,
            }
            for color in colors
        ]
