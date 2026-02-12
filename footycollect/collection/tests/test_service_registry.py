"""Tests for service_registry."""

from unittest.mock import patch

import pytest
from django.test import TestCase

from footycollect.collection.services import service_registry
from footycollect.collection.services.service_registry import (
    get_collection_service,
    get_color_service,
    get_item_service,
    get_photo_service,
    get_service,
    get_size_service,
)


class TestServiceRegistry(TestCase):
    def test_get_service_raises_key_error_when_not_registered(self):
        with patch.object(service_registry, "_services", {}):
            with pytest.raises(KeyError) as exc_info:
                get_service("item_service")
            assert "item_service" in str(exc_info.value)

    def test_get_collection_service_returns_collection_service(self):
        from footycollect.collection.services.collection_service import CollectionService

        assert isinstance(get_collection_service(), CollectionService)

    def test_get_item_service_returns_item_service(self):
        from footycollect.collection.services.item_service import ItemService

        assert isinstance(get_item_service(), ItemService)

    def test_get_photo_service_returns_photo_service(self):
        from footycollect.collection.services.photo_service import PhotoService

        assert isinstance(get_photo_service(), PhotoService)

    def test_get_color_service_returns_color_service(self):
        from footycollect.collection.services.color_service import ColorService

        assert isinstance(get_color_service(), ColorService)

    def test_get_size_service_returns_size_service(self):
        from footycollect.collection.services.size_service import SizeService

        assert isinstance(get_size_service(), SizeService)

    def test_clear_services(self):
        service_registry.clear_services()
        self.addCleanup(service_registry.initialize_default_services)
        with pytest.raises(KeyError):
            get_service("item_service")
