"""
Tests for CollectionService.
"""

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from footycollect.collection.services.collection_service import CollectionService

User = get_user_model()

# Constants for test values
TEST_PASSWORD = "testpass123"  # NOSONAR (S2068) "test fixture only, not a credential"
EXPECTED_ITEMS_COUNT_10 = 10
EXPECTED_ITEMS_COUNT_8 = 8
EXPECTED_ITEMS_COUNT_25 = 25
EXPECTED_ITEMS_COUNT_100 = 100
EXPECTED_ITEMS_COUNT_2 = 2
EXPECTED_ITEMS_COUNT_3 = 3
EXPECTED_ITEMS_COUNT_4 = 4


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

    def test_get_collection_dashboard_data(self):
        """Test getting collection dashboard data."""
        with (
            patch.object(self.service.item_service, "get_user_item_count") as mock_item_count,
            patch.object(self.service.item_service, "get_public_items") as mock_public_items,
            patch.object(self.service.item_service, "get_recent_items") as mock_recent_items,
            patch.object(self.service.color_service, "get_color_statistics") as mock_color_stats,
            patch.object(self.service.size_service, "get_size_statistics") as mock_size_stats,
            patch.object(self.service.color_service, "get_popular_colors") as mock_popular_colors,
            patch.object(self.service.size_service, "get_popular_sizes") as mock_popular_sizes,
        ):
            mock_item_count.return_value = EXPECTED_ITEMS_COUNT_10
            mock_public_items.return_value.count.return_value = EXPECTED_ITEMS_COUNT_8
            mock_recent_items.return_value.to_numpy.return_value = [{"id": 1}, {"id": 2}]
            mock_color_stats.return_value = {"total_colors": EXPECTED_ITEMS_COUNT_10}
            mock_size_stats.return_value = {"total_sizes": EXPECTED_ITEMS_COUNT_8}
            mock_popular_colors.return_value.to_numpy.return_value = [{"name": "Red"}]
            mock_popular_sizes.return_value.to_numpy.return_value = [{"name": "M"}]

            result = self.service.get_collection_dashboard_data(self.user)

            assert result["total_items"] == EXPECTED_ITEMS_COUNT_10
            assert result["public_items"] == EXPECTED_ITEMS_COUNT_8
            assert isinstance(result["recent_items"], list)
            assert result["color_stats"] == {"total_colors": EXPECTED_ITEMS_COUNT_10}
            assert result["size_stats"] == {"total_sizes": EXPECTED_ITEMS_COUNT_8}
            assert isinstance(result["popular_colors"], list)
            assert isinstance(result["popular_sizes"], list)

    def test_get_collection_analytics(self):
        """Test getting collection analytics."""
        with (
            patch.object(self.service.item_service, "get_item_analytics") as mock_item_analytics,
            patch.object(self.service.color_service, "get_color_usage_analytics") as mock_color_analytics,
            patch.object(self.service.size_service, "get_size_usage_analytics") as mock_size_analytics,
            patch.object(self.service.photo_service, "get_photo_analytics") as mock_photo_analytics,
        ):
            mock_item_analytics.return_value = {"items": EXPECTED_ITEMS_COUNT_25}
            mock_color_analytics.return_value = {"colors": EXPECTED_ITEMS_COUNT_10}
            mock_size_analytics.return_value = {"sizes": EXPECTED_ITEMS_COUNT_8}
            mock_photo_analytics.return_value = {"photos": EXPECTED_ITEMS_COUNT_100}

            result = self.service.get_collection_analytics(self.user)

            assert result["item_analytics"]["items"] == EXPECTED_ITEMS_COUNT_25
            assert result["color_analytics"]["colors"] == EXPECTED_ITEMS_COUNT_10
            assert result["size_analytics"]["sizes"] == EXPECTED_ITEMS_COUNT_8
            assert result["photo_analytics"]["photos"] == EXPECTED_ITEMS_COUNT_100

    def test_search_collection(self):
        """Test searching across the collection."""
        with (
            patch.object(self.service.item_service, "search_items") as mock_search_items,
            patch.object(self.service.color_service, "search_colors") as mock_search_colors,
            patch.object(self.service.size_service, "search_sizes") as mock_search_sizes,
        ):
            mock_search_items.return_value = [{"id": 1}]
            mock_search_colors.return_value = [{"id": 2}]
            mock_search_sizes.return_value = [{"id": 3}]

            result = self.service.search_collection(self.user, "query", {"key": "value"})

            assert len(result["items"]) == 1
            assert len(result["colors"]) == 1
            assert len(result["sizes"]) == 1
            assert result["total_results"] == EXPECTED_ITEMS_COUNT_3

    def test_create_item_with_photos(self):
        """Test creating item with photos through facade."""
        photo_files = ["photo1", "photo2"]

        with (
            patch.object(self.service.item_service, "create_item") as mock_create_item,
            patch.object(self.service.photo_service, "create_photo") as mock_create_photo,
        ):
            mock_item = Mock()
            mock_create_item.return_value = mock_item

            result = self.service.create_item_with_photos(self.user, {"name": "Item"}, photo_files)

            assert result == mock_item
            mock_create_item.assert_called_once_with(self.user, {"name": "Item"})
            assert mock_create_photo.call_count == len(photo_files)

    def test_create_item_with_photos_without_photos(self):
        """Test creating item without photos through facade."""
        with (
            patch.object(self.service.item_service, "create_item") as mock_create_item,
            patch.object(self.service.photo_service, "create_photo") as mock_create_photo,
        ):
            mock_item = Mock()
            mock_create_item.return_value = mock_item

            result = self.service.create_item_with_photos(self.user, {"name": "Item"}, None)

            assert result == mock_item
            mock_create_item.assert_called_once_with(self.user, {"name": "Item"})
            mock_create_photo.assert_not_called()

    def test_update_item_with_photos(self):
        """Test updating item and managing photos through facade."""
        mock_item = Mock()

        with (
            patch.object(self.service.item_service, "update_item") as mock_update_item,
            patch.object(self.service.photo_service, "delete_photo") as mock_delete_photo,
            patch.object(self.service.photo_service, "create_photo") as mock_create_photo,
        ):
            mock_update_item.return_value = mock_item

            result = self.service.update_item_with_photos(
                mock_item,
                {"name": "Updated"},
                photo_files=["file1"],
                remove_photo_ids=[1, 2],
            )

            assert result == mock_item
            mock_update_item.assert_called_once_with(mock_item, {"name": "Updated"})
            assert mock_delete_photo.call_count == EXPECTED_ITEMS_COUNT_2
            mock_create_photo.assert_called_once_with(mock_item, "file1")

    def test_get_user_collection_summary(self):
        """Test getting user collection summary through facade."""
        with (
            patch.object(self.service.item_service, "get_user_items") as mock_get_user_items,
            patch.object(self.service.item_service, "get_user_item_count_by_type") as mock_get_by_type,
            patch.object(self.service.item_service, "get_items_by_club") as mock_get_by_club,
            patch.object(self.service.item_service, "get_items_by_season") as mock_get_by_season,
            patch.object(self.service.item_service, "get_recent_items") as mock_get_recent,
        ):
            mock_items = Mock()
            mock_items.count.return_value = EXPECTED_ITEMS_COUNT_25
            mock_get_user_items.return_value = mock_items
            mock_get_by_type.return_value = {"jersey": 20, "shorts": 5}
            mock_get_by_club.return_value.count.return_value = 3
            mock_get_by_season.return_value.count.return_value = 4
            mock_get_recent.return_value.to_numpy.return_value = [{"id": 1}, {"id": 2}]

            summary = self.service.get_user_collection_summary(self.user)

            assert summary["total_items"] == EXPECTED_ITEMS_COUNT_25
            assert summary["by_type"] == {"jersey": 20, "shorts": 5}
            assert summary["by_club"] == EXPECTED_ITEMS_COUNT_3
            assert summary["by_season"] == EXPECTED_ITEMS_COUNT_4
            assert isinstance(summary["recent_additions"], list)
