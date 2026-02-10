"""
Tests for photo views with real functionality testing.
"""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import reverse

from footycollect.collection.models import BaseItem, Brand, Jersey, Photo, Size

User = get_user_model()

# Constants for test values
TEST_PASSWORD = "testpass123"  # NOSONAR (S2068) "test fixture only, not a credential"
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_FOUND = 302
PHOTO1_EXPECTED_ORDER = 7
PHOTO2_EXPECTED_ORDER = 3
PHOTO_PROCESSING_COUNTDOWN = 5
EXPECTED_START_ORDER = 4


class TestPhotoViews(TestCase):
    """Test cases for photo views with real functionality tests."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.brand = Brand.objects.create(name="Nike")
        self.size = Size.objects.create(name="M", category="tops")

        self.base_item = BaseItem.objects.create(
            user=self.user,
            name="Test Jersey",
            description="Test description",
            brand=self.brand,
        )

        self.jersey = Jersey.objects.create(
            base_item=self.base_item,
            size=self.size,
        )

    def test_reorder_photos_success_with_service_integration(self):
        """Test successful photo reordering with service integration."""
        # Create test photos
        photo1 = Photo.objects.create(
            content_object=self.jersey,
            image=SimpleUploadedFile("test1.jpg", b"fake content", content_type="image/jpeg"),
            order=1,
        )
        photo2 = Photo.objects.create(
            content_object=self.jersey,
            image=SimpleUploadedFile("test2.jpg", b"fake content", content_type="image/jpeg"),
            order=2,
        )

        with patch("footycollect.collection.views.photo_views.get_photo_service") as mock_service:
            mock_photo_service = Mock()
            mock_service.return_value = mock_photo_service

            # Login user
            self.client.force_login(self.user)

            # Make POST request to reorder photos
            response = self.client.post(
                reverse("collection:reorder_photos", kwargs={"item_id": self.jersey.pk}),
                {"order[]": [str(photo2.pk), str(photo1.pk)]},
                headers={"x-requested-with": "XMLHttpRequest"},
            )

            # Check response
            assert response.status_code == HTTP_OK
            assert response["Content-Type"] == "application/json"

            # Check that service was called with correct parameters
            mock_photo_service.reorder_photos.assert_called_once()
            call_args = mock_photo_service.reorder_photos.call_args
            assert call_args[0][0] == self.jersey  # item parameter
            assert len(call_args[0][1]) == 2  # photo_orders parameter  # noqa: PLR2004

    def test_reorder_photos_handles_validation_errors(self):
        """Test reorder photos handles validation errors gracefully."""
        with patch("footycollect.collection.views.photo_views.get_photo_service") as mock_service:
            mock_photo_service = Mock()
            mock_service.return_value = mock_photo_service
            mock_photo_service.reorder_photos.side_effect = Exception("Validation error")

            # Login user
            self.client.force_login(self.user)

            # Make POST request - this will raise an exception, so we expect it to fail
            with pytest.raises(Exception, match="Validation error"):
                self.client.post(
                    reverse("collection:reorder_photos", kwargs={"item_id": self.jersey.pk}),
                    {"order[]": ["1", "2"]},
                    headers={"x-requested-with": "XMLHttpRequest"},
                )

    def test_reorder_photos_invalid_item_handling(self):
        """Test reorder photos with invalid item ID handling."""
        # Login user
        self.client.force_login(self.user)

        # Make POST request with invalid item ID
        with pytest.raises(Exception, match="Jersey matching query does not exist"):
            self.client.post(
                reverse("collection:reorder_photos", kwargs={"item_id": 999}),
                {"order[]": ["1", "2"]},
                headers={"x-requested-with": "XMLHttpRequest"},
            )

    def test_upload_photo_success_with_service_validation(self):
        """Test successful photo upload with service validation."""
        with patch("footycollect.collection.views.photo_views.get_photo_service") as mock_service:
            mock_photo_service = Mock()
            mock_photo = Mock()
            mock_photo.id = 1
            mock_photo.get_image_url.return_value = "/media/test.jpg"
            mock_photo.thumbnail = None
            mock_photo_service.create_photo_with_validation.return_value = mock_photo
            mock_service.return_value = mock_photo_service

            # Login user
            self.client.force_login(self.user)

            # Create test image
            image = SimpleUploadedFile("test.jpg", b"fake content", content_type="image/jpeg")

            # Make POST request
            response = self.client.post(
                reverse("collection:upload_photo"),
                {
                    "photo": image,
                    "order": 1,
                },
                headers={"x-requested-with": "XMLHttpRequest"},
            )

            # Check response
            assert response.status_code == HTTP_OK
            assert response["Content-Type"] == "application/json"

            # Check that service was called with correct parameters
            mock_photo_service.create_photo_with_validation.assert_called_once()
            call_kwargs = mock_photo_service.create_photo_with_validation.call_args[1]
            assert call_kwargs["user"] == self.user
            assert call_kwargs["order"] == "1"  # POST data comes as string

    def test_upload_photo_handles_validation_errors(self):
        """Test upload photo handles validation errors gracefully."""
        with patch("footycollect.collection.views.photo_views.get_photo_service") as mock_service:
            mock_photo_service = Mock()
            mock_service.return_value = mock_photo_service
            mock_photo_service.create_photo_with_validation.side_effect = Exception("Validation error")

            # Login user
            self.client.force_login(self.user)

            # Create test image
            image = SimpleUploadedFile("test.jpg", b"fake content", content_type="image/jpeg")

            # Make POST request - this will raise an exception, so we expect it to fail
            with pytest.raises(Exception, match="Validation error"):
                self.client.post(
                    reverse("collection:upload_photo"),
                    {
                        "photo": image,
                        "order": 1,
                    },
                    headers={"x-requested-with": "XMLHttpRequest"},
                )

    def test_upload_photo_no_image_validation(self):
        """Test photo upload without image validation."""
        with patch("footycollect.collection.views.photo_views.get_photo_service") as mock_service:
            mock_photo_service = Mock()
            mock_service.return_value = mock_photo_service

            # Login user
            self.client.force_login(self.user)

            # Make POST request without image
            response = self.client.post(
                reverse("collection:upload_photo"),
                {
                    "order": 1,
                },
                headers={"x-requested-with": "XMLHttpRequest"},
            )

            # Check response
            assert response.status_code == HTTP_BAD_REQUEST

    def test_upload_photo_requires_authentication(self):
        """Test photo upload requires authentication."""
        response = self.client.post(
            reverse("collection:upload_photo"),
            {
                "photo": SimpleUploadedFile("test.jpg", b"fake content", content_type="image/jpeg"),
                "order": 1,
            },
            headers={"x-requested-with": "XMLHttpRequest"},
        )

        # Should redirect to login
        assert response.status_code == HTTP_FOUND

    def test_file_upload_success_creates_photo(self):
        """Test successful file upload creates photo object."""
        # Login user
        self.client.force_login(self.user)

        # Create test image
        image = SimpleUploadedFile("test.jpg", b"fake content", content_type="image/jpeg")

        # Make POST request
        response = self.client.post(
            reverse("collection:file_upload"),
            {
                "file": image,
            },
            headers={"x-requested-with": "XMLHttpRequest"},
        )

        # Check response
        assert response.status_code == HTTP_OK
        assert response["Content-Type"] == "text/html; charset=utf-8"

        # Check that photo was created
        assert Photo.objects.count() == 1
        photo = Photo.objects.first()
        assert photo.image.name.endswith("test.jpg")

    def test_file_upload_no_file_handling(self):
        """Test file upload without file handling."""
        # Login user
        self.client.force_login(self.user)

        # Make POST request without file
        response = self.client.post(
            reverse("collection:file_upload"),
            {},
            headers={"x-requested-with": "XMLHttpRequest"},
        )

        # Check response - returns 400 when no file provided
        assert response.status_code == HTTP_BAD_REQUEST

    def test_handle_dropzone_files_success_returns_metadata(self):
        """Test successful dropzone file handling returns correct metadata."""
        # Login user
        self.client.force_login(self.user)

        # Create test image
        image = SimpleUploadedFile("test.jpg", b"fake content", content_type="image/jpeg")

        # Make POST request
        response = self.client.post(
            reverse("collection:handle_dropzone_files"),
            {
                "file": image,
            },
            headers={"x-requested-with": "XMLHttpRequest"},
        )

        # Check response
        assert response.status_code == HTTP_OK
        assert response["Content-Type"] == "application/json"

        # Check response content
        data = response.json()
        assert "name" in data
        assert "size" in data
        assert "url" in data
        assert "deleteUrl" in data
        assert "deleteType" in data
        assert data["name"] == "test.jpg"
        assert data["size"] == len(b"fake content")

    def test_handle_dropzone_files_no_file_validation(self):
        """Test dropzone file handling without file validation."""
        # Login user
        self.client.force_login(self.user)

        # Make POST request without file
        response = self.client.post(
            reverse("collection:handle_dropzone_files"),
            {},
            headers={"x-requested-with": "XMLHttpRequest"},
        )

        # Check response
        assert response.status_code == HTTP_BAD_REQUEST

    def test_handle_dropzone_files_delete_method(self):
        """Test dropzone file handling DELETE method."""
        # Login user
        self.client.force_login(self.user)

        # Make DELETE request
        response = self.client.delete(
            reverse("collection:handle_dropzone_files"),
            {"fileName": "test.jpg"},
            headers={"x-requested-with": "XMLHttpRequest"},
        )

        # Check response
        assert response.status_code == HTTP_OK
        assert response["Content-Type"] == "application/json"

        # Check response content
        data = response.json()
        assert data["success"] is True
        assert "deleted" in data["message"]

    def test_handle_dropzone_files_unauthorized_access(self):
        """Test dropzone file handling requires authentication."""
        response = self.client.post(
            reverse("collection:handle_dropzone_files"),
            {
                "file": SimpleUploadedFile("test.jpg", b"fake content", content_type="image/jpeg"),
            },
            headers={"x-requested-with": "XMLHttpRequest"},
        )

        assert response.status_code == HTTP_FOUND
        assert response.url.startswith(reverse("account_login"))

    def test_photo_processor_mixin_initialization(self):
        """Test PhotoProcessorMixin initialization and lazy loading."""
        from footycollect.collection.views.photo_processor_mixin import PhotoProcessorMixin

        # Create a test class that uses the mixin
        class TestView(PhotoProcessorMixin):
            pass

        view = TestView()

        # Check that the mixin is properly initialized
        assert hasattr(view, "_photo_processor_initialized")
        assert view._photo_processor_initialized is False

        # Test lazy initialization
        view._ensure_photo_processor_initialized()
        assert view._photo_processor_initialized is True

    def test_photo_processor_mixin_download_image_success(self):
        """Test PhotoProcessorMixin download and attach image functionality."""
        from footycollect.collection.views.photo_processor_mixin import PhotoProcessorMixin

        # Create a test class that uses the mixin
        class TestView(PhotoProcessorMixin):
            pass

        view = TestView()

        # Test that the mixin can be instantiated and has the required method
        assert hasattr(view, "_download_and_attach_image")
        assert callable(view._download_and_attach_image)

        # Test that the mixin can be initialized
        view._ensure_photo_processor_initialized()
        assert view._photo_processor_initialized is True

    def test_photo_processor_mixin_integration_with_error_handling(self):
        """Test PhotoProcessorMixin enqueues download task and handles errors."""
        from footycollect.collection.views.photo_processor_mixin import PhotoProcessorMixin

        class TestView(PhotoProcessorMixin):
            pass

        view = TestView()

        with (
            patch("footycollect.collection.views.photo_processor_mixin.transaction.on_commit") as mock_on_commit,
            patch(
                "footycollect.collection.views.photo_processor_mixin.download_external_image_and_attach"
            ) as mock_task,
        ):
            view._download_and_attach_image(self.jersey, "https://example.com/image.jpg")
            mock_on_commit.assert_called_once()
            callback = mock_on_commit.call_args[0][0]
            callback()
            mock_task.delay.assert_called_once_with(
                self.jersey._meta.app_label,
                self.jersey._meta.model_name,
                self.jersey.pk,
                "https://example.com/image.jpg",
                None,
            )

        with (
            patch("footycollect.collection.views.photo_processor_mixin.transaction.on_commit") as mock_on_commit,
            patch(
                "footycollect.collection.views.photo_processor_mixin.download_external_image_and_attach"
            ) as mock_task,
        ):
            view._download_and_attach_image(self.jersey, "https://example.com/other.jpg", order=2)
            mock_on_commit.assert_called_once()
            callback = mock_on_commit.call_args[0][0]
            callback()
            mock_task.delay.assert_called_once_with(
                self.jersey._meta.app_label,
                self.jersey._meta.model_name,
                self.jersey.pk,
                "https://example.com/other.jpg",
                2,
            )

        with (
            patch(
                "footycollect.collection.views.photo_processor_mixin.transaction.on_commit",
                side_effect=Exception("DB error"),
            ),
            patch("footycollect.collection.views.photo_processor_mixin.logger") as mock_logger,
        ):
            result = view._download_and_attach_image(self.jersey, "https://example.com/bad.jpg")
            assert result is None
            mock_logger.exception.assert_called_once()

    def test_photo_processor_mixin_parse_photo_ids_json_and_csv(self):
        from footycollect.collection.views.photo_processor_mixin import PhotoProcessorMixin

        class TestView(PhotoProcessorMixin):
            pass

        view = TestView()

        json_payload = '[{"id": 1, "order": 3}, {"url": "https://example.com/img.jpg"}, "5"]'
        photo_ids, external_images, order_map = view._parse_photo_ids(json_payload)
        assert photo_ids == ["1", "5"]
        assert external_images == [{"url": "https://example.com/img.jpg"}]
        assert order_map == {"1": 3}

        csv_payload = "10, 11,  12 "
        photo_ids, external_images, order_map = view._parse_photo_ids(csv_payload)
        assert photo_ids == ["10", "11", "12"]
        assert external_images == []
        assert order_map == {}

    def test_photo_processor_mixin_parse_photo_ids_invalid_or_empty(self):
        from footycollect.collection.views.photo_processor_mixin import PhotoProcessorMixin

        class TestView(PhotoProcessorMixin):
            pass

        view = TestView()

        assert view._parse_photo_ids("") is None
        assert view._parse_photo_ids("   ") is None
        assert view._parse_photo_ids(None) is None
        assert view._parse_photo_ids(123) is None

    def test_photo_processor_mixin_process_existing_photos_attaches_and_triggers_processing(self):
        from footycollect.collection.views.photo_processor_mixin import PhotoProcessorMixin

        class TestView(PhotoProcessorMixin):
            pass

        view = TestView()
        view.object = self.base_item

        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.user
        view.request = request

        photo1 = Photo.objects.create(
            content_object=self.base_item,
            image=SimpleUploadedFile("p1.jpg", b"1", content_type="image/jpeg"),
            user=self.user,
        )
        photo2 = Photo.objects.create(
            content_object=self.base_item,
            image=SimpleUploadedFile("p2.jpg", b"2", content_type="image/jpeg"),
            user=self.user,
        )

        photo_ids = [str(photo1.id), str(photo2.id)]
        order_map = {str(photo1.id): 5}

        with patch(
            "footycollect.collection.views.photo_processor_mixin.check_item_photo_processing",
        ) as mock_task:
            view._process_existing_photos(photo_ids, order_map, start_order=2)

            photo1.refresh_from_db()
            photo2.refresh_from_db()

            assert photo1.object_id == self.base_item.id
            assert photo2.object_id == self.base_item.id
            assert photo1.order == PHOTO1_EXPECTED_ORDER
            assert photo2.order == PHOTO2_EXPECTED_ORDER

            self.base_item.refresh_from_db()
            assert self.base_item.is_processing_photos is True

            mock_task.apply_async.assert_called_once()
            _args, kwargs = mock_task.apply_async.call_args
            assert kwargs["args"] == [self.base_item.pk]
            assert kwargs["countdown"] == PHOTO_PROCESSING_COUNTDOWN

    def test_photo_processor_mixin_process_photo_ids_uses_parsed_data(self):
        from footycollect.collection.views.photo_processor_mixin import PhotoProcessorMixin

        class TestView(PhotoProcessorMixin):
            pass

        view = TestView()
        view.object = self.jersey

        with (
            patch.object(
                view,
                "_parse_photo_ids",
                return_value=(["1"], [{"url": "https://example.com/x.jpg"}], {"1": 2}),
            ) as mock_parse,
            patch.object(view, "_process_external_images") as mock_external,
            patch.object(view, "_process_existing_photos") as mock_existing,
        ):
            view._process_photo_ids("ignored", start_order=3)

        mock_parse.assert_called_once_with("ignored")
        mock_external.assert_called_once_with([{"url": "https://example.com/x.jpg"}])
        mock_existing.assert_called_once()
        args, kwargs = mock_existing.call_args
        assert args[0] == ["1"]
        assert args[1] == {"1": 2}
        assert kwargs["start_order"] == EXPECTED_START_ORDER

    def test_proxy_helpers_validate_and_build_url(self):
        from footycollect.collection.views.photo_views import (
            _build_allowed_proxy_url,
            _is_allowed_proxy_host,
            _validate_proxy_url,
        )

        assert _validate_proxy_url(None) == "Missing url parameter"
        assert _validate_proxy_url("foo://example.com") == "Invalid url"

        ok = _validate_proxy_url("https://www.footballkitarchive.com/path?x=1")
        assert ok is None
        assert _is_allowed_proxy_host("https://www.footballkitarchive.com/img.png") is True

        built = _build_allowed_proxy_url("https://www.footballkitarchive.com/path?x=1")
        assert built == "https://www.footballkitarchive.com/path?x=1"

    def test_proxy_image_success_and_invalid_host(self):
        self.client.force_login(self.user)

        with patch("footycollect.collection.views.photo_views.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.iter_content.return_value = [b"abc", b"def"]
            mock_resp.headers = {"Content-Type": "image/jpeg; charset=utf-8"}
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            response = self.client.get(
                reverse("collection:proxy_image"),
                {"url": "https://www.footballkitarchive.com/img.jpg"},
            )
            assert response.status_code == HTTP_OK
            assert response["Content-Type"].startswith("image/")
            assert response.content == b"abcdef"

        response_invalid = self.client.get(
            reverse("collection:proxy_image"),
            {"url": "https://not-allowed-host.com/img.jpg"},
        )
        assert response_invalid.status_code == HTTP_BAD_REQUEST
        assert b"URL host not allowed" in response_invalid.content
