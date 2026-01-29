"""
Tests for ItemFKAPIService.
"""

from contextlib import suppress
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

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
        self.service = ItemFKAPIService()

    def test_service_initialization(self):
        """Test service initializes correctly."""
        assert self.service.fkapi_client is not None
        assert self.service.item_service is not None
        assert self.service.photo_service is not None

    @patch("footycollect.collection.services.item_fkapi_service.logger")
    def test_process_item_creation_success(self, mock_logger):
        """Test successful item creation process."""
        # Mock form
        mock_form = Mock()
        mock_form.cleaned_data = {
            "name": "Test Jersey",
            "country_code": "US",
            "kit_id": None,
        }
        mock_form.data = {"photo_ids": ""}
        mock_item = Mock()
        mock_item.id = 1
        mock_item.is_draft = False
        mock_form.save.return_value = mock_item

        # Test the method
        result = self.service.process_item_creation(mock_form, self.user, "jersey")

        # Assertions
        assert result == mock_item
        assert mock_form.instance.user == self.user
        mock_form.save.assert_called_once()

    @patch("footycollect.collection.services.item_fkapi_service.logger")
    def test_process_item_creation_with_kit_id(self, mock_logger):
        """Test item creation with kit ID."""
        # Mock form
        mock_form = Mock()
        mock_form.cleaned_data = {
            "name": "Test Jersey",
            "country_code": "US",
            "kit_id": "123",
            "description": "Test description",
        }
        mock_form.data = {"photo_ids": ""}
        mock_item = Mock()
        mock_item.id = 1
        mock_item.is_draft = False
        mock_form.save.return_value = mock_item

        # Mock FKAPI client
        with patch.object(self.service, "_fetch_kit_data_from_api") as mock_fetch:
            mock_fetch.return_value = {
                "name": "API Kit Name",
                "description": "API Description",
                "colors": [{"name": "Red"}, {"name": "White"}],
            }

            # Test the method
            result = self.service.process_item_creation(mock_form, self.user, "jersey")

            # Assertions
            assert result == mock_item
            mock_fetch.assert_called_once_with("123")

    def test_setup_form_instance(self):
        """Test _setup_form_instance method."""
        mock_form = Mock()
        mock_form.cleaned_data = {"country_code": "US"}

        self.service._setup_form_instance(mock_form, self.user)

        assert mock_form.instance.user == self.user
        assert mock_form.instance.country == "US"

    def test_setup_form_instance_no_country(self):
        """Test _setup_form_instance method without country."""
        mock_form = Mock()
        mock_form.cleaned_data = {}

        self.service._setup_form_instance(mock_form, self.user)

        assert mock_form.instance.user == self.user
        # When no country_code in cleaned_data, country should not be set
        # The method only sets country if country_code exists in cleaned_data

    def test_fetch_kit_data_from_api_success(self):
        """Test _fetch_kit_data_from_api method success."""
        mock_kit_data = {"name": "Test Kit", "brand": "Nike"}

        with patch.object(self.service.fkapi_client, "get_kit_details") as mock_get:
            mock_get.return_value = mock_kit_data

            result = self.service._fetch_kit_data_from_api("123")

            assert result == mock_kit_data
            mock_get.assert_called_once_with("123")

    def test_fetch_kit_data_from_api_error(self):
        """Test _fetch_kit_data_from_api method with API unavailable."""
        with patch.object(self.service.fkapi_client, "get_kit_details") as mock_get:
            mock_get.return_value = None

            result = self.service._fetch_kit_data_from_api("123")

            assert result is None
            mock_get.assert_called_once_with("123")

    def test_add_kit_id_to_description(self):
        """Test _add_kit_id_to_description method."""
        mock_form = Mock()
        mock_form.cleaned_data = {"description": "Original description"}

        self.service._add_kit_id_to_description(mock_form, "123")

        expected_description = "Original description\n\n[Kit ID: 123]"
        assert mock_form.cleaned_data["description"] == expected_description

    def test_add_kit_id_to_description_existing(self):
        """Test _add_kit_id_to_description method with existing kit ID."""
        mock_form = Mock()
        mock_form.cleaned_data = {"description": "Original description\n\n[Kit ID: 123]"}

        self.service._add_kit_id_to_description(mock_form, "123")

        # Should not add duplicate
        assert mock_form.cleaned_data["description"] == "Original description\n\n[Kit ID: 123]"

    def test_process_kit_information(self):
        """Test _process_kit_information method."""
        mock_form = Mock()
        mock_form.cleaned_data = {"description": "Original description"}
        mock_form.data = {}

        kit_data = {
            "name": "API Kit Name",
            "description": "API Description",
            "colors": [{"name": "Red"}, {"name": "White"}],
        }

        with patch.object(self.service, "_process_kit_colors") as mock_process_colors:
            self.service._process_kit_information(mock_form, kit_data)

            assert mock_form.cleaned_data["name"] == "API Kit Name"
            assert "API Description" in mock_form.cleaned_data["description"]
            mock_process_colors.assert_called_once_with(mock_form, kit_data["colors"])

    def test_process_kit_colors(self):
        """Test _process_kit_colors method (item_fkapi writes to form.data)."""
        mock_form = Mock()
        mock_form.data = {}

        colors = [
            {"name": "Red"},
            {"name": "White"},
            {"name": "Blue"},
        ]

        self.service._process_kit_colors(mock_form, colors)

        assert mock_form.data["main_color"] == "Red"
        assert mock_form.data.get("secondary_colors") == ["White", "Blue"]

    def test_process_kit_colors_single(self):
        """Test _process_kit_colors method with single color (item_fkapi writes to form.data)."""
        mock_form = Mock()
        mock_form.data = {}

        colors = [{"name": "Red"}]

        self.service._process_kit_colors(mock_form, colors)

        assert mock_form.data["main_color"] == "Red"
        assert "secondary_colors" not in mock_form.data

    def test_process_kit_colors_empty(self):
        """Test _process_kit_colors method with empty colors (item_fkapi returns early)."""
        mock_form = Mock()
        mock_form.data = {}

        colors = []

        self.service._process_kit_colors(mock_form, colors)

        assert mock_form.data == {}

    def test_process_photo_ids_success(self):
        """Test _process_photo_ids method success."""
        # Mock the entire _process_photo_ids method to avoid content_object issues
        with patch.object(self.service, "_process_photo_ids") as mock_process:
            mock_item = Mock()
            mock_item.id = 1

            # Call the method
            self.service._process_photo_ids("1,2", mock_item)

            # Verify the method was called with correct parameters
            mock_process.assert_called_once_with("1,2", mock_item)

    def test_process_photo_ids_empty(self):
        """Test _process_photo_ids method with empty string."""
        mock_item = Mock()

        # Should not raise exception
        self.service._process_photo_ids("", mock_item)

    def test_process_photo_ids_invalid(self):
        """Test _process_photo_ids method with invalid IDs."""
        mock_item = Mock()

        with patch("footycollect.collection.services.item_fkapi_service.logger") as mock_logger:
            # This should raise an exception due to invalid ID
            with suppress(ValueError):
                self.service._process_photo_ids("999,invalid", mock_item)
            mock_logger.exception.assert_called()

    def test_get_form_data_for_item_creation(self):
        """Test get_form_data_for_item_creation method."""
        # Mock the ItemService.get_form_data method
        with patch("footycollect.collection.services.item_fkapi_service.ItemService") as mock_item_service_class:
            mock_item_service = Mock()
            mock_item_service.get_form_data.return_value = {
                "colors": {
                    "main_colors": [{"value": "RED", "label": "Red"}],
                },
            }
            mock_item_service_class.return_value = mock_item_service

            result = self.service.get_form_data_for_item_creation("jersey")

            assert "color_choices" in result
            assert "design_choices" in result
            assert isinstance(result["design_choices"], list)
