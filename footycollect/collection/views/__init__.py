"""
Collection views package.

This package contains all the views for the collection app, organized by functionality.
"""

# Import all views explicitly to avoid import issues
from .crud_views import ItemCreateView, ItemDeleteView, ItemUpdateView
from .demo_views import home
from .detail_views import ItemDetailView, ItemQuickViewView
from .feed_views import FeedView
from .item_views import JerseySelectView
from .jersey_crud_views import JerseyCreateView, JerseyUpdateView
from .jersey_views import JerseyFKAPICreateView
from .list_views import ItemListView
from .photo_processor_mixin import PhotoProcessorMixin
from .photo_views import (
    ItemProcessingStatusView,
    file_upload,
    handle_dropzone_files,
    proxy_image,
    reorder_photos,
    upload_photo,
)

__all__ = [
    "FeedView",
    "ItemCreateView",
    "ItemDeleteView",
    "ItemDetailView",
    "ItemListView",
    "ItemProcessingStatusView",
    "ItemQuickViewView",
    "ItemUpdateView",
    "JerseyCreateView",
    "JerseyFKAPICreateView",
    "JerseySelectView",
    "JerseyUpdateView",
    "PhotoProcessorMixin",
    "file_upload",
    "handle_dropzone_files",
    "home",
    "proxy_image",
    "reorder_photos",
    "upload_photo",
]
