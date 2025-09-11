"""
Repository layer for the collection app.

This module contains repository classes that abstract data access
and provide a clean interface for database operations.
"""

from .base_repository import BaseRepository
from .item_repository import ItemRepository

__all__ = [
    "BaseRepository",
    "ItemRepository",
]
