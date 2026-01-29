# ruff: noqa: E501
from django.urls import path

from .views import (
    FeedView,
    ItemCreateView,
    ItemDeleteView,
    ItemDetailView,
    ItemListView,
    ItemProcessingStatusView,
    ItemQuickViewView,
    ItemUpdateView,
    JerseyCreateView,
    JerseyFKAPICreateView,
    JerseySelectView,
    JerseyUpdateView,
    file_upload,
    handle_dropzone_files,
    home,
    reorder_photos,
    upload_photo,
)

# Keep original views for fallback
# Choose which views to use:
# - Use original views.py: from . import views
# - Use modular views: from .views import *
# For testing modular structure:

app_name = "collection"

urlpatterns = [
    # Home
    path("", home, name="home"),
    # Feed
    path("feed/", FeedView.as_view(), name="feed"),
    # Item CRUD operations
    path("items/", ItemListView.as_view(), name="item_list"),
    path("items/<int:pk>/", ItemDetailView.as_view(), name="item_detail"),
    path("items/<int:pk>/quick-view/", ItemQuickViewView.as_view(), name="item_quick_view"),
    path("items/create/", ItemCreateView.as_view(), name="item_create"),
    path("items/<int:pk>/update/", ItemUpdateView.as_view(), name="item_update"),
    path("items/<int:pk>/delete/", ItemDeleteView.as_view(), name="item_delete"),
    # Jersey-specific views
    path("jersey/create/manual/", JerseyCreateView.as_view(), name="jersey_create_manual"),
    path("jersey/create/automatic/", JerseyFKAPICreateView.as_view(), name="jersey_create_automatic"),
    path("jersey/<int:pk>/update/", JerseyUpdateView.as_view(), name="jersey_update"),
    path("jersey/select/", JerseySelectView.as_view(), name="jersey_select"),
    # Legacy URLs for backwards compatibility
    path("jersey/create/", JerseyCreateView.as_view(), name="jersey_create"),
    path("jersey/add/", JerseyFKAPICreateView.as_view(), name="jersey_add_automatic"),
    # Photo operations
    path("items/<int:item_id>/reorder-photos/", reorder_photos, name="reorder_photos"),
    path("items/<int:item_id>/processing-status/", ItemProcessingStatusView.as_view(), name="item_processing_status"),
    path("upload/", file_upload, name="file_upload"),
    path("upload/photo/", upload_photo, name="upload_photo"),
    path("dropzone/files/", handle_dropzone_files, name="handle_dropzone_files"),
    # Fallback to original views if needed
    # path("jersey/create/details/<int:kit_id>/",
    # original_views.JerseyDetailsView.as_view(), name="jersey_details"),
]
