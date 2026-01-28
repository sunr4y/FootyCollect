"""
Photo-related views for the collection app.

This module contains all views that handle photo operations including
upload, download, deletion, and processing.
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import Error as DBError
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.http import require_http_methods, require_POST

from footycollect.collection.models import BaseItem, Photo
from footycollect.collection.services import get_photo_service
from footycollect.collection.tasks import download_external_image_and_attach

logger = logging.getLogger(__name__)


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


class PhotoProcessorMixin:
    """Mixin that provides photo processing functionality with lazy loading."""

    def __init__(self, *args, **kwargs):
        """Initialize the mixin with lazy loading."""
        super().__init__(*args, **kwargs)
        # Ensure the attribute exists
        if not hasattr(self, "_photo_processor_initialized"):
            self._photo_processor_initialized = False

    def _ensure_photo_processor_initialized(self):
        """Lazy initialization of photo processor components."""
        if not hasattr(self, "_photo_processor_initialized"):
            self._photo_processor_initialized = False

        if not self._photo_processor_initialized:
            # Only initialize when actually needed
            self._photo_processor_initialized = True
            logger.debug("PhotoProcessorMixin initialized for %s", self.__class__.__name__)

    def _download_and_attach_image(self, instance, image_url, order=None):
        self._ensure_photo_processor_initialized()

        try:
            app_label = instance._meta.app_label
            model_name = instance._meta.model_name
            download_external_image_and_attach.delay(
                app_label,
                model_name,
                instance.pk,
                image_url,
                order,
            )
        except Exception:
            logger.exception("Error queuing download task for image %s", image_url)

    def _process_photo_ids(self, photo_ids, start_order=0):
        """
        Process photo IDs uploaded through the dropzone.
        Associates existing photos with the jersey.
        photo_ids: String with JSON of photos or comma-separated IDs
        start_order: Starting order for local photos (after external images)
        """
        try:
            # Parse the photo_ids
            parsed_data = self._parse_photo_ids(photo_ids)
            if not parsed_data:
                return

            photo_id_list, external_images, order_map = parsed_data

            logger.info("Processing photos with IDs: %s", photo_id_list)
            if external_images:
                logger.info("Processing external images: %s", external_images)

            # Process external images first (they get order 0, 1, 2...)
            external_count = len(external_images)
            self._process_external_images(external_images)

            # Process existing photos (local photos start after externals)
            self._process_existing_photos(photo_id_list, order_map, start_order=start_order + external_count)

            logger.info(
                "Processed %d photo(s) (including %d external) for jersey %s",
                len(photo_id_list),
                len(external_images),
                self.object.id,
            )
        except Exception:
            logger.exception(
                "Failed to process photo IDs for jersey %s",
                self.object.id,
            )
            raise

    def _parse_photo_ids(self, photo_ids):
        """Parse photo_ids string and extract
        photo IDs, external images, and order mapping."""
        if isinstance(photo_ids, str):
            if not photo_ids.strip():
                logger.warning("Empty photo_ids string provided")
                return None

            # Try to parse as JSON first
            try:
                photo_data = json.loads(photo_ids)
            except json.JSONDecodeError:
                # If not JSON, assume it's a comma-separated list
                photo_id_list = [pid.strip() for pid in photo_ids.split(",") if pid.strip()]
                external_images = []
                order_map = {}
                logger.info(
                    "Parsed photo_ids as comma-separated list: %s",
                    photo_id_list,
                )
                return photo_id_list, external_images, order_map

            # Process JSON data
            logger.info("Parsed photo_ids as JSON: %s", photo_data)

            # Extract photo IDs and external images
            photo_id_list = []
            external_images = []
            order_map = {}

            for item in photo_data:
                if isinstance(item, dict):
                    if "id" in item:
                        photo_id = str(item["id"])
                        photo_id_list.append(photo_id)
                        if "order" in item:
                            order_map[photo_id] = item["order"]
                    elif "url" in item:
                        external_images.append(item)
                else:
                    photo_id_list.append(str(item))

            return photo_id_list, external_images, order_map
        logger.warning("Unexpected photo_ids type: %s", type(photo_ids))
        return None

    def _process_external_images(self, external_images):
        """Process external images by downloading and attaching them."""
        for idx, img_data in enumerate(external_images):
            try:
                # Download and attach the external image
                # External images always get order 0, 1, 2... (main image is 0)
                order = img_data.get("order", idx)
                self._download_and_attach_image(
                    self.object,
                    img_data["url"],
                    order=order,
                )
                logger.info(
                    "External image queued for download: %s, order: %s",
                    img_data["url"],
                    order,
                )
            except Exception:
                logger.exception(
                    "Error queuing external image download %s",
                    img_data["url"],
                )
                messages.error(
                    self.request,
                    _("Error downloading image"),
                )

    def _process_existing_photos(self, photo_id_list, order_map, start_order=0):
        """Process existing photos by associating them with the jersey."""

        # Get the photos from the database
        photos = Photo.objects.filter(id__in=photo_id_list, user=self.request.user)

        base_item = self.object
        if hasattr(self.object, "base_item"):
            base_item = self.object.base_item

        has_unprocessed = False

        # Associate photos with the jersey and set their order
        for idx, photo in enumerate(photos):
            # Associate the photo with the jersey
            photo.content_type = ContentType.objects.get_for_model(self.object)
            photo.object_id = self.object.id

            # Set the order: use order_map if provided, otherwise use start_order + index
            if str(photo.id) in order_map:
                mapped_order = order_map[str(photo.id)]
                photo.order = start_order + mapped_order if mapped_order is not None else start_order + idx
            else:
                photo.order = start_order + idx

            if photo.image and not (photo.image_avif and photo.image_avif.name):
                has_unprocessed = True

            photo.save()
            logger.info(
                "Associated photo %s with jersey %s, order: %s (start_order=%s)",
                photo.id,
                self.object.id,
                photo.order,
                start_order,
            )

        if has_unprocessed:
            base_item.is_processing_photos = True
            base_item.save(update_fields=["is_processing_photos"])
            from footycollect.collection.tasks import check_item_photo_processing

            check_item_photo_processing.apply_async(
                args=[base_item.pk],
                countdown=5,
            )

    def _process_external_images_form(self, form):
        """
        Process external images provided by the API.
        Downloads images and associates them with the jersey.
        """
        # Process the main image if it exists
        main_img_url = form.cleaned_data.get("main_img_url")
        if main_img_url:
            try:
                photo = self._download_and_attach_image(self.object, main_img_url)
                if photo:
                    # Set as main image
                    photo.order = 0
                    photo.save()
                    logger.info("Main image saved with ID: %s", photo.id)
                    messages.success(
                        self.request,
                        _("Main image downloaded and attached successfully"),
                    )
            except Exception:
                logger.exception("Error downloading main image %s", main_img_url)
                messages.error(
                    self.request,
                    _("Error downloading main image"),
                )

        # Process additional external images
        external_urls = form.cleaned_data.get("external_image_urls", "")
        if external_urls:
            urls = external_urls.split(",")
            # Start from 1 to keep 0 for main image
            for i, url in enumerate(urls, start=1):
                clean_url = url.strip()
                if clean_url and clean_url != main_img_url:  # Avoid duplicates with main image
                    try:
                        photo = self._download_and_attach_image(self.object, clean_url)
                        if photo:
                            # Set order to maintain image order
                            photo.order = i
                            photo.save()
                    except Exception:
                        logger.exception("Error downloading image %s", clean_url)
                        messages.error(
                            self.request,
                            _("Error downloading image"),
                        )
