"""
Additional tests for ItemService fit filter behaviour.
"""

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from footycollect.collection.services.item_service import ItemService

User = get_user_model()


class TestItemServiceFitFilter(TestCase):
    def setUp(self):
        self.service = ItemService()
        self.user = User.objects.create_user(
            username="fit-user",
            email="fit@example.com",
            password="testpass123",  # NOSONAR - test fixture
        )

    def test_apply_filters_ignores_empty_fit(self):
        """_apply_filters should not touch queryset when fit is falsy."""
        items = Mock()
        # Copy behaviour: other filters empty, fit falsy
        result = self.service._apply_filters(items, {"fit": ""})
        assert result is items
        items.filter.assert_not_called()

    def test_apply_filters_filters_by_fit_when_present(self):
        """_apply_filters should add fit filter when value is present."""
        items = Mock()
        filtered = Mock()
        items.filter.return_value = filtered

        result = self.service._apply_filters(items, {"fit": "TRUE_TO_SIZE"})

        items.filter.assert_called_once_with(fit="TRUE_TO_SIZE")
        assert result is filtered

