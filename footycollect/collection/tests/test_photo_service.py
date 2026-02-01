"""
Tests for PhotoService.
"""

from unittest.mock import Mock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from footycollect.collection.services.photo_service import PhotoService
from footycollect.users.models import User

# Constants for test values
TEST_PASSWORD = "testpass123"
EXPECTED_PHOTOS_COUNT_2 = 2
EXPECTED_PHOTOS_COUNT_3 = 3
EXPECTED_PHOTOS_COUNT_5 = 5
EXPECTED_PHOTOS_COUNT_20 = 20


class TestPhotoService(TestCase):
    """Test cases for PhotoService."""

    def setUp(self):
        """Set up test data."""
        self.service = PhotoService()

        # Create test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )

        # Use mocks to avoid database constraints
        self.jersey = Mock()
        self.jersey.pk = 1
        self.jersey._meta = Mock()
        self.jersey._meta.app_label = "collection"
        self.jersey._meta.model_name = "jersey"
        self.jersey.base_item = Mock()
        self.jersey.base_item.user = self.user

    def test_service_integration_with_repository(self):
        """Test service integration with photo repository."""
        # Test photo upload through service with mocked repository
        with (
            patch.object(self.service.photo_repository, "create") as mock_create,
            patch.object(self.service.photo_repository, "get_photos_by_item") as mock_get_photos,
        ):
            # Mock the get_photos_by_item to return a mock queryset with count
            mock_queryset = Mock()
            mock_queryset.count.return_value = 0
            mock_get_photos.return_value = mock_queryset

            # Mock the create method to return mock photos
            mock_photo1 = Mock()
            mock_photo1.id = 1
            mock_photo1.order = 0
            mock_photo2 = Mock()
            mock_photo2.id = 2
            mock_photo2.order = 1
            mock_create.side_effect = [mock_photo1, mock_photo2]

            # Create test images
            test_image1 = SimpleUploadedFile(
                "test1.jpg",
                b"fake content",
                content_type="image/jpeg",
            )
            test_image2 = SimpleUploadedFile(
                "test2.jpg",
                b"fake content",
                content_type="image/jpeg",
            )

            files = [test_image1, test_image2]
            photos = self.service.upload_photos_for_item(self.jersey, files, self.user)

            # Verify service used repository correctly
            assert len(photos) == 2  # noqa: PLR2004
            assert mock_create.call_count == 2  # noqa: PLR2004
            mock_get_photos.assert_called_once_with(self.jersey)

    def test_upload_photos_for_item_success(self):
        """Test successful photo upload for item."""
        # Create test image files
        test_image1 = SimpleUploadedFile(
            "test1.jpg",
            b"fake image content",
            content_type="image/jpeg",
        )
        test_image2 = SimpleUploadedFile(
            "test2.jpg",
            b"fake image content",
            content_type="image/jpeg",
        )

        with (
            patch("django.core.files.storage.default_storage") as mock_storage,
            patch("footycollect.core.utils.images.optimize_image") as mock_optimize,
            patch.object(self.service.photo_repository, "get_photos_by_item") as mock_get_photos,
            patch.object(self.service.photo_repository, "create") as mock_create,
        ):
            mock_storage.size.return_value = 1000  # Mock file size
            mock_optimize.return_value = None  # Mock optimization
            mock_get_photos.return_value.count.return_value = 0  # No existing photos

            # Mock photo objects
            mock_photo1 = Mock()
            mock_photo1.id = 1
            mock_photo2 = Mock()
            mock_photo2.id = 2
            mock_create.side_effect = [mock_photo1, mock_photo2]

            photos = self.service.upload_photos_for_item(
                self.jersey,
                [test_image1, test_image2],
                self.user,
            )

            assert len(photos) == EXPECTED_PHOTOS_COUNT_2
            assert photos[0] == mock_photo1
            assert photos[1] == mock_photo2

    def test_upload_photos_for_item_empty_list(self):
        """Test upload with empty photo list."""
        photos = self.service.upload_photos_for_item(
            self.jersey,
            [],
            self.user,
        )

        assert photos == []

    def test_upload_photos_for_item_too_many_photos(self):
        """Test upload with too many photos."""
        # Create 11 photos (limit is 10)
        photo_files = [
            SimpleUploadedFile(
                f"test{i}.jpg",
                b"fake image content",
                content_type="image/jpeg",
            )
            for i in range(11)
        ]

        with pytest.raises(ValueError, match="Too many photos"):
            self.service.upload_photos_for_item(
                self.jersey,
                photo_files,
                self.user,
            )

    def test_upload_photos_for_item_file_too_large(self):
        """Test upload with file too large."""
        # Create a large file (16MB)
        large_file = SimpleUploadedFile(
            "large.jpg",
            b"x" * (16 * 1024 * 1024),  # 16MB
            content_type="image/jpeg",
        )

        with pytest.raises(ValueError, match="is too large"):
            self.service.upload_photos_for_item(
                self.jersey,
                [large_file],
                self.user,
            )

    def test_upload_photos_for_item_invalid_content_type(self):
        """Test upload with invalid content type."""
        invalid_file = SimpleUploadedFile(
            "test.txt",
            b"not an image",
            content_type="text/plain",
        )

        with pytest.raises(ValueError, match="invalid format"):
            self.service.upload_photos_for_item(
                self.jersey,
                [invalid_file],
                self.user,
            )

    def test_reorder_photos_success(self):
        """Test successful photo reordering."""
        with patch.object(self.service.photo_repository, "reorder_photos") as mock_reorder:
            mock_reorder.return_value = True

            result = self.service.reorder_photos(self.jersey, [(1, 0), (2, 1)])

            assert result is True
            mock_reorder.assert_called_once_with(self.jersey, [(1, 0), (2, 1)])

    def test_delete_photo_success(self):
        """Test successful photo deletion."""
        with (
            patch.object(self.service.photo_repository, "get_by_id") as mock_get,
            patch.object(self.service.photo_repository, "delete") as mock_delete,
        ):
            mock_photo = Mock()
            mock_photo.uploaded_by = self.user
            mock_get.return_value = mock_photo
            mock_delete.return_value = True

            result = self.service.delete_photo(1, self.user)

            assert result is True
            mock_get.assert_called_once_with(1)
            mock_delete.assert_called_once_with(1)

    def test_delete_photo_wrong_user(self):
        """Test photo deletion by wrong user."""
        # Create another user
        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password=TEST_PASSWORD,
        )

        with patch.object(self.service.photo_repository, "get_by_id") as mock_get:
            mock_photo = Mock()
            mock_photo.uploaded_by = self.user  # Different from other_user
            mock_get.return_value = mock_photo

            result = self.service.delete_photo(1, other_user)

            assert result is False
            mock_get.assert_called_once_with(1)

    def test_delete_photo_nonexistent(self):
        """Test deletion of non-existent photo."""
        result = self.service.delete_photo(999, self.user)
        assert result is False

    def test_delete_all_photos_for_item(self):
        """Test deletion of all photos for item."""
        with patch.object(self.service.photo_repository, "delete_photos_by_item") as mock_delete:
            mock_delete.return_value = 3

            result = self.service.delete_all_photos_for_item(self.jersey)

            assert result == EXPECTED_PHOTOS_COUNT_3
            mock_delete.assert_called_once_with(self.jersey)

    def test_get_item_photos(self):
        """Test getting photos for item."""
        with patch.object(self.service.photo_repository, "get_photos_by_item") as mock_get:
            mock_queryset = Mock()
            mock_get.return_value = mock_queryset

            result = self.service.get_item_photos(self.jersey)

            assert result == mock_queryset
            mock_get.assert_called_once_with(self.jersey)

    def test_get_main_photo(self):
        """Test getting main photo for item."""
        with patch.object(self.service.photo_repository, "get_main_photo") as mock_get:
            mock_photo = Mock()
            mock_get.return_value = mock_photo

            result = self.service.get_main_photo(self.jersey)

            assert result == mock_photo
            mock_get.assert_called_once_with(self.jersey)

    def test_get_user_photos(self):
        """Test getting photos by user."""
        with patch.object(self.service.photo_repository, "get_photos_by_user") as mock_get:
            mock_queryset = Mock()
            mock_queryset.__getitem__ = Mock(return_value=[])  # Mock slicing
            mock_get.return_value = mock_queryset

            result = self.service.get_user_photos(self.user, limit=10)

            assert result == []
            mock_get.assert_called_once_with(self.user)

    def test_get_recent_photos(self):
        """Test getting recent photos."""
        with patch.object(self.service.photo_repository, "get_recent_photos") as mock_get:
            mock_queryset = Mock()
            mock_get.return_value = mock_queryset

            result = self.service.get_recent_photos(limit=15)

            assert result == mock_queryset
            mock_get.assert_called_once_with(15)

    def test_get_photo_statistics_with_user(self):
        """Test getting photo statistics for specific user."""
        with (
            patch.object(self.service.photo_repository, "get_photos_count_by_user") as mock_count,
            patch.object(self.service, "get_user_photos") as mock_user_photos,
            patch.object(self.service, "_get_photos_by_month") as mock_monthly,
        ):
            mock_count.return_value = 5
            mock_user_photos.return_value = Mock()
            mock_monthly.return_value = {"2024-01": 3, "2024-02": 2}

            result = self.service.get_photo_statistics(self.user)

            assert result["total_photos"] == EXPECTED_PHOTOS_COUNT_5
            assert "recent_photos" in result
            assert "photos_by_month" in result
            mock_count.assert_called_once_with(self.user)
            mock_user_photos.assert_called_once_with(self.user, limit=10)
            mock_monthly.assert_called_once_with(self.user)

    def test_get_photo_statistics_without_user(self):
        """Test getting photo statistics for all users."""
        with (
            patch.object(self.service.photo_repository, "count") as mock_count,
            patch.object(self.service, "get_recent_photos") as mock_recent,
            patch.object(self.service, "_get_photos_by_month") as mock_monthly,
        ):
            mock_count.return_value = 20
            mock_recent.return_value = Mock()
            mock_monthly.return_value = {"2024-01": 10, "2024-02": 10}

            result = self.service.get_photo_statistics()

            assert result["total_photos"] == EXPECTED_PHOTOS_COUNT_20
            assert "recent_photos" in result
            assert "photos_by_month" in result
            mock_count.assert_called_once()
            mock_recent.assert_called_once_with(limit=10)
            mock_monthly.assert_called_once_with(None)

    def test_create_photo_with_validation_success(self):
        """Test successful photo creation with validation."""
        test_image = SimpleUploadedFile(
            "test.jpg",
            b"fake image content",
            content_type="image/jpeg",
        )

        with (
            patch("django.core.files.storage.default_storage") as mock_storage,
            patch("footycollect.core.utils.images.optimize_image") as mock_optimize,
            patch.object(self.service.photo_repository, "create") as mock_create,
        ):
            mock_storage.size.return_value = 1000
            mock_optimize.return_value = None
            mock_photo = Mock()
            mock_create.return_value = mock_photo

            result = self.service.create_photo_with_validation(test_image, self.user, order=1)

            assert result == mock_photo
            mock_create.assert_called_once_with(
                image=test_image,
                order=1,
                user=self.user,
            )

    def test_create_photo_with_validation_invalid(self):
        """Test photo creation with invalid file."""
        invalid_file = SimpleUploadedFile(
            "test.txt",
            b"not an image",
            content_type="text/plain",
        )

        with pytest.raises(ValueError, match="invalid format"):
            self.service.create_photo_with_validation(invalid_file, self.user)

    def test_validate_photos_empty_list(self):
        """Test validation with empty photo list."""
        with pytest.raises(ValueError, match="No photos provided"):
            self.service._validate_photos([])

    def test_validate_photos_valid_files(self):
        """Test validation with valid files."""
        test_image = SimpleUploadedFile(
            "test.jpg",
            b"fake image content",
            content_type="image/jpeg",
        )

        # Should not raise exception
        self.service._validate_photos([test_image])

    def test_get_photos_by_month(self):
        """Test getting photos by month."""
        with patch.object(self.service.photo_repository, "get_all") as mock_get_all:
            mock_queryset = Mock()
            mock_get_all.return_value = mock_queryset
            mock_queryset.filter.return_value = mock_queryset
            mock_queryset.annotate.return_value = mock_queryset
            mock_queryset.values.return_value = mock_queryset
            mock_queryset.values_list.return_value = [("2024-01", 3), ("2024-02", 2)]

            result = self.service._get_photos_by_month(self.user)

            assert result == {"2024-01": 3, "2024-02": 2}
            mock_get_all.assert_called_once()
            mock_queryset.filter.assert_called_once_with(uploaded_by=self.user)
