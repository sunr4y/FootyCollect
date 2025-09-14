"""
Main service facade for the collection app.

This service acts as a facade for all collection-related services,
providing a unified interface for complex operations that involve
multiple services.
"""

from typing import Any

from django.contrib.auth.models import User

from footycollect.collection.models import Jersey
from footycollect.collection.services.color_service import ColorService
from footycollect.collection.services.item_service import ItemService
from footycollect.collection.services.photo_service import PhotoService
from footycollect.collection.services.size_service import SizeService


class CollectionService:
    """
    Main service facade for collection operations.

    This service orchestrates operations across multiple services
    and provides a unified interface for complex collection operations.
    """

    def __init__(self):
        self.item_service = ItemService()
        self.photo_service = PhotoService()
        self.color_service = ColorService()
        self.size_service = SizeService()

    def initialize_collection_data(self) -> dict[str, int]:
        """
        Initialize all default data for the collection.

        Returns:
            Dictionary with counts of initialized items
        """
        return {
            "colors": self.color_service.initialize_default_colors(),
            "sizes": self.size_service.initialize_default_sizes(),
        }

    def get_collection_dashboard_data(self, user: User) -> dict[str, Any]:
        """
        Get comprehensive dashboard data for a user's collection.

        Args:
            user: User instance

        Returns:
            Dictionary with dashboard data
        """
        return {
            "total_items": self.item_service.get_user_item_count(user),
            "public_items": self.item_service.get_public_items().count(),
            "recent_items": list(self.item_service.get_recent_items(limit=5).values()),
            "color_stats": self.color_service.get_color_statistics(),
            "size_stats": self.size_service.get_size_statistics(),
            "popular_colors": list(self.color_service.get_popular_colors(5).values()),
            "popular_sizes": list(self.size_service.get_popular_sizes(5).values()),
        }

    def get_collection_analytics(self, user: User) -> dict[str, Any]:
        """
        Get comprehensive analytics for a user's collection.

        Args:
            user: User instance

        Returns:
            Dictionary with collection analytics
        """
        return {
            "item_analytics": self.item_service.get_item_analytics(user),
            "color_analytics": self.color_service.get_color_usage_analytics(),
            "size_analytics": self.size_service.get_size_usage_analytics(),
            "photo_analytics": self.photo_service.get_photo_analytics(),
        }

    def search_collection(self, user: User, query: str, filters: dict | None = None) -> dict[str, Any]:
        """
        Search across the entire collection.

        Args:
            user: User instance
            query: Search query
            filters: Optional filters

        Returns:
            Dictionary with search results
        """
        results = {
            "items": list(self.item_service.search_items(user, query, filters).values()),
            "colors": list(self.color_service.search_colors(query).values()),
            "sizes": list(self.size_service.search_sizes(query).values()),
        }

        # Add result counts
        results["total_results"] = sum(len(v) for v in results.values())

        return results

    def get_collection_statistics(self) -> dict[str, Any]:
        """
        Get global collection statistics.

        Returns:
            Dictionary with global statistics
        """
        return {
            "total_colors": self.color_service.color_repository.count(),
            "total_sizes": self.size_service.size_repository.count(),
            "total_items": self.item_service.item_repository.count(),
            "total_photos": self.photo_service.photo_repository.count(),
            "color_distribution": self.color_service.get_color_usage_analytics(),
            "size_distribution": self.size_service.get_size_distribution_by_category(),
        }

    def get_form_data(self) -> dict[str, Any]:
        """
        Get all data needed for item forms.

        Returns:
            Dictionary with form data
        """
        return {
            "colors": self.color_service.get_colors_for_item_form(),
            "sizes": self.size_service.get_sizes_for_item_form(),
        }

    def get_api_data(self) -> dict[str, list[dict[str, str]]]:
        """
        Get all data formatted for API responses.

        Returns:
            Dictionary with API-formatted data
        """
        return {
            "colors": self.color_service.get_colors_for_api(),
            "sizes": self.size_service.get_sizes_for_api(),
        }

    def create_item_with_photos(
        self,
        user: User,
        item_data: dict[str, Any],
        photo_files: list | None = None,
    ) -> Jersey:
        """
        Create an item with associated photos.

        Args:
            user: User instance
            item_data: Item data dictionary
            photo_files: Optional list of photo files

        Returns:
            Created item instance
        """
        # Create the item
        item = self.item_service.create_item(user, item_data)

        # Add photos if provided
        if photo_files:
            for photo_file in photo_files:
                self.photo_service.create_photo(item, photo_file)

        return item

    def update_item_with_photos(
        self,
        item: Jersey,
        item_data: dict[str, Any],
        photo_files: list | None = None,
        remove_photo_ids: list[int] | None = None,
    ) -> Jersey:
        """
        Update an item and manage its photos.

        Args:
            item: Item instance to update
            item_data: Updated item data
            photo_files: Optional new photo files
            remove_photo_ids: Optional list of photo IDs to remove

        Returns:
            Updated item instance
        """
        # Update the item
        updated_item = self.item_service.update_item(item, item_data)

        # Remove photos if specified
        if remove_photo_ids:
            for photo_id in remove_photo_ids:
                self.photo_service.delete_photo(photo_id)

        # Add new photos if provided
        if photo_files:
            for photo_file in photo_files:
                self.photo_service.create_photo(updated_item, photo_file)

        return updated_item

    def get_user_collection_summary(self, user: User) -> dict[str, Any]:
        """
        Get a summary of a user's collection.

        Args:
            user: User instance

        Returns:
            Dictionary with collection summary
        """
        items = self.item_service.get_user_items(user)

        return {
            "total_items": items.count(),
            "by_type": self.item_service.get_user_item_count_by_type(user),
            "by_club": self.item_service.get_items_by_club(user).count(),
            "by_season": self.item_service.get_items_by_season(user).count(),
            "recent_additions": list(self.item_service.get_recent_items(limit=10).values()),
        }

    def cleanup_unused_data(self) -> dict[str, int]:
        """
        Clean up unused colors, sizes, and orphaned photos.

        Returns:
            Dictionary with cleanup results
        """
        # This would implement cleanup logic for unused data
        # For now, return empty results
        return {
            "unused_colors_removed": 0,
            "unused_sizes_removed": 0,
            "orphaned_photos_removed": 0,
        }
