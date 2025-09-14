"""
Repository layer for the collection app.

This module contains repository classes that abstract data access
and provide a clean interface for database operations.
"""

from .base_repository import BaseRepository
from .color_repository import ColorRepository
from .item_repository import ItemRepository
from .photo_repository import PhotoRepository
from .size_repository import SizeRepository

__all__ = [
    "BaseRepository",
    "ColorRepository",
    "ItemRepository",
    "PhotoRepository",
    "SizeRepository",
]
