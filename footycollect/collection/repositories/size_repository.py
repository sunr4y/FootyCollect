"""
Repository for size-related database operations.

This repository handles all database operations related to sizes,
including tops, bottoms, and other size categories.
"""

from django.db.models import Count, QuerySet

from footycollect.collection.models import Size

from .base_repository import BaseRepository


class SizeRepository(BaseRepository):
    """
    Repository for size-related database operations.

    This repository provides specialized methods for working with sizes
    and their related data.
    """

    def __init__(self):
        super().__init__(Size)

    @staticmethod
    def _clamp_limit(limit: int, min_val: int = 1, max_val: int = 500) -> int:
        return max(min_val, min(limit, max_val))

    def get_sizes_by_category(self, category: str) -> QuerySet[Size]:
        """
        Get sizes by category.

        Args:
            category: Size category ('tops', 'bottoms', 'other')

        Returns:
            QuerySet of sizes in the specified category
        """
        return self.model.objects.filter(category=category).order_by("name")

    def get_tops_sizes(self) -> QuerySet[Size]:
        """
        Get all sizes for tops.

        Returns:
            QuerySet of tops sizes
        """
        return self.get_sizes_by_category("tops")

    def get_bottoms_sizes(self) -> QuerySet[Size]:
        """
        Get all sizes for bottoms.

        Returns:
            QuerySet of bottoms sizes
        """
        return self.get_sizes_by_category("bottoms")

    def get_other_sizes(self) -> QuerySet[Size]:
        """
        Get all sizes for other items.

        Returns:
            QuerySet of other sizes
        """
        return self.get_sizes_by_category("other")

    def get_size_by_name_and_category(self, name: str, category: str) -> Size | None:
        """
        Get a specific size by name and category.

        Args:
            name: Size name
            category: Size category

        Returns:
            Size instance or None if not found
        """
        try:
            return self.model.objects.get(name=name, category=category)
        except self.model.DoesNotExist:
            return None

    def get_sizes_by_name(self, query: str) -> QuerySet[Size]:
        """
        Get sizes whose name contains the query (case-insensitive).

        Args:
            query: Search string

        Returns:
            QuerySet of matching sizes
        """
        return self.model.objects.filter(name__icontains=query).order_by("name")

    def get_size_distribution_by_category(self) -> dict[str, int]:
        """
        Get count of sizes per category.

        Returns:
            Dictionary mapping category to count
        """
        return {r["category"]: r["count"] for r in self.model.objects.values("category").annotate(count=Count("id"))}

    def get_most_used_sizes_by_category(self, category: str, limit: int = 5) -> QuerySet[Size]:
        """
        Get most used sizes in a category (by jersey usage count).

        Args:
            category: Size category
            limit: Maximum number of sizes to return

        Returns:
            QuerySet of Size with usage_count annotated
        """
        limit = self._clamp_limit(limit)
        return (
            self.model.objects.filter(category=category)
            .annotate(usage_count=Count("jersey"))
            .order_by("-usage_count")[:limit]
        )

    def get_popular_sizes(self, category: str | None = None, limit: int = 10) -> QuerySet[Size]:
        """
        Get the most popular sizes based on usage.

        Args:
            category: Optional size category filter
            limit: Maximum number of sizes to return

        Returns:
            QuerySet of popular sizes
        """
        limit = self._clamp_limit(limit)
        queryset = self.model.objects.all()

        if category:
            queryset = queryset.filter(category=category)

        # This would need to be implemented based on actual usage data
        # For now, return sizes ordered by name
        return queryset.order_by("name")[:limit]

    def create_default_sizes(self) -> int:
        """
        Create default sizes for each category if they don't exist.

        Returns:
            Number of sizes created
        """
        default_sizes = {
            "tops": ["XS", "S", "M", "L", "XL", "XXL", "XXXL"],
            "bottoms": ["28", "30", "32", "34", "36", "38", "40", "42", "44", "46"],
            "other": ["One Size", "Small", "Medium", "Large", "Extra Large"],
        }

        created_count = 0
        for category, sizes in default_sizes.items():
            for size_name in sizes:
                size, created = self.model.objects.get_or_create(
                    name=size_name,
                    category=category,
                )
                if created:
                    created_count += 1
        return created_count

    def get_sizes_used_in_items(self, category: str | None = None) -> QuerySet[Size]:
        """
        Get sizes that are actually used in items.

        Args:
            category: Optional size category filter

        Returns:
            QuerySet of sizes used in items
        """

        queryset = self.model.objects.filter(jersey__isnull=False).distinct()

        if category:
            queryset = queryset.filter(category=category)

        return queryset

    def get_size_statistics(self) -> dict:
        """
        Get size usage statistics.

        Returns:
            Dictionary with size usage statistics
        """
        from django.db import models

        stats = {}

        # Count sizes usage by category
        for category, _ in Size.CATEGORY_CHOICES:
            category_sizes = (
                self.model.objects.filter(
                    category=category,
                    jersey__isnull=False,
                )
                .values("name")
                .annotate(
                    count=models.Count("jersey"),
                )
                .order_by("-count")
            )

            stats[category] = list(category_sizes)

        stats["total_sizes"] = self.model.objects.count()
        stats["used_sizes"] = self.get_sizes_used_in_items().count()

        return stats

    def get_sizes_for_item_type(self, item_type: str) -> QuerySet[Size]:
        """
        Get appropriate sizes for a specific item type.

        Args:
            item_type: Item type ('jersey', 'shorts', 'outerwear', etc.)

        Returns:
            QuerySet of appropriate sizes for the item type
        """
        # Map item types to size categories
        item_type_mapping = {
            "jersey": "tops",
            "shorts": "bottoms",
            "outerwear": "tops",
            "tracksuit": "tops",  # Assuming tracksuit tops
            "pants": "bottoms",
            "other": "other",
        }

        category = item_type_mapping.get(item_type, "other")
        return self.get_sizes_by_category(category)
