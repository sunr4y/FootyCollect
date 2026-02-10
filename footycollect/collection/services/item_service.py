"""
Service for item-related business logic.

This service handles complex business operations related to items,
orchestrating between repositories and implementing business rules.
"""

from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet

from footycollect.collection.models import BaseItem, Jersey
from footycollect.collection.repositories import ColorRepository, ItemRepository, PhotoRepository

User = get_user_model()


class ItemService:
    """
    Service for item-related business logic.

    This service handles complex operations that involve multiple repositories
    and implements business rules for item management.
    """

    def __init__(self):
        self.item_repository = ItemRepository()
        self.photo_repository = PhotoRepository()
        self.color_repository = ColorRepository()

    def create_item_with_photos(
        self,
        _user: User,
        item_data: dict[str, Any],
        photos: list[Any] | None = None,
    ) -> Jersey:
        """
        Create an item with associated photos.

        Args:
            _user: User creating the item (kept for API consistency; item user comes from item_data).
            item_data: Dictionary containing item data
            photos: List of photo files

        Returns:
            Created item instance

        Raises:
            ValueError: If item data is invalid
        """
        with transaction.atomic():
            # Create the item
            item = self.item_repository.create(**item_data)

            # Handle photos if provided
            if photos:
                self._process_item_photos(item, photos)

            return item

    def create_item(
        self,
        _user: User,
        item_data: dict[str, Any],
    ) -> Jersey:
        """
        Backwards-compatible wrapper for creating an item.

        The _user parameter is accepted for future use but item creation
        is currently delegated directly to the repository.
        """
        return self.item_repository.create(**item_data)

    def update_item_with_photos(
        self,
        item_id: int,
        item_data: dict[str, Any],
        photos: list[Any] | None = None,
    ) -> Jersey | None:
        """
        Update an item with new photos.

        Args:
            item_id: ID of the item to update
            item_data: Dictionary containing updated item data
            photos: List of new photo files

        Returns:
            Updated item instance or None if not found
        """
        with transaction.atomic():
            # Update the item
            item = self.item_repository.update(item_id, **item_data)
            if not item:
                return None

            # Handle photos if provided
            if photos:
                self._process_item_photos(item, photos)

            return item

    def update_item(
        self,
        item: Jersey,
        item_data: dict[str, Any],
    ) -> Jersey | None:
        """
        Backwards-compatible wrapper for updating an item instance.
        """
        return self.item_repository.update(item.pk, **item_data)

    def delete_item_with_photos(self, item_id: int) -> bool:
        """
        Delete an item and all its associated photos.

        Args:
            item_id: ID of the item to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        with transaction.atomic():
            item = self.item_repository.get_by_id(item_id)
            if not item:
                return False

            # Delete all photos first
            self.photo_repository.delete_photos_by_item(item)

            # Delete the item
            return self.item_repository.delete(item_id)

    def get_user_items(self, user: User) -> QuerySet[BaseItem]:
        """
        Get all items for a user.

        Args:
            user: User instance

        Returns:
            QuerySet of user's items
        """
        return self.item_repository.get_user_items(user)

    def _build_collection_summary(self, user: User) -> dict[str, Any]:
        """
        Build the core collection summary analytics for a user.
        """
        items = self.item_repository.get_user_items(user)

        return {
            "total_items": items.count(),
            "by_type": self.item_repository.get_user_item_count_by_type(user),
            "by_condition": self._get_items_by_condition(items),
            "by_brand": self._get_items_by_brand(items),
            "by_club": self._get_items_by_club(items),
        }

    def get_user_collection_summary(self, user: User) -> dict[str, Any]:
        """
        Get a summary of the user's collection.

        Args:
            user: User instance

        Returns:
            Dictionary with collection summary
        """
        return {
            **self._build_collection_summary(user),
            "recent_items": self.item_repository.get_recent_items(limit=5, user=user),
        }

    def get_user_item_count(self, user: User) -> int:
        """
        Get total item count for a user.
        """
        return self.item_repository.get_user_items(user).count()

    def get_public_items(self) -> QuerySet[BaseItem]:
        """
        Get all public items.
        """
        return self.item_repository.get_public_items()

    def get_recent_items(self, limit: int = 5, user: User | None = None) -> QuerySet[BaseItem]:
        """
        Get recent items, optionally filtered by user.
        """
        return self.item_repository.get_recent_items(limit=limit, user=user)

    def get_user_item_count_by_type(self, user: User) -> dict[str, int]:
        """
        Get item count by type for a user.
        """
        return self.item_repository.get_user_item_count_by_type(user)

    def get_items_by_club(self, user: User) -> QuerySet[BaseItem]:
        """
        Get all items for a user ordered by club.
        """
        return self.item_repository.get_user_items(user).order_by("club__name", "-created_at")

    def get_items_by_season(self, user: User) -> QuerySet[BaseItem]:
        """
        Get all items for a user ordered by season.
        """
        return self.item_repository.get_user_items(user).order_by("season__name", "-created_at")

    def get_item_analytics(self, user: User) -> dict[str, Any]:
        """
        Get analytics for items in a user's collection.
        """
        return self._build_collection_summary(user)

    def search_items_advanced(
        self,
        query: str,
        user: User = None,
        filters: dict[str, Any] | None = None,
    ) -> QuerySet[Jersey]:
        """
        Advanced search for items with multiple filters.

        Args:
            query: Search query string
            user: Optional user to limit search to their items
            filters: Dictionary of additional filters

        Returns:
            QuerySet of matching items
        """
        items = self.item_repository.get_user_items(user) if user else self.item_repository.get_public_items()

        # Apply text search
        if query:
            items = self.item_repository.search_items(query, user)

        # Apply additional filters
        if filters:
            items = self._apply_filters(items, filters)

        return items

    def search_items(
        self,
        user: User | None,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> QuerySet[Jersey]:
        """
        Backwards-compatible search wrapper used by CollectionService.
        """
        return self.search_items_advanced(query=query, user=user, filters=filters)

    def reorder_item_photos(self, item_id: int, photo_orders: list[tuple[int, int]]) -> bool:
        """
        Reorder photos for an item.

        Args:
            item_id: ID of the item
            photo_orders: List of (photo_id, new_order) tuples

        Returns:
            True if successful, False otherwise
        """
        item = self.item_repository.get_by_id(item_id)
        if not item:
            return False

        return self.photo_repository.reorder_photos(item, photo_orders)

    def get_item_with_photos(self, item_id: int) -> Jersey | None:
        """
        Get an item with its photos.

        Args:
            item_id: ID of the item

        Returns:
            Item instance with photos or None if not found
        """
        item = self.item_repository.get_by_id(item_id)
        if item:
            # Add photos to the item
            item.photos_list = self.photo_repository.get_photos_by_item(item)
        return item

    def _process_item_photos(self, item: Jersey, photos: list[Any]) -> None:
        """
        Process and save photos for an item.

        Args:
            item: Item instance
            photos: List of photo files
        """
        for index, photo_file in enumerate(photos):
            self.photo_repository.create(
                image=photo_file,
                content_object=item,
                order=index,
                uploaded_by=item.user,
            )

    def _get_items_by_condition(self, items: QuerySet[Jersey]) -> dict[str, int]:
        """Get count of items by condition."""
        from django.db.models import Count

        return dict(items.values("condition").annotate(count=Count("condition")).values_list("condition", "count"))

    def _get_items_by_brand(self, items: QuerySet[Jersey]) -> dict[str, int]:
        """Get count of items by brand."""
        from django.db.models import Count

        return dict(items.values("brand__name").annotate(count=Count("brand")).values_list("brand__name", "count"))

    def _get_items_by_club(self, items: QuerySet[Jersey]) -> dict[str, int]:
        """Get count of items by club."""
        from django.db.models import Count

        return dict(items.values("club__name").annotate(count=Count("club")).values_list("club__name", "count"))

    def _apply_filters(self, items: QuerySet[Jersey], filters: dict[str, Any]) -> QuerySet[Jersey]:
        """Apply additional filters to items queryset."""
        if "brand" in filters:
            items = items.filter(brand__name__icontains=filters["brand"])
        if "club" in filters:
            items = items.filter(club__name__icontains=filters["club"])
        if "condition" in filters:
            items = items.filter(condition=filters["condition"])
        if "is_draft" in filters:
            items = items.filter(is_draft=filters["is_draft"])
        if "is_private" in filters:
            items = items.filter(is_private=filters["is_private"])

        return items
