"""
Repository for color-related database operations.

This repository handles all database operations related to colors,
including main colors and secondary colors for items.
"""

from django.db import models
from django.db.models import QuerySet

from footycollect.collection.models import Color

from .base_repository import BaseRepository


class ColorRepository(BaseRepository):
    """
    Repository for color-related database operations.

    This repository provides specialized methods for working with colors
    and their related data.
    """

    def __init__(self):
        super().__init__(Color)

    def get_colors_by_hex(self, hex_value: str) -> QuerySet[Color]:
        """
        Get colors by hexadecimal value.

        Args:
            hex_value: Hexadecimal color value (e.g., '#FF0000')

        Returns:
            QuerySet of colors with the specified hex value
        """
        return self.model.objects.filter(hex_value__iexact=hex_value)

    def get_colors_by_name(self, name: str) -> QuerySet[Color]:
        """
        Get colors by name (case-insensitive).

        Args:
            name: Color name

        Returns:
            QuerySet of colors with the specified name
        """
        return self.model.objects.filter(name__icontains=name)

    def get_default_colors(self) -> QuerySet[Color]:
        """
        Get all default colors from the COLOR_MAP.

        Returns:
            QuerySet of default colors
        """
        default_names = list(Color.COLOR_MAP.keys())
        return self.model.objects.filter(name__in=default_names).order_by("id")

    def get_colors_by_category(self, category: str) -> QuerySet[Color]:
        """
        Get colors by category (if implemented in the future).

        Args:
            category: Color category

        Returns:
            QuerySet of colors in the specified category
        """
        # For now, return all colors since we don't have categories
        # This can be extended when color categories are implemented
        return self.model.objects.all()

    def get_popular_colors(self, limit: int = 10) -> QuerySet[Color]:
        """
        Get the most popular colors based on usage.

        Args:
            limit: Maximum number of colors to return

        Returns:
            QuerySet of popular colors
        """
        # This would need to be implemented based on actual usage data
        # For now, return default colors
        return self.get_default_colors()[:limit]

    def create_default_colors(self) -> int:
        """
        Create default colors from COLOR_MAP if they don't exist.

        Returns:
            Number of colors created
        """
        created_count = 0
        for name, hex_value in Color.COLOR_MAP.items():
            color, created = self.model.objects.get_or_create(
                name=name,
                defaults={"hex_value": hex_value},
            )
            if created:
                created_count += 1
        return created_count

    def get_colors_used_in_items(self) -> QuerySet[Color]:
        """
        Get colors that are actually used in items (as main or secondary colors).

        Returns:
            QuerySet of colors used in items
        """

        # Get colors used as main colors
        main_colors = self.model.objects.filter(
            baseitem__isnull=False,
        ).distinct()

        # Get colors used as secondary colors
        secondary_colors = self.model.objects.filter(
            collection_baseitem_secondary__isnull=False,
        ).distinct()

        # Combine and return unique colors
        return (main_colors | secondary_colors).distinct()

    def get_color_statistics(self) -> dict:
        """
        Get color usage statistics.

        Returns:
            Dictionary with color usage statistics
        """

        stats = {}

        # Count main colors usage
        main_color_usage = (
            self.model.objects.filter(
                baseitem__isnull=False,
            )
            .values("name", "hex_value")
            .annotate(
                count=models.Count("baseitem"),
            )
            .order_by("-count")
        )

        # Count secondary colors usage
        secondary_color_usage = (
            self.model.objects.filter(
                collection_baseitem_secondary__isnull=False,
            )
            .values("name", "hex_value")
            .annotate(
                count=models.Count("collection_baseitem_secondary"),
            )
            .order_by("-count")
        )

        stats["main_colors"] = list(main_color_usage)
        stats["secondary_colors"] = list(secondary_color_usage)
        stats["total_colors"] = self.model.objects.count()
        stats["used_colors"] = self.get_colors_used_in_items().count()

        return stats
