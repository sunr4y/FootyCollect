"""
Tests for ItemFKAPIService.
"""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from footycollect.collection.models import BaseItem, Brand, Jersey, Photo, Size
from footycollect.collection.services.item_fkapi_service import ItemFKAPIService

User = get_user_model()

# Constants for test values
TEST_PASSWORD = "testpass123"


class TestItemFKAPIService(TestCase):
    """Test cases for ItemFKAPIService."""

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

        self.service = ItemFKAPIService()

    def test_init(self):
        """Test service initialization."""
        assert self.service.fkapi_client is not None
        assert self.service.item_service is not None
        assert self.service.photo_service is not None

    @patch("footycollect.collection.services.item_fkapi_service.transaction.atomic")
    def test_process_item_creation_without_kit(self, mock_atomic):
        """Test process_item_creation without kit data."""
        # Create mock form
        mock_form = Mock()
        mock_form.cleaned_data = {
            "name": "Test Jersey",
            "description": "Test description",
            "country_code": "US",
        }
        mock_form.data = {}
        mock_form.save.return_value = self.jersey
        # Mock the id attribute for MTI
        self.jersey.id = self.jersey.base_item.id

        # Mock the atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)

        result = self.service.process_item_creation(mock_form, self.user)

        assert result == self.jersey
        mock_form.save.assert_called_once()

    @patch("footycollect.collection.services.item_fkapi_service.transaction.atomic")
    def test_process_item_creation_with_kit(self, mock_atomic):
        """Test process_item_creation with kit data."""
        # Create mock form
        mock_form = Mock()
        mock_form.cleaned_data = {
            "name": "Test Jersey",
            "description": "Test description",
            "country_code": "US",
            "kit_id": "12345",
        }
        mock_form.data = {}
        mock_form.save.return_value = self.jersey
        # Mock the id attribute for MTI
        self.jersey.id = self.jersey.base_item.id

        # Mock the atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)

        with patch.object(self.service.kit_processor, "process_kit_data") as mock_process_kit:
            result = self.service.process_item_creation(mock_form, self.user)

            assert result == self.jersey
            mock_process_kit.assert_called_once_with(mock_form, "12345")

    @patch("footycollect.collection.services.item_fkapi_service.transaction.atomic")
    def test_process_item_creation_with_photos(self, mock_atomic):
        """Test process_item_creation with photo IDs."""
        # Create mock form
        mock_form = Mock()
        mock_form.cleaned_data = {
            "name": "Test Jersey",
            "description": "Test description",
        }
        mock_form.data = {"photo_ids": "1,2,3"}
        mock_form.save.return_value = self.jersey
        # Mock the id attribute for MTI
        self.jersey.id = self.jersey.base_item.id

        # Mock the atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)

        with patch.object(self.service, "_process_photo_ids") as mock_process_photos:
            result = self.service.process_item_creation(mock_form, self.user)

            assert result == self.jersey
            mock_process_photos.assert_called_once_with("1,2,3", self.jersey)

    def test_setup_form_instance(self):
        """Test _setup_form_instance method."""
        mock_form = Mock()
        mock_form.cleaned_data = {"country_code": "US"}

        self.service._setup_form_instance(mock_form, self.user)

        assert mock_form.instance.user == self.user
        assert mock_form.instance.country == "US"

    def test_setup_form_instance_no_country(self):
        """Test _setup_form_instance without country."""
        mock_form = Mock()
        mock_form.cleaned_data = {}

        self.service._setup_form_instance(mock_form, self.user)

        assert mock_form.instance.user == self.user

    def test_process_kit_data_success(self):
        """Test kit_processor.process_kit_data with successful API call."""
        mock_form = Mock()
        mock_form.cleaned_data = {"description": "Original description"}

        kit_data = {
            "name": "API Kit Name",
            "description": "API description",
            "colors": [{"name": "Red"}, {"name": "Blue"}],
        }

        with (
            patch.object(self.service.kit_processor, "fetch_kit_data", return_value=kit_data) as mock_fetch,
            patch.object(self.service.kit_processor, "_process_kit_information") as mock_process_info,
        ):
            self.service.kit_processor.process_kit_data(mock_form, "12345")

            mock_fetch.assert_called_once_with("12345")
            mock_process_info.assert_called_once_with(mock_form, kit_data)

    def test_process_kit_data_no_data(self):
        """Test kit_processor.process_kit_data with no API data."""
        mock_form = Mock()

        with (
            patch.object(self.service.kit_processor, "fetch_kit_data", return_value=None),
            patch.object(self.service.kit_processor, "_process_kit_information") as mock_process_info,
        ):
            self.service.kit_processor.process_kit_data(mock_form, "12345")

            mock_process_info.assert_not_called()

    def test_process_kit_data_exception(self):
        """Test kit_processor.process_kit_data with API exception."""
        mock_form = Mock()

        with (
            patch.object(self.service.kit_processor, "fetch_kit_data", side_effect=Exception("API Error")),
            pytest.raises(Exception, match="API Error"),
        ):
            self.service.kit_processor.process_kit_data(mock_form, "12345")

    def test_fetch_kit_data_from_api_success(self):
        """Test kit_processor.fetch_kit_data with successful call."""
        with patch.object(self.service.kit_processor.fkapi_client, "get_kit_details") as mock_get:
            mock_get.return_value = {"name": "Test Kit"}

            result = self.service.kit_processor.fetch_kit_data("12345")

            assert result == {"name": "Test Kit"}
            mock_get.assert_called_once_with("12345")

    def test_fetch_kit_data_from_api_exception(self):
        """Test kit_processor.fetch_kit_data with API unavailable."""
        with patch.object(self.service.kit_processor.fkapi_client, "get_kit_details") as mock_get:
            mock_get.return_value = None

            result = self.service.kit_processor.fetch_kit_data("12345")

            assert result is None
            mock_get.assert_called_once_with("12345")

    def test_add_kit_id_to_description(self):
        """Test kit_processor._add_kit_id_to_description method."""
        mock_form = Mock()
        mock_form.cleaned_data = {"description": "Original description"}

        self.service.kit_processor._add_kit_id_to_description(mock_form, "12345")

        assert mock_form.cleaned_data["description"] == "Original description\n\n[Kit ID: 12345]"

    def test_add_kit_id_to_description_already_exists(self):
        """Test kit_processor._add_kit_id_to_description when kit ID already exists."""
        mock_form = Mock()
        mock_form.cleaned_data = {"description": "Original description\n\n[Kit ID: 12345]"}

        self.service.kit_processor._add_kit_id_to_description(mock_form, "12345")

        assert mock_form.cleaned_data["description"] == "Original description\n\n[Kit ID: 12345]"

    def test_process_kit_information(self):
        """Test kit_processor._process_kit_information method."""
        mock_form = Mock()
        mock_form.cleaned_data = {"description": "Original description"}
        mock_form.data = {}

        kit_data = {
            "name": "API Kit Name",
            "description": "API description",
            "colors": [{"name": "Red"}, {"name": "Blue"}],
        }

        with patch.object(self.service.kit_processor, "_process_kit_colors") as mock_process_colors:
            self.service.kit_processor._process_kit_information(mock_form, kit_data)

            assert mock_form.cleaned_data["name"] == "API Kit Name"
            assert "API description" in mock_form.cleaned_data["description"]
            mock_process_colors.assert_called_once_with(mock_form, [{"name": "Red"}, {"name": "Blue"}])

    def test_process_kit_colors(self):
        """Test kit_processor._process_kit_colors method."""
        mock_form = Mock()
        mock_form.data = {}

        colors = [{"name": "Red"}, {"name": "Blue"}, {"name": "Green"}]

        self.service.kit_processor._process_kit_colors(mock_form, colors)

        assert mock_form.data["main_color"] == "Red"
        assert mock_form.data["secondary_colors"] == ["Blue", "Green"]

    def test_process_kit_colors_empty(self):
        """Test kit_processor._process_kit_colors with empty colors."""
        mock_form = Mock()
        mock_form.data = {}

        self.service.kit_processor._process_kit_colors(mock_form, [])

        assert "main_color" not in mock_form.data

    def test_process_kit_colors_single_color(self):
        """Test kit_processor._process_kit_colors with single color."""
        mock_form = Mock()
        mock_form.data = {}

        colors = [{"name": "Red"}]

        self.service.kit_processor._process_kit_colors(mock_form, colors)

        assert mock_form.data["main_color"] == "Red"
        assert "secondary_colors" not in mock_form.data

    def test_process_photo_ids_success(self):
        """Test _process_photo_ids with valid photo IDs."""
        # Create test photos
        photo1 = Photo.objects.create(
            content_object=self.jersey,
            image=SimpleUploadedFile("test1.jpg", b"fake content", content_type="image/jpeg"),
            user=self.user,
        )
        photo2 = Photo.objects.create(
            content_object=self.jersey,
            image=SimpleUploadedFile("test2.jpg", b"fake content", content_type="image/jpeg"),
            user=self.user,
        )

        photo_ids = f"{photo1.id},{photo2.id}"
        # Mock the id attribute for MTI
        self.jersey.id = self.jersey.base_item.id

        self.service._process_photo_ids(photo_ids, self.jersey)

        # Check that photos are associated with the item
        photo1.refresh_from_db()
        photo2.refresh_from_db()
        assert photo1.content_object == self.jersey
        assert photo2.content_object == self.jersey

    def test_process_photo_ids_empty(self):
        """Test _process_photo_ids with empty string."""
        self.service._process_photo_ids("", self.jersey)
        # Should not raise any exception

    def test_process_photo_ids_invalid(self):
        """Test _process_photo_ids with invalid photo IDs."""
        with pytest.raises(Exception, match="Photo matching query does not exist"):
            self.service._process_photo_ids("999,1000", self.jersey)

    def test_get_form_data_for_item_creation(self):
        """Test get_form_data_for_item_creation method."""
        with patch("footycollect.collection.services.item_fkapi_service.ItemService") as mock_item_service:
            mock_service_instance = Mock()
            mock_service_instance.get_form_data.return_value = {
                "colors": {"main_colors": [{"value": "red", "label": "Red"}]},
            }
            mock_item_service.return_value = mock_service_instance

            result = self.service.get_form_data_for_item_creation()

            assert "color_choices" in result
            assert "design_choices" in result
            assert result["color_choices"] == [{"value": "red", "label": "Red"}]
            assert len(result["design_choices"]) > 0  # Should have design choices
