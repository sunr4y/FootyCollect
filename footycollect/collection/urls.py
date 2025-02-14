from django.urls import path

from . import views

app_name = "collection"

urlpatterns = [
    path("items/create/", views.ItemCreateView.as_view(), name="item_create"),
    path("test-country/", views.test_country_view, name="test_country"),
    path("test-brand/", views.test_brand_view, name="test_brand"),
    path(
        "items/<int:item_id>/reorder-photos/",
        views.reorder_photos,
        name="reorder_photos",
    ),
    path("items/<int:pk>/", views.ItemDetailView.as_view(), name="item_detail"),
    path("upload/", views.file_upload, name="file_upload"),
    path("test-dropzone/", views.DropzoneTestView.as_view(), name="test_dropzone"),
    path(
        "handle-dropzone-files/",
        views.handle_dropzone_files,
        name="handle_dropzone_files",
    ),
    path("upload-photo/", views.upload_photo, name="upload_photo"),
]
