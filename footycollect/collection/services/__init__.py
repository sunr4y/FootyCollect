"""
Service layer for the collection app.

This module contains service classes that implement business logic
and orchestrate operations between repositories and other components.
"""

from .collection_service import CollectionService
from .color_service import ColorService
from .form_service import FormService
from .item_fkapi_service import ItemFKAPIService
from .item_service import ItemService
from .photo_service import PhotoService
from .service_registry import (
    ServiceRegistry,
    get_collection_service,
    get_color_service,
    get_item_service,
    get_photo_service,
    get_service,
    get_size_service,
    service_registry,
)
from .size_service import SizeService

__all__ = [
    "CollectionService",
    "ColorService",
    "FormService",
    "ItemFKAPIService",
    "ItemService",
    "PhotoService",
    "ServiceRegistry",
    "SizeService",
    "get_collection_service",
    "get_color_service",
    "get_item_service",
    "get_photo_service",
    "get_service",
    "get_size_service",
    "service_registry",
]
