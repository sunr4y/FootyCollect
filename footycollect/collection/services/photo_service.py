"""
Service for photo-related business logic.

This service handles complex business operations related to photos,
including upload, processing, and management.
"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import QuerySet

from footycollect.collection.models import Photo
from footycollect.collection.repositories import PhotoRepository

User = get_user_model()


class PhotoService:
    """
    Service for photo-related business logic.

    This service handles complex operations related to photo management,
    including upload, processing, and validation.
    """

    def __init__(self):
        self.photo_repository = PhotoRepository()

    def upload_photos_for_item(
        self,
        item,
        photo_files: list[UploadedFile],
        user: User,
    ) -> list[Photo]:
        """
        Upload multiple photos for an item.

        Args:
            item: Item instance
            photo_files: List of uploaded photo files
            user: User uploading the photos

        Returns:
            List of created Photo instances

        Raises:
            ValueError: If photos are invalid
        """
        if not photo_files:
            return []

        # Validate photos
        self._validate_photos(photo_files)

        with transaction.atomic():
            photos = []
            current_max_order = self.photo_repository.get_photos_by_item(item).count()

            for index, photo_file in enumerate(photo_files):
                photo = self.photo_repository.create(
                    image=photo_file,
                    content_object=item,
                    order=current_max_order + index,
                    uploaded_by=user,
                )
                photos.append(photo)

            return photos

    def reorder_photos(self, item, photo_orders: list[tuple[int, int]]) -> bool:
        """
        Reorder photos for an item.

        Args:
            item: Item instance
            photo_orders: List of (photo_id, new_order) tuples

        Returns:
            True if successful, False otherwise
        """
        return self.photo_repository.reorder_photos(item, photo_orders)

    def delete_photo(self, photo_id: int, user: User) -> bool:
        """
        Delete a specific photo.

        Args:
            photo_id: ID of the photo to delete
            user: User requesting the deletion

        Returns:
            True if deleted successfully, False otherwise
        """
        photo = self.photo_repository.get_by_id(photo_id)
        if not photo or photo.uploaded_by != user:
            return False

        return self.photo_repository.delete(photo_id)

    def delete_all_photos_for_item(self, item) -> int:
        """
        Delete all photos for an item.

        Args:
            item: Item instance

        Returns:
            Number of photos deleted
        """
        return self.photo_repository.delete_photos_by_item(item)

    def get_item_photos(self, item) -> QuerySet[Photo]:
        """
        Get all photos for an item.

        Args:
            item: Item instance

        Returns:
            QuerySet of photos for the item
        """
        return self.photo_repository.get_photos_by_item(item)

    def get_main_photo(self, item) -> Photo | None:
        """
        Get the main photo for an item.

        Args:
            item: Item instance

        Returns:
            Main photo or None if no photos exist
        """
        return self.photo_repository.get_main_photo(item)

    def get_user_photos(self, user: User, limit: int = 20) -> QuerySet[Photo]:
        """
        Get photos uploaded by a user.

        Args:
            user: User instance
            limit: Maximum number of photos to return

        Returns:
            QuerySet of user's photos
        """
        return self.photo_repository.get_photos_by_user(user)[:limit]

    def get_recent_photos(self, limit: int = 20) -> QuerySet[Photo]:
        """
        Get recent photos from all users.

        Args:
            limit: Maximum number of photos to return

        Returns:
            QuerySet of recent photos
        """
        return self.photo_repository.get_recent_photos(limit)

    def get_photo_statistics(self, user: User = None) -> dict:
        """
        Get photo statistics.

        Args:
            user: Optional user to get statistics for

        Returns:
            Dictionary with photo statistics
        """
        if user:
            total_photos = self.photo_repository.get_photos_count_by_user(user)
            recent_photos = self.get_user_photos(user, limit=10)
        else:
            total_photos = self.photo_repository.count()
            recent_photos = self.get_recent_photos(limit=10)

        return {
            "total_photos": total_photos,
            "recent_photos": recent_photos,
            "photos_by_month": self._get_photos_by_month(user),
        }

    def _validate_photos(self, photo_files: list[UploadedFile]) -> None:
        """
        Validate uploaded photo files.

        Args:
            photo_files: List of uploaded photo files

        Raises:
            ValueError: If photos are invalid
        """
        if not photo_files:
            error_msg = "No photos provided"
            raise ValueError(error_msg)

        # Check file count limit
        max_photos_per_item = 10
        if len(photo_files) > max_photos_per_item:
            error_msg = "Too many photos. Maximum 10 photos allowed per item."
            raise ValueError(error_msg)

        for photo_file in photo_files:
            # Check file size (max 15MB)
            if photo_file.size > 15 * 1024 * 1024:
                error_msg = f"Photo {photo_file.name} is too large. Maximum size is 15MB."
                raise ValueError(error_msg)

            # Check file type
            allowed_content_types = ["image/jpeg", "image/png", "image/webp"]
            if photo_file.content_type not in allowed_content_types:
                error_msg = (
                    f"Photo {photo_file.name} has an invalid format. "
                    f"Allowed formats: {', '.join(allowed_content_types)}"
                )
                raise ValueError(error_msg)

    def _get_photos_by_month(self, user: User = None) -> dict:
        """
        Get photo count by month.

        Args:
            user: Optional user to filter by

        Returns:
            Dictionary with photo counts by month
        """
        from django.db.models import Count
        from django.db.models.functions import TruncMonth

        queryset = self.photo_repository.get_all()
        if user:
            queryset = queryset.filter(uploaded_by=user)

        return dict(
            queryset.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .values_list("month", "count"),
        )

    def create_photo_with_validation(
        self,
        file: UploadedFile,
        user: User,
        order: int = 0,
    ) -> Photo:
        """
        Create a single photo with validation (for individual uploads).

        Args:
            file: Uploaded file
            user: User uploading the photo
            order: Order of the photo

        Returns:
            Created Photo instance

        Raises:
            ValueError: If photo is invalid
        """
        # Validate single photo
        self._validate_photos([file])

        # Create photo without associating it with any item yet
        return self.photo_repository.create(
            image=file,
            order=order,
            user=user,
        )
