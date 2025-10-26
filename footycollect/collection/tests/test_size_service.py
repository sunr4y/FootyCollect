"""
Tests for SizeService.
"""

from unittest.mock import Mock, patch

import pytest
from django.test import TestCase

from footycollect.collection.models import Size
from footycollect.collection.services.size_service import SizeService

# Constants for test values
EXPECTED_SIZES_COUNT_4 = 4
EXPECTED_SIZES_COUNT_6 = 6
EXPECTED_SIZES_COUNT_8 = 8


class TestSizeService(TestCase):
    """Test cases for SizeService."""

    def setUp(self):
        """Set up test data."""
        self.service = SizeService()

        # Create test sizes with unique names to avoid conflicts
        self.small_size = Size.objects.create(name="S", category="tops")
        self.medium_size = Size.objects.create(name="M", category="tops")
        self.large_size = Size.objects.create(name="L", category="tops")
        self.xl_size = Size.objects.create(name="XL", category="tops")

        # Create bottoms sizes with different names
        self.bottoms_28 = Size.objects.create(name="28", category="bottoms")
        self.bottoms_30 = Size.objects.create(name="30", category="bottoms")

    def test_service_integration_with_repository(self):
        """Test service integration with size repository."""
        # Test that service can retrieve sizes by category through repository
        tops_sizes = self.service.get_sizes_by_category("tops")

        assert tops_sizes is not None
        assert hasattr(tops_sizes, "count")
        assert tops_sizes.count() == EXPECTED_SIZES_COUNT_4

        # Test that sizes are the ones we created
        size_names = [size.name for size in tops_sizes]
        assert "S" in size_names
        assert "M" in size_names
        assert "L" in size_names
        assert "XL" in size_names

        # Test bottoms category
        bottoms_sizes = self.service.get_sizes_by_category("bottoms")
        assert bottoms_sizes is not None
        assert bottoms_sizes.count() == 2  # noqa: PLR2004

        bottoms_names = [size.name for size in bottoms_sizes]
        assert "28" in bottoms_names
        assert "30" in bottoms_names

    def test_get_sizes_for_item_form(self):
        """Test getting sizes for item form."""
        sizes = self.service.get_sizes_for_item_form()

        assert isinstance(sizes, dict)
        assert "tops" in sizes
        assert "bottoms" in sizes
        assert "accessories" in sizes

        # Check structure
        for size_list in sizes.values():
            assert isinstance(size_list, list)
            for size_data in size_list:
                assert "id" in size_data
                assert "name" in size_data
                assert "category" in size_data

    def test_get_sizes_by_category(self):
        """Test getting sizes by category."""
        sizes = self.service.get_sizes_by_category("tops")

        assert sizes is not None
        assert hasattr(sizes, "count")
        assert sizes.count() >= EXPECTED_SIZES_COUNT_4  # At least our test sizes

    def test_create_custom_size_success(self):
        """Test successful custom size creation."""
        size = self.service.create_custom_size("XXL", "tops")

        assert size is not None
        assert size.name == "XXL"
        assert size.category == "tops"

    def test_create_custom_size_invalid_category(self):
        """Test custom size creation with invalid category."""
        with pytest.raises(ValueError, match="Invalid category"):
            self.service.create_custom_size("XXL", "invalid")

    def test_get_sizes_for_api(self):
        """Test getting sizes for API."""
        sizes = self.service.get_sizes_for_api()

        assert isinstance(sizes, list)
        assert len(sizes) >= EXPECTED_SIZES_COUNT_6  # At least our test sizes

        # Check structure
        for size_data in sizes:
            assert "id" in size_data
            assert "name" in size_data
            assert "category" in size_data

    def test_get_size_statistics(self):
        """Test getting size statistics."""
        with patch.object(self.service.size_repository, "get_size_statistics") as mock_stats:
            mock_stats.return_value = {"total_sizes": EXPECTED_SIZES_COUNT_6}

            stats = self.service.get_size_statistics()

            assert stats == {"total_sizes": EXPECTED_SIZES_COUNT_6}
            mock_stats.assert_called_once()

    def test_get_popular_sizes(self):
        """Test getting popular sizes."""
        with patch.object(self.service.size_repository, "get_popular_sizes") as mock_popular:
            mock_popular.return_value = Mock()

            popular_sizes = self.service.get_popular_sizes(limit=5)

            assert popular_sizes is not None
            mock_popular.assert_called_once_with(5)

    def test_get_sizes_used_in_collection(self):
        """Test getting sizes used in collection."""
        with patch.object(self.service.size_repository, "get_sizes_used_in_items") as mock_used:
            mock_used.return_value = Mock()

            used_sizes = self.service.get_sizes_used_in_collection()

            assert used_sizes is not None
            mock_used.assert_called_once()

    def test_get_size_usage_analytics(self):
        """Test getting size usage analytics."""
        with (
            patch.object(self.service, "get_size_statistics") as mock_stats,
            patch.object(self.service.size_repository, "count") as mock_count,
            patch.object(self.service, "get_sizes_used_in_collection") as mock_used,
        ):
            mock_stats.return_value = {"total_sizes": EXPECTED_SIZES_COUNT_6}
            mock_count.return_value = EXPECTED_SIZES_COUNT_6
            mock_used.return_value.count.return_value = 4

            analytics = self.service.get_size_usage_analytics()

            assert isinstance(analytics, dict)
            assert "total_sizes" in analytics
            assert "used_sizes" in analytics
            assert "unused_sizes" in analytics
            assert "usage_percentage" in analytics

    def test_initialize_default_sizes(self):
        """Test initializing default sizes."""
        with patch.object(self.service.size_repository, "create_default_sizes") as mock_create:
            mock_create.return_value = 8

            result = self.service.initialize_default_sizes()

            assert result == EXPECTED_SIZES_COUNT_8
            mock_create.assert_called_once()

    def test_is_valid_category_valid(self):
        """Test category validation with valid categories."""
        assert self.service._is_valid_category("tops") is True
        assert self.service._is_valid_category("bottoms") is True
        assert self.service._is_valid_category("accessories") is True
        assert self.service._is_valid_category("TOPS") is True  # Case insensitive

    def test_is_valid_category_invalid(self):
        """Test category validation with invalid categories."""
        assert self.service._is_valid_category("invalid") is False
        assert self.service._is_valid_category("") is False
        assert self.service._is_valid_category("shoes") is False
