"""
Collection views package.

This package contains all the views for the collection app, organized by functionality.
"""

# Import all views explicitly to avoid import issues
from .crud_views import ItemCreateView, ItemDeleteView, ItemUpdateView
from .demo_views import home
from .detail_views import ItemDetailView, ItemQuickViewView
from .feed_views import FeedView
from .item_views import JerseyCreateView, JerseySelectView, JerseyUpdateView
from .jersey_views import JerseyFKAPICreateView
from .list_views import ItemListView
from .photo_views import (
    ItemProcessingStatusView,
    PhotoProcessorMixin,
    file_upload,
    handle_dropzone_files,
    reorder_photos,  # Photo views
    upload_photo,
)

__all__ = [
    # Feed views
    "FeedView",
    # Item views
    "ItemListView",
    "ItemDetailView",
    "ItemQuickViewView",
    "ItemCreateView",
    "ItemUpdateView",
    "ItemDeleteView",
    "JerseyCreateView",
    "JerseyUpdateView",
    "JerseySelectView",
    "JerseyFKAPICreateView",
    # Photo views
    "ItemProcessingStatusView",
    "reorder_photos",
    "upload_photo",
    "file_upload",
    "handle_dropzone_files",
    "PhotoProcessorMixin",
    # Demo views
    "home",
]
