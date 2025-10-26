"""
Tests for CollectionService.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from footycollect.collection.services.collection_service import CollectionService

User = get_user_model()

# Constants for test values
TEST_PASSWORD = "testpass123"
EXPECTED_ITEMS_COUNT_10 = 10
EXPECTED_ITEMS_COUNT_8 = 8
EXPECTED_ITEMS_COUNT_25 = 25
EXPECTED_ITEMS_COUNT_100 = 100


class TestCollectionService(TestCase):
    """Test cases for CollectionService."""

    def setUp(self):
        """Set up test data."""
        self.service = CollectionService()

        # Create test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )

    def test_service_initialization(self):
        """Test service initializes correctly."""
        assert self.service is not None
        assert self.service.item_service is not None
        assert self.service.photo_service is not None
        assert self.service.color_service is not None
        assert self.service.size_service is not None

    def test_initialize_collection_data(self):
        """Test initializing collection data."""
        with (
            patch.object(self.service.color_service, "initialize_default_colors") as mock_colors,
            patch.object(self.service.size_service, "initialize_default_sizes") as mock_sizes,
        ):
            mock_colors.return_value = 10
            mock_sizes.return_value = 8

            result = self.service.initialize_collection_data()

            assert result == {"colors": 10, "sizes": 8}
            mock_colors.assert_called_once()
            mock_sizes.assert_called_once()

    def test_get_collection_statistics(self):
        """Test getting collection statistics."""
        with (
            patch.object(self.service.color_service.color_repository, "count") as mock_color_count,
            patch.object(self.service.size_service.size_repository, "count") as mock_size_count,
            patch.object(self.service.item_service.item_repository, "count") as mock_item_count,
            patch.object(self.service.photo_service.photo_repository, "count") as mock_photo_count,
            patch.object(self.service.color_service, "get_color_usage_analytics") as mock_color_analytics,
            patch.object(self.service.size_service, "get_size_distribution_by_category") as mock_size_dist,
        ):
            mock_color_count.return_value = 10
            mock_size_count.return_value = 8
            mock_item_count.return_value = 25
            mock_photo_count.return_value = 100
            mock_color_analytics.return_value = {"usage_percentage": 80}
            mock_size_dist.return_value = {"tops": 5, "bottoms": 3}

            result = self.service.get_collection_statistics()

            assert "total_colors" in result
            assert "total_sizes" in result
            assert "total_items" in result
            assert "total_photos" in result
            assert "color_distribution" in result
            assert "size_distribution" in result
            assert result["total_colors"] == EXPECTED_ITEMS_COUNT_10
            assert result["total_sizes"] == EXPECTED_ITEMS_COUNT_8
            assert result["total_items"] == EXPECTED_ITEMS_COUNT_25
            assert result["total_photos"] == EXPECTED_ITEMS_COUNT_100

    def test_get_form_data(self):
        """Test getting form data."""
        with (
            patch.object(self.service.color_service, "get_colors_for_item_form") as mock_colors,
            patch.object(self.service.size_service, "get_sizes_for_item_form") as mock_sizes,
        ):
            mock_colors.return_value = {"main_colors": [{"value": 1, "label": "Red"}]}
            mock_sizes.return_value = {"tops": [{"id": 1, "name": "M"}]}

            result = self.service.get_form_data()

            assert "colors" in result
            assert "sizes" in result
            assert result["colors"] == mock_colors.return_value
            assert result["sizes"] == mock_sizes.return_value

    def test_get_api_data(self):
        """Test getting API data."""
        with (
            patch.object(self.service.color_service, "get_colors_for_api") as mock_colors,
            patch.object(self.service.size_service, "get_sizes_for_api") as mock_sizes,
        ):
            mock_colors.return_value = [{"id": 1, "name": "Red", "hex_value": "#FF0000"}]
            mock_sizes.return_value = [{"id": 1, "name": "M", "category": "tops"}]

            result = self.service.get_api_data()

            assert "colors" in result
            assert "sizes" in result
            assert result["colors"] == mock_colors.return_value
            assert result["sizes"] == mock_sizes.return_value

    def test_cleanup_unused_data(self):
        """Test cleaning up unused data."""
        result = self.service.cleanup_unused_data()

        assert "unused_colors_removed" in result
        assert "unused_sizes_removed" in result
        assert "orphaned_photos_removed" in result
        assert result["unused_colors_removed"] == 0
        assert result["unused_sizes_removed"] == 0
        assert result["orphaned_photos_removed"] == 0
