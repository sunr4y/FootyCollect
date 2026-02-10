"""
Tests for collection tasks.
"""

from pathlib import Path
from unittest.mock import ANY, Mock, patch

import pytest
from django.core.management.base import CommandError
from django.test import TestCase

from footycollect.collection.models import Photo
from footycollect.collection.tasks import (
    _download_image_to_temp,
    _get_rotating_proxy_config,
    _is_allowed_image_url,
    _validate_and_prepare_image_url,
    check_item_photo_processing,
    cleanup_all_orphaned_photos,
    cleanup_old_incomplete_photos,
    cleanup_orphaned_photos,
    download_external_image_and_attach,
    process_photo_to_avif,
)
from footycollect.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db
EXPECTED_PHOTO_ID = 123


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


def test_get_rotating_proxy_config_with_credentials(settings):
    """Test rotating proxy configuration with credentials."""
    settings.ROTATING_PROXY_URL = "https://proxy.example.com:8443"
    settings.ROTATING_PROXY_USERNAME = "user"
    settings.ROTATING_PROXY_PASSWORD = "pass"

    config = _get_rotating_proxy_config()

    assert config is not None
    proxy_url = config["http"]
    assert proxy_url.startswith("https://user:pass@")


def test_get_rotating_proxy_config_without_url(settings):
    """Test rotating proxy configuration when URL is not set."""
    settings.ROTATING_PROXY_URL = ""
    settings.ROTATING_PROXY_USERNAME = ""
    settings.ROTATING_PROXY_PASSWORD = ""

    assert _get_rotating_proxy_config() is None


def test_is_allowed_image_url_valid_host(settings):
    """Test allowed image URL with valid host."""
    settings.ALLOWED_EXTERNAL_IMAGE_HOSTS = ["cdn.footballkitarchive.com", "www.footballkitarchive.com"]

    assert _is_allowed_image_url("https://cdn.footballkitarchive.com/image.jpg") is True


def test_is_allowed_image_url_invalid_host(settings):
    """Test allowed image URL with invalid host."""
    settings.ALLOWED_EXTERNAL_IMAGE_HOSTS = ["cdn.footballkitarchive.com"]

    assert _is_allowed_image_url("https://example.com/image.jpg") is False


def test_validate_and_prepare_image_url_adds_scheme(settings):
    """Test URL validation adds scheme when missing."""
    settings.ALLOWED_EXTERNAL_IMAGE_HOSTS = ["example.com"]

    result = _validate_and_prepare_image_url("example.com/image.jpg", object_id=1)

    assert result.startswith("https://")
    assert "example.com/image.jpg" in result


def test_validate_and_prepare_image_url_rejects_untrusted_host(settings):
    """Test URL validation rejects untrusted host."""
    settings.ALLOWED_EXTERNAL_IMAGE_HOSTS = ["trusted.com"]

    with pytest.raises(ValueError, match="URL from untrusted source"):
        _validate_and_prepare_image_url("https://untrusted.com/image.jpg", object_id=1)


@patch("footycollect.collection.tasks.requests.get")
def test_download_image_to_temp_uses_proxy(mock_get, settings):
    """Test downloading image to temp file uses proxy when configured."""
    settings.ROTATING_PROXY_URL = "https://proxy.example.com:8443"
    settings.ROTATING_PROXY_USERNAME = "user"
    settings.ROTATING_PROXY_PASSWORD = "pass"

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_content.return_value = [b"data"]
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    img_temp = _download_image_to_temp("https://cdn.footballkitarchive.com/image.jpg", object_id=1)

    try:
        assert img_temp is not None
        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        assert "proxies" in kwargs
        assert "http" in kwargs["proxies"]
    finally:
        if img_temp is not None:
            img_temp.close()
            if getattr(img_temp, "name", None):
                Path(img_temp.name).unlink()


@patch("footycollect.collection.tasks._create_and_save_photo")
@patch("footycollect.collection.tasks.ContentType")
@patch("footycollect.collection.tasks._download_image_to_temp")
@patch("footycollect.collection.tasks._validate_and_prepare_image_url")
@patch("footycollect.collection.tasks.check_item_photo_processing")
def test_download_external_image_and_attach_success(
    mock_check_item_photo_processing,
    mock_validate_url,
    mock_download_temp,
    mock_content_type,
    mock_create_photo,
):
    """Test successful download and attach of external image."""
    mock_validate_url.return_value = "https://cdn.footballkitarchive.com/image.jpg"
    mock_download_temp.return_value = object()

    mock_model = Mock()
    mock_instance = Mock()
    mock_model.objects.get.return_value = mock_instance
    mock_ct = Mock()
    mock_ct.model_class.return_value = mock_model
    mock_content_type.objects.get_by_natural_key.return_value = mock_ct

    mock_photo = Mock()
    mock_photo.id = 123
    mock_create_photo.return_value = mock_photo

    result = download_external_image_and_attach(
        "collection",
        "jersey",
        1,
        "https://cdn.footballkitarchive.com/image.jpg",
        order=0,
    )

    assert result == EXPECTED_PHOTO_ID
    mock_validate_url.assert_called_once()
    mock_download_temp.assert_called_once()
    mock_create_photo.assert_called_once_with(mock_instance, ANY, mock_download_temp.return_value, 0)
    mock_check_item_photo_processing.apply_async.assert_called_once()


@patch("footycollect.collection.tasks.check_item_photo_processing")
def test_download_external_image_and_attach_handles_error(mock_check_item_photo_processing, settings):
    """Test download task handles validation errors and still schedules check."""
    settings.ALLOWED_EXTERNAL_IMAGE_HOSTS = ["trusted.com"]

    with pytest.raises(ValueError, match="URL from untrusted source"):
        download_external_image_and_attach(
            "collection",
            "jersey",
            1,
            "https://untrusted.com/image.jpg",
            order=0,
        )

    mock_check_item_photo_processing.delay.assert_called_once_with(1)


def test_check_item_photo_processing_no_photos(db):
    """Test item photo processing when item has no photos."""
    from footycollect.collection.factories import BaseItemFactory

    base_item = BaseItemFactory()
    base_item.is_processing_photos = True
    base_item.save(update_fields=["is_processing_photos"])

    check_item_photo_processing(base_item.pk)

    base_item.refresh_from_db()
    assert base_item.is_processing_photos is False


def test_check_item_photo_processing_all_processed(db):
    """Test item photo processing when all photos are processed."""
    from io import BytesIO

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image as PILImage

    user = UserFactory()
    from footycollect.collection.factories import BaseItemFactory

    base_item = BaseItemFactory(user=user)
    base_item.is_processing_photos = True
    base_item.save(update_fields=["is_processing_photos"])

    img = PILImage.new("RGB", (10, 10), color="blue")
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)
    image_file = SimpleUploadedFile("photo.jpg", buffer.read(), content_type="image/jpeg")

    photo = Photo.objects.create(user=user, content_object=base_item, image=image_file)
    photo.image_avif.save("photo.avif", image_file, save=True)

    check_item_photo_processing(base_item.pk)

    base_item.refresh_from_db()
    assert base_item.is_processing_photos is False
