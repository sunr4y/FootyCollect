"""
Photo-related views for the collection app.

This module contains all views that handle photo operations including
upload, download, deletion, and processing.
"""

import json
import logging
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import Error as DBError
from django.db.models import Max
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods, require_POST

from footycollect.collection.models import Photo
from footycollect.collection.services import get_photo_service

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

    def _download_and_attach_image(self, instance, image_url):
        """
        Download an image from a URL and associate it with the instance.
        Returns the created photo if successful, None otherwise.
        """
        # Only initialize when this method is actually called
        self._ensure_photo_processor_initialized()

        try:
            # Ensure the URL is properly formatted
            if not image_url.startswith("http"):
                image_url = f"https://{image_url}"

            logger.info("Downloading image from URL: %s", image_url)

            # Get the name of the file from the URL
            image_name = Path(urlparse(image_url).path).name
            if not image_name:
                image_name = f"external_image_{uuid.uuid4().hex[:8]}.jpg"

            # Download the image
            response = requests.get(image_url, stream=True, timeout=30)
            response.raise_for_status()

            # Create a temporary file
            img_temp = tempfile.NamedTemporaryFile(delete=True)
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    img_temp.write(chunk)
            img_temp.flush()

            # Create the photo and associate it with the instance
            photo = Photo(content_object=instance, user=instance.user)
            photo.image.save(image_name, File(img_temp), save=False)

            # Set the order
            last_order = instance.photos.aggregate(Max("order"))["order__max"] or -1
            photo.order = last_order + 1

            # Save the photo
            photo.save()

            # Try to create AVIF version, but don't fail if not implemented
            if hasattr(photo, "create_avif_version"):
                try:
                    photo.create_avif_version()
                except (OSError, ValueError) as e:
                    logger.warning(
                        "Could not create AVIF version for image %s: %s",
                        image_name,
                        e,
                    )

        except Exception:
            logger.exception("Error downloading image %s", image_url)
            return None

        return photo

    def _process_photo_ids(self, photo_ids):
        """
        Process photo IDs uploaded through the dropzone.
        Associates existing photos with the jersey.
        photo_ids: String with JSON of photos or comma-separated IDs
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

            # Process external images first
            self._process_external_images(external_images)

            # Process existing photos
            self._process_existing_photos(photo_id_list, order_map)

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
        for img_data in external_images:
            try:
                # Download and attach the external image
                photo = self._download_and_attach_image(
                    self.object,
                    img_data["url"],
                )
                if photo:
                    photo.order = img_data.get("order", 0)
                    photo.save()
                    logger.info(
                        "External image downloaded and attached with ID: %s, order: %s",
                        photo.id,
                        photo.order,
                    )
            except Exception:
                logger.exception(
                    "Error downloading external image %s",
                    img_data["url"],
                )
                messages.error(
                    self.request,
                    _("Error downloading image"),
                )

    def _process_existing_photos(self, photo_id_list, order_map):
        """Process existing photos by associating them with the jersey."""
        # Get the photos from the database
        photos = Photo.objects.filter(id__in=photo_id_list, user=self.request.user)

        # Associate photos with the jersey and set their order
        for photo in photos:
            # Associate the photo with the jersey
            photo.content_type = ContentType.objects.get_for_model(self.object)
            photo.object_id = self.object.id

            # Set the order
            if str(photo.id) in order_map:
                photo.order = order_map[str(photo.id)]

            photo.save()
            logger.info(
                "Associated photo %s with jersey %s, order: %s",
                photo.id,
                self.object.id,
                photo.order,
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
