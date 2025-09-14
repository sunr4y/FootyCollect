"""
Service registry for dependency injection.

This module provides a service registry that allows for dependency injection
and makes services easily testable by allowing mock implementations.
"""

from typing import Any, Optional

from footycollect.collection.services.collection_service import CollectionService
from footycollect.collection.services.color_service import ColorService
from footycollect.collection.services.item_service import ItemService
from footycollect.collection.services.photo_service import PhotoService
from footycollect.collection.services.size_service import SizeService


class ServiceRegistry:
    """
    Registry for managing service instances and dependencies.

    This registry allows for dependency injection and makes services
    easily testable by allowing mock implementations.
    """

    _instance: Optional["ServiceRegistry"] = None
    _services: dict[str, Any] = {}

    def __new__(cls) -> "ServiceRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register_service(self, name: str, service_instance: Any) -> None:
        """
        Register a service instance.

        Args:
            name: Service name
            service_instance: Service instance
        """
        self._services[name] = service_instance

    def get_service(self, name: str) -> Any:
        """
        Get a service instance.

        Args:
            name: Service name

        Returns:
            Service instance

        Raises:
            KeyError: If service is not registered
        """
        if name not in self._services:
            error_msg = f"Service '{name}' not registered"
            raise KeyError(error_msg)
        return self._services[name]

    def get_collection_service(self) -> CollectionService:
        """Get the collection service instance."""
        return self.get_service("collection_service")

    def get_item_service(self) -> ItemService:
        """Get the item service instance."""
        return self.get_service("item_service")

    def get_photo_service(self) -> PhotoService:
        """Get the photo service instance."""
        return self.get_service("photo_service")

    def get_color_service(self) -> ColorService:
        """Get the color service instance."""
        return self.get_service("color_service")

    def get_size_service(self) -> SizeService:
        """Get the size service instance."""
        return self.get_service("size_service")

    def initialize_default_services(self) -> None:
        """Initialize all default services."""
        self.register_service("item_service", ItemService())
        self.register_service("photo_service", PhotoService())
        self.register_service("color_service", ColorService())
        self.register_service("size_service", SizeService())
        self.register_service("collection_service", CollectionService())

    def clear_services(self) -> None:
        """Clear all registered services."""
        self._services.clear()


# Global service registry instance
service_registry = ServiceRegistry()

# Initialize default services
service_registry.initialize_default_services()


def get_service(service_name: str) -> Any:
    """
    Get a service from the global registry.

    Args:
        service_name: Name of the service to retrieve

    Returns:
        Service instance
    """
    return service_registry.get_service(service_name)


def get_collection_service() -> CollectionService:
    """Get the collection service from the global registry."""
    return service_registry.get_collection_service()


def get_item_service() -> ItemService:
    """Get the item service from the global registry."""
    return service_registry.get_item_service()


def get_photo_service() -> PhotoService:
    """Get the photo service from the global registry."""
    return service_registry.get_photo_service()


def get_color_service() -> ColorService:
    """Get the color service from the global registry."""
    return service_registry.get_color_service()


def get_size_service() -> SizeService:
    """Get the size service from the global registry."""
    return service_registry.get_size_service()
