"""
Service for size-related business logic.

This service handles complex business operations related to sizes,
including size management and statistics.
"""

from django.db.models import QuerySet

from footycollect.collection.models import Size
from footycollect.collection.repositories import SizeRepository


class SizeService:
    """
    Service for size-related business logic.

    This service handles complex operations related to size management,
    including size creation, statistics, and validation.
    """

    def __init__(self):
        self.size_repository = SizeRepository()

    def initialize_default_sizes(self) -> int:
        """
        Initialize default sizes for all categories.

        Returns:
            Number of sizes created
        """
        return self.size_repository.create_default_sizes()

    def get_sizes_for_item_form(self) -> dict[str, list[dict[str, str]]]:
        """
        Get sizes organized for item forms.

        Returns:
            Dictionary with sizes organized by category
        """
        tops_sizes = self.size_repository.get_sizes_by_category("tops")
        bottoms_sizes = self.size_repository.get_sizes_by_category("bottoms")
        accessories_sizes = self.size_repository.get_sizes_by_category("accessories")

        return {
            "tops": [{"id": size.id, "name": size.name, "category": size.category} for size in tops_sizes],
            "bottoms": [{"id": size.id, "name": size.name, "category": size.category} for size in bottoms_sizes],
            "accessories": [
                {"id": size.id, "name": size.name, "category": size.category} for size in accessories_sizes
            ],
        }

    def get_size_statistics(self) -> dict[str, any]:
        """
        Get comprehensive size statistics.

        Returns:
            Dictionary with size usage statistics
        """
        return self.size_repository.get_size_statistics()

    def get_popular_sizes(self, limit: int = 10) -> QuerySet[Size]:
        """
        Get most popular sizes based on usage.

        Args:
            limit: Maximum number of sizes to return

        Returns:
            QuerySet of popular sizes
        """
        return self.size_repository.get_popular_sizes(limit)

    def get_sizes_used_in_collection(self) -> QuerySet[Size]:
        """
        Get sizes that are actually used in the collection.

        Returns:
            QuerySet of sizes used in items
        """
        return self.size_repository.get_sizes_used_in_items()

    def search_sizes(self, query: str) -> QuerySet[Size]:
        """
        Search sizes by name or category.

        Args:
            query: Search query

        Returns:
            QuerySet of matching sizes
        """
        # Search by name
        name_results = self.size_repository.get_sizes_by_name(query)

        # Search by category
        category_results = self.size_repository.get_sizes_by_category(query)

        # Combine results and remove duplicates
        return (name_results | category_results).distinct()

    def get_size_by_name_and_category(self, name: str, category: str) -> Size | None:
        """
        Get a size by its name and category.

        Args:
            name: Size name
            category: Size category

        Returns:
            Size instance or None if not found
        """
        return self.size_repository.get_size_by_name_and_category(name, category)

    def get_sizes_by_category(self, category: str) -> QuerySet[Size]:
        """
        Get all sizes for a specific category.

        Args:
            category: Size category

        Returns:
            QuerySet of sizes in the category
        """
        return self.size_repository.get_sizes_by_category(category)

    def create_custom_size(self, name: str, category: str) -> Size:
        """
        Create a custom size.

        Args:
            name: Size name
            category: Size category

        Returns:
            Created size instance

        Raises:
            ValueError: If size data is invalid
        """
        # Validate category
        if not self._is_valid_category(category):
            error_msg = "Invalid category"
            raise ValueError(error_msg)

        # Check if size already exists
        existing_size = self.get_size_by_name_and_category(name, category)
        if existing_size:
            error_msg = "Size with this name and category already exists"
            raise ValueError(error_msg)

        return self.size_repository.create(name=name, category=category)

    def get_sizes_for_api(self) -> list[dict[str, str]]:
        """
        Get sizes formatted for API responses.

        Returns:
            List of size dictionaries
        """
        sizes = self.size_repository.get_all()
        return [
            {
                "id": size.id,
                "name": size.name,
                "category": size.category,
            }
            for size in sizes
        ]

    def get_size_usage_analytics(self) -> dict[str, any]:
        """
        Get detailed size usage analytics.

        Returns:
            Dictionary with detailed size analytics
        """
        stats = self.get_size_statistics()

        # Add additional analytics
        total_sizes = self.size_repository.count()
        used_sizes = self.get_sizes_used_in_collection().count()

        return {
            **stats,
            "total_sizes": total_sizes,
            "used_sizes": used_sizes,
            "unused_sizes": total_sizes - used_sizes,
            "usage_percentage": (used_sizes / total_sizes * 100) if total_sizes > 0 else 0,
        }

    def get_size_distribution_by_category(self) -> dict[str, int]:
        """
        Get size distribution by category.

        Returns:
            Dictionary with count of sizes per category
        """
        return self.size_repository.get_size_distribution_by_category()

    def get_most_used_sizes_by_category(self) -> dict[str, list[dict[str, any]]]:
        """
        Get most used sizes grouped by category.

        Returns:
            Dictionary with most used sizes per category
        """
        categories = ["tops", "bottoms", "accessories"]
        result = {}

        for category in categories:
            sizes = self.size_repository.get_most_used_sizes_by_category(category, limit=5)
            result[category] = [
                {
                    "name": size.name,
                    "usage_count": size.usage_count,
                    "category": size.category,
                }
                for size in sizes
            ]

        return result

    def _is_valid_category(self, category: str) -> bool:
        """
        Validate size category.

        Args:
            category: Size category

        Returns:
            True if valid, False otherwise
        """
        valid_categories = ["tops", "bottoms", "accessories"]
        return category.lower() in valid_categories
