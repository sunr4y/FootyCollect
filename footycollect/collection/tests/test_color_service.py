"""
Tests for ColorService.
"""

from unittest.mock import Mock, patch

import pytest
from django.test import TestCase

from footycollect.collection.models import Color
from footycollect.collection.services.color_service import ColorService

# Constants for test values
EXPECTED_COLORS_COUNT_3 = 3
EXPECTED_COLORS_COUNT_5 = 5


class TestColorService(TestCase):
    """Test cases for ColorService."""

    def setUp(self):
        """Set up test data."""
        self.service = ColorService()

        # Create test colors
        self.red_color = Color.objects.create(name="RED", hex_value="#FF0000")
        self.blue_color = Color.objects.create(name="BLUE", hex_value="#0000FF")
        self.green_color = Color.objects.create(name="GREEN", hex_value="#008000")

    def test_service_integration_with_repository(self):
        """Test service integration with color repository."""
        # Test that service can retrieve colors for API through repository
        colors_api = self.service.get_colors_for_api()

        assert colors_api is not None
        assert isinstance(colors_api, list)
        assert len(colors_api) == EXPECTED_COLORS_COUNT_3

        # Test that colors are the ones we created
        color_names = [color["name"] for color in colors_api]
        assert "RED" in color_names
        assert "BLUE" in color_names
        assert "GREEN" in color_names

        # Test that each color has required fields
        for color_data in colors_api:
            assert "id" in color_data
            assert "name" in color_data
            assert "hex_value" in color_data

    def test_get_color_by_name_existing(self):
        """Test getting color by existing name."""
        color = self.service.get_color_by_name("RED")

        assert color is not None
        assert color.name == "RED"
        assert color.hex_value == "#FF0000"

    def test_get_color_by_name_nonexistent(self):
        """Test getting color by non-existent name."""
        color = self.service.get_color_by_name("NONEXISTENT")

        assert color is None

    def test_get_colors_for_item_form(self):
        """Test getting colors for item form."""
        colors = self.service.get_colors_for_item_form()

        assert isinstance(colors, dict)
        assert "main_colors" in colors
        assert "secondary_colors" in colors
        assert isinstance(colors["main_colors"], list)
        assert isinstance(colors["secondary_colors"], list)

    def test_get_color_by_hex_existing(self):
        """Test getting color by existing hex value."""
        color = self.service.get_color_by_hex("#FF0000")

        assert color is not None
        assert color.name == "RED"
        assert color.hex_value == "#FF0000"

    def test_get_color_by_hex_nonexistent(self):
        """Test getting color by non-existent hex value."""
        color = self.service.get_color_by_hex("#000000")

        assert color is None

    def test_search_colors(self):
        """Test searching colors."""
        colors = self.service.search_colors("RED")

        assert colors is not None
        # Should return a QuerySet
        assert hasattr(colors, "distinct")

    def test_search_colors_no_results(self):
        """Test searching colors with no results."""
        colors = self.service.search_colors("NONEXISTENT")

        assert colors is not None
        assert hasattr(colors, "distinct")

    def test_create_custom_color_success(self):
        """Test successful custom color creation."""
        color = self.service.create_custom_color("YELLOW", "#FFFF00")

        assert color is not None
        assert color.name == "YELLOW"
        assert color.hex_value == "#FFFF00"

    def test_create_custom_color_invalid_hex(self):
        """Test custom color creation with invalid hex."""
        with pytest.raises(ValueError, match="Invalid hex value format"):
            self.service.create_custom_color("INVALID", "invalid_hex")

    def test_create_custom_color_duplicate_hex(self):
        """Test custom color creation with duplicate hex."""
        with pytest.raises(ValueError, match="Color with this hex value already exists"):
            self.service.create_custom_color("RED_DUPLICATE", "#FF0000")

    def test_get_colors_for_api(self):
        """Test getting colors for API."""
        colors = self.service.get_colors_for_api()

        assert isinstance(colors, list)
        assert len(colors) == EXPECTED_COLORS_COUNT_3

        # Check structure
        for color_data in colors:
            assert "id" in color_data
            assert "name" in color_data
            assert "hex_value" in color_data

    def test_get_color_choices_for_forms(self):
        """Test getting color choices for forms."""
        choices = self.service.get_color_choices_for_forms()

        assert isinstance(choices, list)
        assert len(choices) == EXPECTED_COLORS_COUNT_3

        # Check structure
        for choice in choices:
            assert "value" in choice
            assert "label" in choice
            assert "hex_value" in choice

    def test_get_color_usage_analytics(self):
        """Test getting color usage analytics."""
        with (
            patch.object(self.service, "get_color_statistics") as mock_stats,
            patch.object(self.service.color_repository, "count") as mock_count,
            patch.object(self.service, "get_colors_used_in_collection") as mock_used,
        ):
            mock_stats.return_value = {"total_colors": 3}
            mock_count.return_value = 3
            mock_used.return_value.count.return_value = 2

            analytics = self.service.get_color_usage_analytics()

            assert isinstance(analytics, dict)
            assert "total_colors" in analytics
            assert "used_colors" in analytics
            assert "unused_colors" in analytics
            assert "usage_percentage" in analytics

    def test_get_popular_colors(self):
        """Test getting popular colors."""
        popular_colors = self.service.get_popular_colors(limit=2)

        assert popular_colors is not None
        assert hasattr(popular_colors, "count")

    def test_get_colors_used_in_collection(self):
        """Test getting colors used in collection."""
        with patch.object(self.service.color_repository, "get_colors_used_in_items") as mock_get:
            mock_get.return_value = Mock()

            used_colors = self.service.get_colors_used_in_collection()

            assert used_colors is not None
            mock_get.assert_called_once()

    def test_initialize_default_colors(self):
        """Test initializing default colors."""
        with patch.object(self.service.color_repository, "create_default_colors") as mock_create:
            mock_create.return_value = 5

            result = self.service.initialize_default_colors()

            assert result == EXPECTED_COLORS_COUNT_5
            mock_create.assert_called_once()

    def test_get_color_statistics(self):
        """Test getting color statistics."""
        with patch.object(self.service.color_repository, "get_color_statistics") as mock_stats:
            mock_stats.return_value = {"total_colors": 3}

            stats = self.service.get_color_statistics()

            assert stats == {"total_colors": 3}
            mock_stats.assert_called_once()

    def test_is_valid_hex_valid(self):
        """Test hex validation with valid hex."""
        assert self.service._is_valid_hex("#FF0000") is True
        assert self.service._is_valid_hex("#fff") is True
        assert self.service._is_valid_hex("#ABC123") is True

    def test_is_valid_hex_invalid(self):
        """Test hex validation with invalid hex."""
        assert self.service._is_valid_hex("invalid") is False
        assert self.service._is_valid_hex("#GG0000") is False
        assert self.service._is_valid_hex("FF0000") is False
        assert self.service._is_valid_hex("#FF00") is False
