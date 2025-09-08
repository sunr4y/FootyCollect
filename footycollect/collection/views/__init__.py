"""
Collection views package.

This package contains all the views for the collection app, organized by functionality.
"""

# Import all views explicitly to avoid import issues
from .item_views import (
    DropzoneTestView,
    ItemCreateView,
    ItemDeleteView,
    ItemDetailView,
    ItemListView,  # Item views
    ItemUpdateView,
    JerseyCreateView,
    JerseySelectView,
    JerseyUpdateView,
    PostCreateView,
    home,
    test_brand_view,
    test_country_view,  # Test views
    test_dropzone,
)
from .jersey_views import JerseyFKAPICreateView
from .photo_views import (
    PhotoProcessorMixin,
    file_upload,
    handle_dropzone_files,
    reorder_photos,  # Photo views
    upload_photo,
)

__all__ = [
    # Item views
    "ItemListView",
    "ItemDetailView",
    "ItemCreateView",
    "ItemUpdateView",
    "ItemDeleteView",
    "JerseyCreateView",
    "JerseyUpdateView",
    "PostCreateView",
    "DropzoneTestView",
    "JerseySelectView",
    "JerseyFKAPICreateView",
    # Photo views
    "reorder_photos",
    "upload_photo",
    "file_upload",
    "handle_dropzone_files",
    "PhotoProcessorMixin",
    # Test views
    "test_country_view",
    "test_brand_view",
    "home",
    "test_dropzone",
]
