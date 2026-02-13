"""
Additional tests for ItemService (create_item, update_item, get_* wrappers).
Merge into test_item_service.py when convenient.
"""

from unittest.mock import Mock, patch

from django.test import TestCase

from footycollect.collection.services.item_service import ItemService

EXPECTED_ITEMS_COUNT_3 = 3


class TestItemServiceWrappers(TestCase):
    """Tests for ItemService wrapper methods and get_* delegates."""

    def setUp(self):
        self.service = ItemService()
        self.user = Mock()
        self.user.pk = 1

    def test_create_item_calls_repository(self):
        """create_item delegates to item_repository.create."""
        item_data = {"name": "Jersey", "design": "PLAIN"}
        mock_item = Mock()
        with patch.object(self.service.item_repository, "create") as mock_create:
            mock_create.return_value = mock_item
            result = self.service.create_item(self.user, item_data)
            assert result == mock_item
            mock_create.assert_called_once_with(**item_data)

    def test_update_item_calls_repository(self):
        """update_item delegates to item_repository.update."""
        mock_item = Mock()
        mock_item.pk = 42
        item_data = {"name": "Updated"}
        with patch.object(self.service.item_repository, "update") as mock_update:
            mock_update.return_value = mock_item
            result = self.service.update_item(mock_item, item_data)
            assert result == mock_item
            mock_update.assert_called_once_with(42, **item_data)

    def test_get_user_item_count(self):
        """get_user_item_count returns repository count."""
        with patch.object(self.service.item_repository, "get_user_items") as mock_get:
            mock_get.return_value.count.return_value = EXPECTED_ITEMS_COUNT_3
            result = self.service.get_user_item_count(self.user)
            assert result == EXPECTED_ITEMS_COUNT_3
            mock_get.return_value.count.assert_called_once_with()

    def test_get_public_items(self):
        """get_public_items returns repository queryset."""
        mock_qs = Mock()
        with patch.object(self.service.item_repository, "get_public_items") as mock_get:
            mock_get.return_value = mock_qs
            result = self.service.get_public_items()
            assert result == mock_qs
            mock_get.assert_called_once_with()

    def test_get_recent_items(self):
        """get_recent_items delegates to repository with limit and user."""
        mock_qs = Mock()
        with patch.object(self.service.item_repository, "get_recent_items") as mock_get:
            mock_get.return_value = mock_qs
            result = self.service.get_recent_items(limit=5, user=self.user)
            assert result == mock_qs
            mock_get.assert_called_once_with(limit=5, user=self.user)

    def test_get_user_item_count_by_type(self):
        """get_user_item_count_by_type returns repository result."""
        with patch.object(self.service.item_repository, "get_user_item_count_by_type") as mock_get:
            mock_get.return_value = {"jersey": 2, "shorts": 1}
            result = self.service.get_user_item_count_by_type(self.user)
            assert result == {"jersey": 2, "shorts": 1}
            mock_get.assert_called_once_with(self.user)

    def test_get_items_by_club_queryset(self):
        """get_items_by_club returns user items ordered by club and created_at."""
        mock_qs = Mock()
        with patch.object(self.service.item_repository, "get_user_items") as mock_get:
            mock_get.return_value.order_by.return_value = mock_qs
            result = self.service.get_items_by_club(self.user)
            assert result == mock_qs
            mock_get.return_value.order_by.assert_called_once_with("club__name", "-created_at")

    def test_get_items_by_season(self):
        """get_items_by_season returns user items ordered by season and created_at."""
        mock_qs = Mock()
        with patch.object(self.service.item_repository, "get_user_items") as mock_get:
            mock_get.return_value.order_by.return_value = mock_qs
            result = self.service.get_items_by_season(self.user)
            assert result == mock_qs
            mock_get.return_value.order_by.assert_called_once_with("season__name", "-created_at")

    def test_get_item_analytics(self):
        """get_item_analytics returns _build_collection_summary."""
        with patch.object(self.service, "_build_collection_summary") as mock_build:
            mock_build.return_value = {"total_items": 1, "by_type": {}}
            result = self.service.get_item_analytics(self.user)
            assert result == {"total_items": 1, "by_type": {}}
            mock_build.assert_called_once_with(self.user)

    def test_search_items_wrapper(self):
        """search_items delegates to search_items_advanced."""
        mock_qs = Mock()
        with patch.object(self.service, "search_items_advanced") as mock_advanced:
            mock_advanced.return_value = mock_qs
            result = self.service.search_items(self.user, "query", filters={"brand": "Nike"})
            assert result == mock_qs
            mock_advanced.assert_called_once_with(query="query", user=self.user, filters={"brand": "Nike"})
