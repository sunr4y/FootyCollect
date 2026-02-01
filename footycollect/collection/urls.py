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
    mass_delete_items,
    proxy_image,
    reorder_photos,
    rotate_photos_admin,
    upload_photo,
)
from .views.admin_actions import admin_delete_item, admin_edit_item, admin_rotate_photos

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
    path("items/mass-delete/", mass_delete_items, name="mass_delete_items"),
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
    path("admin/photos/<int:item_pk>/rotate/", rotate_photos_admin, name="admin_rotate_photos"),
    path("items/<int:item_id>/processing-status/", ItemProcessingStatusView.as_view(), name="item_processing_status"),
    path("upload/", file_upload, name="file_upload"),
    path("upload/photo/", upload_photo, name="upload_photo"),
    path("dropzone/files/", handle_dropzone_files, name="handle_dropzone_files"),
    path("proxy-image/", proxy_image, name="proxy_image"),
    # Admin actions (demo mode only, staff required)
    path("admin/delete/<int:pk>/", admin_delete_item, name="admin_delete_item"),
    path("admin/rotate-photos/<int:pk>/", admin_rotate_photos, name="admin_rotate_photos"),
    path("admin/edit/<int:pk>/", admin_edit_item, name="admin_edit_item"),
]
