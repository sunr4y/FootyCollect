"""
Tests for collection tasks.
"""

from unittest.mock import patch

import pytest
from django.core.management.base import CommandError
from django.test import TestCase

from footycollect.collection.models import Photo
from footycollect.collection.tasks import (
    cleanup_all_orphaned_photos,
    cleanup_old_incomplete_photos,
    cleanup_orphaned_photos,
    process_photo_to_avif,
)
from footycollect.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_process_photo_to_avif(settings, tmp_path):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.CELERY_BROKER_URL = "memory://"
    settings.CELERY_RESULT_BACKEND = "cache+memory://"

    from io import BytesIO

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image as PILImage

    user = UserFactory()
    img = PILImage.new("RGB", (100, 100), color="red")
    img_buffer = BytesIO()
    img.save(img_buffer, format="JPEG")
    img_buffer.seek(0)

    image_file = SimpleUploadedFile("test.jpg", img_buffer.read(), content_type="image/jpeg")
    photo = Photo.objects.create(user=user, image=image_file)

    result = process_photo_to_avif.delay(photo.pk)
    result.get(timeout=10)

    photo.refresh_from_db()
    assert photo.image_avif


class TestCleanupOrphanedPhotos(TestCase):
    """Test cases for cleanup_orphaned_photos task."""

    @patch("footycollect.collection.tasks.call_command")
    @patch("footycollect.collection.tasks.logger")
    def test_cleanup_orphaned_photos_success(self, mock_logger, mock_call_command):
        """Test successful orphaned photos cleanup."""
        mock_call_command.return_value = None

        result = cleanup_orphaned_photos()

        mock_logger.info.assert_any_call("Starting orphaned photos cleanup task")
        mock_logger.info.assert_any_call("Orphaned photos cleanup task completed successfully")
        mock_call_command.assert_called_once_with(
            "cleanup_orphaned_photos",
            "--incomplete-only",
            "--older-than-hours=24",
            verbosity=1,
        )
        assert result == "Orphaned photos cleanup completed"

    @patch("footycollect.collection.tasks.call_command")
    @patch("footycollect.collection.tasks.logger")
    def test_cleanup_orphaned_photos_exception(self, mock_logger, mock_call_command):
        """Test orphaned photos cleanup with exception."""
        mock_call_command.side_effect = CommandError("Test error")

        with pytest.raises(CommandError, match="Test error"):
            cleanup_orphaned_photos()

        mock_logger.info.assert_called_once_with("Starting orphaned photos cleanup task")
        mock_logger.exception.assert_called_once()
        assert "Error in orphaned photos cleanup task" in mock_logger.exception.call_args[0][0]


class TestCleanupAllOrphanedPhotos(TestCase):
    """Test cases for cleanup_all_orphaned_photos task."""

    @patch("footycollect.collection.tasks.call_command")
    @patch("footycollect.collection.tasks.logger")
    def test_cleanup_all_orphaned_photos_success(self, mock_logger, mock_call_command):
        """Test successful comprehensive orphaned photos cleanup."""
        mock_call_command.return_value = None

        result = cleanup_all_orphaned_photos()

        mock_logger.info.assert_any_call("Starting comprehensive orphaned photos cleanup task")
        mock_logger.info.assert_any_call("Comprehensive orphaned photos cleanup task completed successfully")
        mock_call_command.assert_called_once_with(
            "cleanup_orphaned_photos",
            verbosity=1,
        )
        assert result == "Comprehensive orphaned photos cleanup completed"

    @patch("footycollect.collection.tasks.call_command")
    @patch("footycollect.collection.tasks.logger")
    def test_cleanup_all_orphaned_photos_exception(self, mock_logger, mock_call_command):
        """Test comprehensive orphaned photos cleanup with exception."""
        mock_call_command.side_effect = CommandError("Test error")

        with pytest.raises(CommandError, match="Test error"):
            cleanup_all_orphaned_photos()

        mock_logger.info.assert_called_once_with("Starting comprehensive orphaned photos cleanup task")
        mock_logger.exception.assert_called_once()
        assert "comprehensive orphaned photos cleanup" in mock_logger.exception.call_args[0][0]


class TestCleanupOldIncompletePhotos(TestCase):
    """Test cases for cleanup_old_incomplete_photos task."""

    @patch("footycollect.collection.tasks.call_command")
    @patch("footycollect.collection.tasks.logger")
    def test_cleanup_old_incomplete_photos_success(self, mock_logger, mock_call_command):
        """Test successful old incomplete photos cleanup."""
        mock_call_command.return_value = None

        result = cleanup_old_incomplete_photos()

        mock_logger.info.assert_any_call("Starting old incomplete photos cleanup task")
        mock_logger.info.assert_any_call("Old incomplete photos cleanup task completed successfully")
        mock_call_command.assert_called_once_with(
            "cleanup_orphaned_photos",
            "--incomplete-only",
            "--older-than-hours=168",
            verbosity=1,
        )
        assert result == "Old incomplete photos cleanup completed"

    @patch("footycollect.collection.tasks.call_command")
    @patch("footycollect.collection.tasks.logger")
    def test_cleanup_old_incomplete_photos_exception(self, mock_logger, mock_call_command):
        """Test old incomplete photos cleanup with exception."""
        mock_call_command.side_effect = CommandError("Test error")

        with pytest.raises(CommandError, match="Test error"):
            cleanup_old_incomplete_photos()

        mock_logger.info.assert_called_once_with("Starting old incomplete photos cleanup task")
        mock_logger.exception.assert_called_once()
        assert "old incomplete photos cleanup" in mock_logger.exception.call_args[0][0]
