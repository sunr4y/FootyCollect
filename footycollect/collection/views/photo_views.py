"""
Photo-related views for the collection app.

This module contains all views that handle photo operations including
upload, download, deletion, and processing.
"""

import logging
from urllib.parse import urlparse

import requests
from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import Error as DBError
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from footycollect.collection.models import BaseItem, Photo
from footycollect.collection.services import get_photo_service

PROXY_IMAGE_MAX_SIZE = 10 * 1024 * 1024
PROXY_REFERER = "https://www.footballkitarchive.com/"

logger = logging.getLogger(__name__)


def _is_allowed_proxy_host(url: str) -> bool:
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        allowed = getattr(
            django_settings,
            "ALLOWED_EXTERNAL_IMAGE_HOSTS",
            ["cdn.footballkitarchive.com", "www.footballkitarchive.com"],
        )
        return hostname in [h.lower() for h in allowed]
    except (ValueError, AttributeError):
        return False


def _validate_proxy_url(url: str | None) -> str | None:
    """Validate proxy URL and return error message if invalid, None if valid."""
    if not url:
        return "Missing url parameter"
    if not url.startswith(("http://", "https://")):
        return "Invalid url"
    if not _is_allowed_proxy_host(url):
        return "URL host not allowed"
    return None


@login_required
@require_GET
def proxy_image(request):
    """Proxy external image with Referer so hotlink protection allows the request."""
    url = request.GET.get("url")
    validation_error = _validate_proxy_url(url)
    if validation_error:
        return HttpResponseBadRequest(validation_error)
    try:
        resp = requests.get(
            url,
            timeout=15,
            stream=True,
            headers={"Referer": PROXY_REFERER},
        )
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        if not content_type.startswith("image/"):
            return HttpResponseBadRequest("Not an image")
        size = 0
        chunks = []
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                size += len(chunk)
                if size > PROXY_IMAGE_MAX_SIZE:
                    return HttpResponseBadRequest("Image too large")
                chunks.append(chunk)
        return HttpResponse(b"".join(chunks), content_type=content_type)
    except requests.RequestException as e:
        logger.warning("Proxy image failed for %s: %s", url[:80], e)
        return HttpResponseBadRequest("Failed to fetch image")


@login_required
@require_POST
def reorder_photos(request, item_id):
    """Handle photo reordering via AJAX."""
    try:
        from footycollect.collection.models import Jersey

        # Get the item and verify ownership
        item = Jersey.objects.get(pk=item_id, base_item__user=request.user)

        photo_service = get_photo_service()
        new_order = request.POST.getlist("order[]")

        # Convert to list of tuples (photo_id, new_order)
        photo_orders = [(int(photo_id), index) for index, photo_id in enumerate(new_order)]

        photo_service.reorder_photos(item, photo_orders)
        return JsonResponse({"status": "success"})
    except (ValidationError, DBError) as e:
        logger.exception("Error reordering photos")
        return JsonResponse({"status": "error", "message": str(e)})


@login_required
@require_POST
def upload_photo(request):
    """Upload a single photo without associating it with an item yet."""
    try:
        photo_service = get_photo_service()
        file = request.FILES.get("photo")
        if not file:
            return JsonResponse({"error": _("No file received")}, status=400)

        # Use service to create photo
        photo = photo_service.create_photo_with_validation(
            file=file,
            user=request.user,
            order=request.POST.get("order", 0),
        )

        return JsonResponse(
            {
                "id": photo.id,
                "url": photo.get_image_url(),
                "thumbnail_url": photo.thumbnail.url if photo.thumbnail else None,
            },
        )

    except (ValidationError, DBError) as e:
        logger.exception("Error creating photo")
        messages.error(request, _("Error: {}").format(str(e)))
        return JsonResponse({"error": str(e)}, status=500)
    except OSError:  # For I/O errors
        logger.exception("System error")
        messages.error(request, _("System error"))
        return JsonResponse({"error": _("System error")}, status=500)


