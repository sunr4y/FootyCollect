"""
Repository for photo-related database operations.

This repository handles all database operations related to photos,
including upload, ordering, and management of item photos.
"""

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from footycollect.collection.models import Photo

from .base_repository import BaseRepository

User = get_user_model()


class PhotoRepository(BaseRepository):
    """
    Repository for photo-related database operations.

    This repository provides specialized methods for working with photos
    and their related data.
    """

    def __init__(self):
        super().__init__(Photo)

    def get_photos_by_item(self, item) -> QuerySet[Photo]:
        """
        Get all photos for a specific item.

        Args:
            item: Item instance (Jersey, Shorts, BaseItem, etc.)

        Returns:
            QuerySet of photos for the item
        """
        from django.contrib.contenttypes.models import ContentType

        # For MTI models like Jersey, we need to get the BaseItem
        # because GenericRelation is on BaseItem, not on Jersey
        from footycollect.collection.models import BaseItem

        # If item is a Jersey (or other MTI model), get its base_item
        if hasattr(item, "base_item"):
            base_item = item.base_item
        elif isinstance(item, BaseItem):
            base_item = item
        else:
            # Fallback: assume it's already a BaseItem or try to get it
            base_item = item

        # Get ContentType for BaseItem model class (not instance)
        content_type = ContentType.objects.get_for_model(BaseItem)
        return self.model.objects.filter(
            content_type=content_type,
            object_id=base_item.pk,
        ).order_by("order")

    def get_main_photo(self, item) -> Photo | None:
        """
        Get the main photo for an item (first in order).

        Args:
            item: Item instance

        Returns:
            Main photo or None if no photos exist
        """
        return self.get_photos_by_item(item).first()

    def reorder_photos(self, item, photo_orders: list[tuple[int, int]]) -> bool:
        """
        Reorder photos for an item.

        Args:
            item: Item instance
            photo_orders: List of (photo_id, new_order) tuples

        Returns:
            True if successful, False otherwise
        """
        from django.contrib.contenttypes.models import ContentType

        # For MTI models like Jersey, we need to get the BaseItem
        # because GenericRelation is on BaseItem, not on Jersey
        from footycollect.collection.models import BaseItem

        # If item is a Jersey (or other MTI model), get its base_item
        if hasattr(item, "base_item"):
            base_item = item.base_item
        elif isinstance(item, BaseItem):
            base_item = item
        else:
            # Fallback: assume it's already a BaseItem or try to get it
            base_item = item

        # Get ContentType for BaseItem model class (not instance)
        content_type = ContentType.objects.get_for_model(BaseItem)
        try:
            for photo_id, new_order in photo_orders:
                photo = self.model.objects.get(
                    id=photo_id,
                    content_type=content_type,
                    object_id=base_item.pk,
                )
                photo.order = new_order
                photo.save(update_fields=["order"])
        except self.model.DoesNotExist:
            return False
        else:
            return True

    def delete_photos_by_item(self, item) -> int:
        """
        Delete all photos for a specific item.

        Args:
            item: Item instance

        Returns:
            Number of photos deleted
        """
        photos = self.get_photos_by_item(item)
        count = photos.count()
        photos.delete()
        return count

    def get_photos_by_user(self, user: User) -> QuerySet[Photo]:
        """
        Get all photos uploaded by a specific user.

        Args:
            user: User instance

        Returns:
            QuerySet of photos uploaded by the user
        """
        return self.model.objects.filter(user=user).order_by("-uploaded_at")

    def get_photos_by_type(self, content_type: str) -> QuerySet[Photo]:
        """
        Get all photos for a specific content type.

        Args:
            content_type: Content type model name (e.g., 'jersey', 'shorts')

        Returns:
            QuerySet of photos for the content type
        """
        return self.model.objects.filter(
            content_type__model=content_type,
        ).order_by("-uploaded_at")

    def get_recent_photos(self, limit: int = 10) -> QuerySet[Photo]:
        """
        Get the most recently uploaded photos.

        Args:
            limit: Maximum number of photos to return

        Returns:
            QuerySet of recent photos
        """
        return self.model.objects.all().order_by("-uploaded_at")[:limit]

    def get_photos_count_by_item(self, item) -> int:
        """
        Get the count of photos for a specific item.

        Args:
            item: Item instance

        Returns:
            Number of photos for the item
        """
        return self.get_photos_by_item(item).count()

    def get_photos_count_by_user(self, user: User) -> int:
        """
        Get the count of photos uploaded by a specific user.

        Args:
            user: User instance

        Returns:
            Number of photos uploaded by the user
        """
        return self.get_photos_by_user(user).count()
