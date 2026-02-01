"""
Tests for FormService.
"""

from unittest.mock import patch

from django.test import TestCase

from footycollect.collection.models import BaseItem
from footycollect.collection.services.form_service import FormService

# Constants for test values
EXPECTED_CHOICES_COUNT_2 = 2
EXPECTED_CHOICES_COUNT_6 = 6


class TestFormService(TestCase):
    """Test cases for FormService."""

    def setUp(self):
        """Set up test data."""
        self.service = FormService()

    def test_service_initialization(self):
        """Test service initializes correctly."""
        assert self.service is not None
        assert self.service.color_service is not None
        assert self.service.size_service is not None

    def test_get_form_data_for_item_type_jersey(self):
        """Test getting form data for jersey item type."""
        with (
            patch.object(self.service, "_get_color_choices") as mock_colors,
            patch.object(self.service, "_get_size_choices_for_item_type") as mock_sizes,
            patch.object(self.service, "_get_design_choices") as mock_designs,
            patch.object(self.service, "_get_condition_choices") as mock_conditions,
        ):
            mock_colors.return_value = [{"value": 1, "label": "Red"}]
            mock_sizes.return_value = [{"value": 1, "label": "M"}]
            mock_designs.return_value = [{"value": "home", "label": "Home"}]
            mock_conditions.return_value = [{"value": "new", "label": "New"}]

            result = self.service.get_form_data_for_item_type("jersey")

            assert "color_choices" in result
            assert "size_choices" in result
            assert "design_choices" in result
            assert "condition_choices" in result
            mock_colors.assert_called_once()
            mock_sizes.assert_called_once_with("jersey")
            mock_designs.assert_called_once()
            mock_conditions.assert_called_once()

    def test_get_form_data_for_item_type_shorts(self):
        """Test getting form data for shorts item type."""
        with (
            patch.object(self.service, "_get_color_choices") as mock_colors,
            patch.object(self.service, "_get_size_choices_for_item_type") as mock_sizes,
            patch.object(self.service, "_get_design_choices") as mock_designs,
            patch.object(self.service, "_get_condition_choices") as mock_conditions,
        ):
            mock_colors.return_value = [{"value": 1, "label": "Blue"}]
            mock_sizes.return_value = [{"value": 1, "label": "32"}]
            mock_designs.return_value = [{"value": "home", "label": "Home"}]
            mock_conditions.return_value = [{"value": "used", "label": "Used"}]

            result = self.service.get_form_data_for_item_type("shorts")

            assert "color_choices" in result
            assert "size_choices" in result
            assert "design_choices" in result
            assert "condition_choices" in result
            mock_sizes.assert_called_once_with("shorts")

    def test_get_color_choices(self):
        """Test getting color choices."""
        with patch.object(self.service.color_service, "get_color_choices_for_forms") as mock_get:
            mock_get.return_value = [{"value": 1, "label": "Red", "hex_value": "#FF0000"}]

            result = self.service._get_color_choices()

            assert result == [{"value": 1, "label": "Red", "hex_value": "#FF0000"}]
            mock_get.assert_called_once()

    def test_get_size_choices_for_item_type_jersey(self):
        """Test getting size choices for jersey item type."""
        with (
            patch.object(self.service.size_service, "get_sizes_for_item_form") as mock_get_sizes,
            patch.object(self.service, "_get_category_for_item_type") as mock_get_category,
        ):
            mock_get_category.return_value = "tops"
            mock_get_sizes.return_value = {
                "tops": [{"id": 1, "name": "M", "category": "tops"}],
                "bottoms": [{"id": 2, "name": "32", "category": "bottoms"}],
            }

            result = self.service._get_size_choices_for_item_type("jersey")

            assert len(result) == 1
            assert result[0]["value"] == 1
            assert result[0]["label"] == "M"
            assert result[0]["category"] == "tops"
            mock_get_category.assert_called_once_with("jersey")
            mock_get_sizes.assert_called_once()

    def test_get_size_choices_for_item_type_shorts(self):
        """Test getting size choices for shorts item type."""
        with (
            patch.object(self.service.size_service, "get_sizes_for_item_form") as mock_get_sizes,
            patch.object(self.service, "_get_category_for_item_type") as mock_get_category,
        ):
            mock_get_category.return_value = "bottoms"
            mock_get_sizes.return_value = {
                "tops": [{"id": 1, "name": "M", "category": "tops"}],
                "bottoms": [
                    {"id": 2, "name": "32", "category": "bottoms"},
                    {"id": 3, "name": "34", "category": "bottoms"},
                ],
            }

            result = self.service._get_size_choices_for_item_type("shorts")

            assert len(result) == EXPECTED_CHOICES_COUNT_2
            assert result[0]["value"] == EXPECTED_CHOICES_COUNT_2
            assert result[0]["label"] == "32"
            assert result[0]["category"] == "bottoms"

    def test_get_category_for_item_type_jersey(self):
        """Test getting category for jersey item type."""
        result = self.service._get_category_for_item_type("jersey")
        assert result == "tops"

    def test_get_category_for_item_type_shorts(self):
        """Test getting category for shorts item type."""
        result = self.service._get_category_for_item_type("shorts")
        assert result == "bottoms"

    def test_get_category_for_item_type_outerwear(self):
        """Test getting category for outerwear item type."""
        result = self.service._get_category_for_item_type("outerwear")
        assert result == "tops"

    def test_get_category_for_item_type_track_suit(self):
        """Test getting category for track_suit item type."""
        result = self.service._get_category_for_item_type("track_suit")
        assert result == "tops"

    def test_get_category_for_item_type_pants(self):
        """Test getting category for pants item type."""
        result = self.service._get_category_for_item_type("pants")
        assert result == "bottoms"

    def test_get_category_for_item_type_other(self):
        """Test getting category for other item type."""
        result = self.service._get_category_for_item_type("other")
        assert result == "other"

    def test_get_category_for_item_type_unknown(self):
        """Test getting category for unknown item type."""
        result = self.service._get_category_for_item_type("unknown")
        assert result == "other"

    def test_get_design_choices(self):
        """Test getting design choices."""
        result = self.service._get_design_choices()

        # Check that we get the expected design choices from BaseItem
        expected_choices = [{"value": value, "label": label} for value, label in BaseItem.DESIGN_CHOICES]
        assert result == expected_choices
        assert len(result) > 0
        assert all("value" in choice and "label" in choice for choice in result)

    def test_get_condition_choices(self):
        """Test getting condition choices."""
        result = self.service._get_condition_choices()

        # Check that we get the expected condition choices from BaseItem
        expected_choices = [{"value": value, "label": label} for value, label in BaseItem.CONDITION_CHOICES]
        assert result == expected_choices
        assert len(result) > 0
        assert all("value" in choice and "label" in choice for choice in result)

    def test_get_common_form_data(self):
        """Test getting common form data."""
        with (
            patch.object(self.service, "_get_color_choices") as mock_colors,
            patch.object(self.service, "_get_design_choices") as mock_designs,
            patch.object(self.service, "_get_condition_choices") as mock_conditions,
        ):
            mock_colors.return_value = [{"value": 1, "label": "Red"}]
            mock_designs.return_value = [{"value": "home", "label": "Home"}]
            mock_conditions.return_value = [{"value": "new", "label": "New"}]

            result = self.service.get_common_form_data()

            assert "colors" in result
            assert "designs" in result
            assert "conditions" in result
            assert "main_colors" in result["colors"]
            assert "secondary_colors" in result["colors"]
            assert result["colors"]["main_colors"] == mock_colors.return_value
            assert result["colors"]["secondary_colors"] == mock_colors.return_value
            assert result["designs"] == mock_designs.return_value
            assert result["conditions"] == mock_conditions.return_value

    def test_get_item_type_specific_data(self):
        """Test getting item type specific data."""
        with patch.object(self.service, "_get_size_choices_for_item_type") as mock_sizes:
            mock_sizes.return_value = [{"value": 1, "label": "M"}]

            result = self.service.get_item_type_specific_data("jersey")

            assert "sizes" in result
            assert "item_type" in result
            assert result["sizes"] == mock_sizes.return_value
            assert result["item_type"] == "jersey"
            mock_sizes.assert_called_once_with("jersey")

    def test_validate_item_type_valid(self):
        """Test validating valid item types."""
        valid_types = ["jersey", "shorts", "outerwear", "tracksuit", "pants", "other"]

        for item_type in valid_types:
            assert self.service.validate_item_type(item_type) is True

    def test_validate_item_type_invalid(self):
        """Test validating invalid item types."""
        invalid_types = ["unknown", "invalid", "", None]

        for item_type in invalid_types:
            assert self.service.validate_item_type(item_type) is False

    def test_get_available_item_types(self):
        """Test getting available item types."""
        result = self.service.get_available_item_types()

        assert isinstance(result, list)
        assert len(result) == EXPECTED_CHOICES_COUNT_6

        expected_types = [
            {"value": "jersey", "label": "Jersey"},
            {"value": "shorts", "label": "Shorts"},
            {"value": "outerwear", "label": "Outerwear"},
            {"value": "tracksuit", "label": "Tracksuit"},
            {"value": "pants", "label": "Pants"},
            {"value": "other", "label": "Other Item"},
        ]

        assert result == expected_types

        # Check that each item has the expected structure
        for item_type in result:
            assert "value" in item_type
            assert "label" in item_type
            assert isinstance(item_type["value"], str)
            assert isinstance(item_type["label"], str)
