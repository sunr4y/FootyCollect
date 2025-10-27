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
    demo_brand_view,
    demo_country_view,  # Demo views
    home,
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
    # Demo views
    "demo_country_view",
    "demo_brand_view",
    "home",
    "test_dropzone",
]
