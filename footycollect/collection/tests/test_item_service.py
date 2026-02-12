"""
Tests for ItemService.
"""

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from footycollect.collection.services.item_service import ItemService

User = get_user_model()

# Constants for test values
TEST_PASSWORD = "testpass123"  # NOSONAR (S2068) "test fixture only, not a credential"
EXPECTED_ITEMS_COUNT_2 = 2


class TestItemService(TestCase):
    """Test cases for ItemService."""

    def setUp(self):
        """Set up test data."""
        self.service = ItemService()

        # Create test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )

    def test_service_initialization(self):
        """Test service initializes correctly."""
        assert self.service is not None
        assert self.service.item_repository is not None
        assert self.service.photo_repository is not None
        assert self.service.color_repository is not None

    def test_create_item_with_photos_success(self):
        """Test successful item creation with photos."""
        item_data = {
            "name": "Test Jersey",
            "description": "Test description",
            "main_color": "Red",
            "design": "home",
        }

        with patch.object(self.service.item_repository, "create") as mock_create:
            mock_item = Mock()
            mock_item.id = 1
            mock_create.return_value = mock_item

            result = self.service.create_item_with_photos(
                self.user,
                item_data,
                [],
            )

            assert result == mock_item
            mock_create.assert_called_once()

    def test_create_item_with_photos_with_photos(self):
        """Test item creation with photos."""
        item_data = {
            "name": "Test Jersey",
            "description": "Test description",
            "main_color": "Red",
            "design": "home",
        }

        mock_photos = [Mock(), Mock()]

        with (
            patch.object(self.service.item_repository, "create") as mock_create,
            patch.object(self.service, "_process_item_photos") as mock_process,
        ):
            mock_item = Mock()
            mock_item.id = 1
            mock_create.return_value = mock_item

            result = self.service.create_item_with_photos(
                self.user,
                item_data,
                mock_photos,
            )

            assert result == mock_item
            mock_create.assert_called_once()
            mock_process.assert_called_once_with(mock_item, mock_photos)

    def test_update_item_with_photos_success(self):
        """Test successful item update with photos."""
        item_data = {
            "name": "Updated Jersey",
            "description": "Updated description",
        }

        with patch.object(self.service.item_repository, "update") as mock_update:
            mock_item = Mock()
            mock_item.id = 1
            mock_update.return_value = mock_item

            result = self.service.update_item_with_photos(1, item_data, [])

            assert result == mock_item
            mock_update.assert_called_once_with(1, **item_data)

    def test_update_item_with_photos_not_found(self):
        """Test item update when item not found."""
        item_data = {"name": "Updated Jersey"}

        with patch.object(self.service.item_repository, "update") as mock_update:
            mock_update.return_value = None

            result = self.service.update_item_with_photos(1, item_data, [])

            assert result is None
            mock_update.assert_called_once_with(1, **item_data)

    def test_update_item_with_photos_calls_process_photos_when_photos_provided(self):
        """Test update_item_with_photos calls _process_item_photos when photos list is non-empty."""
        item_data = {"name": "Updated"}
        mock_photos = [Mock()]

        with (
            patch.object(self.service.item_repository, "update") as mock_update,
            patch.object(self.service, "_process_item_photos") as mock_process,
        ):
            mock_item = Mock()
            mock_item.id = 1
            mock_update.return_value = mock_item

            result = self.service.update_item_with_photos(1, item_data, mock_photos)

            assert result == mock_item
            mock_update.assert_called_once_with(1, **item_data)
            mock_process.assert_called_once_with(mock_item, mock_photos)

    def test_delete_item_with_photos_success(self):
        """Test successful item deletion with photos."""
        with (
            patch.object(self.service.item_repository, "get_by_id") as mock_get,
            patch.object(self.service.photo_repository, "delete_photos_by_item") as mock_delete_photos,
            patch.object(self.service.item_repository, "delete") as mock_delete,
        ):
            mock_item = Mock()
            mock_get.return_value = mock_item
            mock_delete.return_value = True

            result = self.service.delete_item_with_photos(1)

            assert result is True
            mock_get.assert_called_once_with(1)
            mock_delete_photos.assert_called_once_with(mock_item)
            mock_delete.assert_called_once_with(1)

    def test_delete_item_with_photos_not_found(self):
        """Test item deletion when item not found."""
        with patch.object(self.service.item_repository, "get_by_id") as mock_get:
            mock_get.return_value = None

            result = self.service.delete_item_with_photos(1)

            assert result is False
            mock_get.assert_called_once_with(1)

    def test_get_user_items(self):
        """Test getting items for user."""
        with patch.object(self.service.item_repository, "get_user_items") as mock_get:
            mock_queryset = Mock()
            mock_get.return_value = mock_queryset

            result = self.service.get_user_items(self.user)

            assert result == mock_queryset
            mock_get.assert_called_once_with(self.user)

    def test_get_user_collection_summary(self):
        """Test getting user collection summary."""
        with (
            patch.object(self.service.item_repository, "get_user_items") as mock_get_items,
            patch.object(self.service.item_repository, "get_user_item_count_by_type") as mock_get_by_type,
            patch.object(self.service.item_repository, "get_recent_items") as mock_get_recent,
            patch.object(self.service, "_get_items_by_condition") as mock_condition,
            patch.object(self.service, "_get_items_by_brand") as mock_brand,
            patch.object(self.service, "_get_items_by_club") as mock_club,
        ):
            mock_items = Mock()
            mock_items.count.return_value = 10
            mock_get_items.return_value = mock_items
            mock_get_by_type.return_value = {"jersey": 5, "shorts": 3}
            mock_get_recent.return_value = []
            mock_condition.return_value = {"new": 5, "used": 5}
            mock_brand.return_value = {"Nike": 3, "Adidas": 2}
            mock_club.return_value = {"Barcelona": 2, "Real Madrid": 1}

            result = self.service.get_user_collection_summary(self.user)

            assert "total_items" in result
            assert "by_type" in result
            assert "by_condition" in result
            assert "by_brand" in result
            assert "by_club" in result
            assert "recent_items" in result

    def test_search_items_advanced_with_user(self):
        """Test advanced search with user."""
        with (
            patch.object(self.service.item_repository, "get_user_items") as mock_get_user,
            patch.object(self.service.item_repository, "search_items") as mock_search,
            patch.object(self.service, "_apply_filters") as mock_apply,
        ):
            mock_queryset = Mock()
            mock_get_user.return_value = mock_queryset
            mock_search.return_value = mock_queryset
            mock_apply.return_value = mock_queryset

            result = self.service.search_items_advanced("jersey", self.user, {"brand": "Nike"})

            assert result == mock_queryset
            mock_get_user.assert_called_once_with(self.user)
            mock_search.assert_called_once_with("jersey", self.user)
            mock_apply.assert_called_once_with(mock_queryset, {"brand": "Nike"})

    def test_search_items_advanced_without_user(self):
        """Test advanced search without user."""
        with (
            patch.object(self.service.item_repository, "get_public_items") as mock_get_public,
            patch.object(self.service.item_repository, "search_items") as mock_search,
            patch.object(self.service, "_apply_filters") as mock_apply,
        ):
            mock_queryset = Mock()
            mock_get_public.return_value = mock_queryset
            mock_search.return_value = mock_queryset
            mock_apply.return_value = mock_queryset

            result = self.service.search_items_advanced("jersey", None, {"brand": "Nike"})

            assert result == mock_queryset
            mock_get_public.assert_called_once()
            mock_search.assert_called_once_with("jersey", None)
            mock_apply.assert_called_once_with(mock_queryset, {"brand": "Nike"})

    def test_reorder_item_photos_success(self):
        """Test successful photo reordering."""
        with (
            patch.object(self.service.item_repository, "get_by_id") as mock_get,
            patch.object(self.service.photo_repository, "reorder_photos") as mock_reorder,
        ):
            mock_item = Mock()
            mock_get.return_value = mock_item
            mock_reorder.return_value = True

            result = self.service.reorder_item_photos(1, [(1, 0), (2, 1)])

            assert result is True
            mock_get.assert_called_once_with(1)
            mock_reorder.assert_called_once_with(mock_item, [(1, 0), (2, 1)])

    def test_reorder_item_photos_item_not_found(self):
        """Test photo reordering when item not found."""
        with patch.object(self.service.item_repository, "get_by_id") as mock_get:
            mock_get.return_value = None

            result = self.service.reorder_item_photos(1, [(1, 0), (2, 1)])

            assert result is False
            mock_get.assert_called_once_with(1)

    def test_get_item_with_photos_success(self):
        """Test getting item with photos."""
        with (
            patch.object(self.service.item_repository, "get_by_id") as mock_get,
            patch.object(self.service.photo_repository, "get_photos_by_item") as mock_get_photos,
        ):
            mock_item = Mock()
            mock_photos = [Mock(), Mock()]
            mock_get.return_value = mock_item
            mock_get_photos.return_value = mock_photos

            result = self.service.get_item_with_photos(1)

            assert result == mock_item
            assert result.photos_list == mock_photos
            mock_get.assert_called_once_with(1)
            mock_get_photos.assert_called_once_with(mock_item)

    def test_get_item_with_photos_not_found(self):
        """Test getting item with photos when item not found."""
        with patch.object(self.service.item_repository, "get_by_id") as mock_get:
            mock_get.return_value = None

            result = self.service.get_item_with_photos(1)

            assert result is None
            mock_get.assert_called_once_with(1)

    def test_process_item_photos(self):
        """Test processing item photos."""
        mock_item = Mock()
        mock_item.user = self.user
        mock_photos = [Mock(), Mock()]

        with patch.object(self.service.photo_repository, "create") as mock_create:
            self.service._process_item_photos(mock_item, mock_photos)

            assert mock_create.call_count == EXPECTED_ITEMS_COUNT_2
            mock_create.assert_any_call(
                image=mock_photos[0],
                content_object=mock_item,
                order=0,
                uploaded_by=self.user,
            )
            mock_create.assert_any_call(
                image=mock_photos[1],
                content_object=mock_item,
                order=1,
                uploaded_by=self.user,
            )

    def test_apply_filters(self):
        """Test applying filters to items."""
        mock_items = Mock()

        filters = {
            "brand": "Nike",
            "club": "Barcelona",
            "condition": "new",
            "is_draft": False,
            "is_private": True,
        }

        self.service._apply_filters(mock_items, filters)

        # Verify filter calls were made
        mock_items.filter.assert_called()

    def test_get_items_by_condition(self):
        """Test getting items by condition."""
        mock_items = Mock()
        mock_items.values.return_value.annotate.return_value.values_list.return_value = [("new", 5), ("used", 3)]

        result = self.service._get_items_by_condition(mock_items)

        assert result == {"new": 5, "used": 3}

    def test_get_items_by_brand(self):
        """Test getting items by brand."""
        mock_items = Mock()
        mock_items.values.return_value.annotate.return_value.values_list.return_value = [
            ("Nike", 3),
            ("Adidas", 2),
        ]

        result = self.service._get_items_by_brand(mock_items)

        assert result == {"Nike": 3, "Adidas": 2}

    def test_get_items_by_club(self):
        """Test getting items by club."""
        mock_items = Mock()
        mock_items.values.return_value.annotate.return_value.values_list.return_value = [
            ("Barcelona", 2),
            ("Real Madrid", 1),
        ]

        result = self.service._get_items_by_club(mock_items)

        assert result == {"Barcelona": 2, "Real Madrid": 1}