@login_required
def check_photos_status(request, item_id):
    """Check if photos for an item have AVIF versions processed."""
    try:
        from footycollect.collection.models import BaseItem

        base_item = BaseItem.objects.get(pk=item_id, user=request.user)
        photos = base_item.photos.all()

        photos_status = [
            {
                "id": photo.id,
                "has_avif": bool(photo.image_avif),
                "image_url": photo.image.url if photo.image else None,
                "avif_url": photo.image_avif.url if photo.image_avif else None,
            }
            for photo in photos
        ]

        all_processed = all(p["has_avif"] for p in photos_status)
        return JsonResponse({"photos": photos_status, "all_processed": all_processed})
    except BaseItem.DoesNotExist:
        return JsonResponse({"error": _("Item not found")}, status=404)
    except Exception as e:
        logger.exception("Error checking photos status")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def file_upload(request):
    """Handle file upload for testing purposes."""
    my_file = request.FILES.get("file")
    if not my_file:
        return JsonResponse({"error": _("No file provided")}, status=400)
    Photo.objects.create(image=my_file, user=request.user)
    return HttpResponse("")


@login_required
@require_http_methods(["POST", "DELETE"])
def handle_dropzone_files(request):
    """Handles file upload and deletion for Dropzone."""
    if request.method == "POST":
        # Create a test file without associating it with a model
        file = request.FILES.get("file")
        if not file:
            return HttpResponseBadRequest(_("No file provided"))

        # Simulate saving (in reality we don't save)
        file_data = {
            "name": file.name,
            "size": file.size,
            "url": "#",
            "deleteUrl": reverse("collection:handle_dropzone_files"),
            "deleteType": "DELETE",
        }
        return JsonResponse(file_data)

    if request.method == "DELETE":
        # Simulate deletion
        file_name = request.POST.get("fileName")
        return JsonResponse(
            {"success": True, "message": _("File {} deleted").format(file_name)},
        )

    return HttpResponseBadRequest(_("Method not allowed"))


class ItemProcessingStatusView(View):
    def get(self, request, item_id):  # noqa: C901
        try:
            base_item = BaseItem.objects.get(pk=item_id)
            if base_item.user != request.user:
                return JsonResponse({"error": "Permission denied"}, status=403)

            photos = base_item.photos.all()
            photos_with_image = [photo for photo in photos if photo.image]

            def is_photo_processed(photo):
                if not photo.image_avif:
                    return False
                try:
                    name = getattr(photo.image_avif, "name", None)
                    return bool(name and str(name).strip())
                except (ValueError, AttributeError):
                    return False

            photos_processing = [photo.id for photo in photos_with_image if not is_photo_processed(photo)]

            all_processed = (
                all(is_photo_processed(photo) for photo in photos_with_image) if photos_with_image else True
            )

            base_item.refresh_from_db()
            current_flag = base_item.is_processing_photos

            if all_processed and current_flag:
                from django.db import transaction

                with transaction.atomic():
                    base_item.is_processing_photos = False
                    base_item.save(update_fields=["is_processing_photos"])
                logger.info(
                    "Item %s: all %d photos processed, flag updated from %s to False",
                    item_id,
                    len(photos_with_image),
                    current_flag,
                )
            elif all_processed:
                logger.debug("Item %s: all photos processed but flag already False", item_id)
            else:
                logger.debug(
                    "Item %s: %d/%d photos still processing (IDs: %s)",
                    item_id,
                    len(photos_processing),
                    len(photos_with_image),
                    photos_processing,
                )
                from django.core.cache import cache

                from footycollect.collection.tasks import process_photo_to_avif

                for pid in photos_processing:
                    cache_key = f"avif_queued_photo_{pid}"
                    if not cache.get(cache_key):
                        process_photo_to_avif.delay(pid)
                        cache.set(cache_key, 1, timeout=120)
                        logger.info("Re-queued AVIF processing for photo %s (item %s)", pid, item_id)

            payload = {
                "is_processing": base_item.is_processing_photos and not all_processed,
                "has_photos": photos.exists(),
                "photo_count": photos.count(),
                "photos_processing": photos_processing,
                "all_processed": all_processed,
            }
            if request.GET.get("debug"):
                payload["_debug"] = {
                    "item_id": item_id,
                    "is_processing_photos_flag": base_item.is_processing_photos,
                    "photos_with_image_count": len(photos_with_image),
                    "photos": [
                        {
                            "id": p.id,
                            "has_image": bool(p.image),
                            "has_avif": bool(p.image_avif),
                            "avif_name": getattr(p.image_avif, "name", None) or None,
                            "processed": is_photo_processed(p),
                        }
                        for p in photos_with_image
                    ],
                }
            return JsonResponse(payload)
        except BaseItem.DoesNotExist:
            return JsonResponse({"error": "Item not found"}, status=404)
