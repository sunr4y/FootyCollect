# ruff: noqa: E501
from django.urls import path

from .views import (
    DropzoneTestView,
    FeedView,
    ItemCreateView,
    ItemDeleteView,
    ItemDetailView,
    ItemListView,
    ItemQuickViewView,
    ItemUpdateView,
    JerseyCreateView,
    JerseyFKAPICreateView,
    JerseySelectView,
    JerseyUpdateView,
    PostCreateView,
    demo_brand_view,
    demo_country_view,
    file_upload,
    handle_dropzone_files,
    home,
    reorder_photos,
    test_dropzone,
    upload_photo,
)

# Keep original views for fallback
# Choose which views to use:
# - Use original views.py: from . import views
# - Use modular views: from .views import *
# For testing modular structure:

app_name = "collection"

urlpatterns = [
    # Home and test views
    path("", home, name="home"),
    # Feed
    path("feed/", FeedView.as_view(), name="feed"),
    path("test/country/", demo_country_view, name="test_country"),
    path("test/brand/", demo_brand_view, name="test_brand"),
    path("test/dropzone/", test_dropzone, name="test_dropzone"),
    path("test/dropzone-page/", DropzoneTestView.as_view(), name="dropzone_test_page"),
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
    path("upload/", file_upload, name="file_upload"),
    path("upload/photo/", upload_photo, name="upload_photo"),
    path("dropzone/files/", handle_dropzone_files, name="handle_dropzone_files"),
    # Post creation (legacy)
    path("post/create/", PostCreateView.as_view(), name="post_create"),
    # Fallback to original views if needed
    # path("jersey/create/details/<int:kit_id>/",
    # original_views.JerseyDetailsView.as_view(), name="jersey_details"),
]
