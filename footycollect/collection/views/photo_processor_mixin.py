"""
Reusable mixin for photo processing logic.

Extracted from photo_views to keep that module smaller and focused.
"""

import json
import logging

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from footycollect.collection.models import Photo
from footycollect.collection.tasks import (
    check_item_photo_processing,
    download_external_image_and_attach,
)

logger = logging.getLogger(__name__)


class PhotoProcessorMixin:
    """Mixin that provides photo processing functionality with lazy loading."""

    def __init__(self, *args, **kwargs):
        """Initialize the mixin with lazy loading."""
        super().__init__(*args, **kwargs)
        if not hasattr(self, "_photo_processor_initialized"):
            self._photo_processor_initialized = False

    def _ensure_photo_processor_initialized(self):
        """Lazy initialization of photo processor components."""
        if not hasattr(self, "_photo_processor_initialized"):
            self._photo_processor_initialized = False

        if not self._photo_processor_initialized:
            self._photo_processor_initialized = True
            logger.debug("PhotoProcessorMixin initialized for %s", self.__class__.__name__)

    def _download_and_attach_image(self, instance, image_url, order=None):
        """
        Queue a background task to download and attach an external image.

        The task is enqueued after the current transaction commits so the worker
        sees the instance in the database (avoids BaseItem.DoesNotExist).
        """
        self._ensure_photo_processor_initialized()

        try:
            app_label = instance._meta.app_label
            model_name = instance._meta.model_name
            object_id = instance.pk

            def enqueue():
                download_external_image_and_attach.delay(
                    app_label,
                    model_name,
                    object_id,
                    image_url,
                    order,
                )

            transaction.on_commit(enqueue)
        except Exception:
            logger.exception("Error queuing download task for image %s", image_url)

    def _process_photo_ids(self, photo_ids, start_order=0):
        """
        Process photo IDs uploaded through the dropzone.

        Associates existing photos with the jersey and triggers AVIF processing when needed.
        """
        try:
            parsed_data = self._parse_photo_ids(photo_ids)
            if not parsed_data:
                return

            photo_id_list, external_images, order_map = parsed_data

            logger.info("Processing photos with IDs: %s", photo_id_list)
            if external_images:
                logger.info("Processing external images: %s", external_images)

            external_count = len(external_images)
            self._process_external_images(external_images)

            self._process_existing_photos(
                photo_id_list,
                order_map,
                start_order=start_order + external_count,
            )
        except Exception:
            logger.exception("Failed to process photo IDs for jersey %s", self.object.id)
            raise

    def _parse_photo_ids(self, photo_ids):
        """Parse photo_ids string and extract photo IDs, external images, and order mapping."""
        if not isinstance(photo_ids, str):
            logger.warning("Unexpected photo_ids type: %s", type(photo_ids))
            return None

        if not photo_ids.strip():
            logger.warning("Empty photo_ids string provided")
            return None

        try:
            photo_data = json.loads(photo_ids)
        except json.JSONDecodeError:
            photo_id_list = [pid.strip() for pid in photo_ids.split(",") if pid.strip()]
            logger.info("Parsed photo_ids as comma-separated list: %s", photo_id_list)
            return photo_id_list, [], {}

        logger.info("Parsed photo_ids as JSON: %s", photo_data)

        photo_id_list: list[str] = []
        external_images: list[dict] = []
        order_map: dict[str, int] = {}

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

    def _process_external_images(self, external_images):
        """Process external images by downloading and attaching them."""
        for idx, img_data in enumerate(external_images):
            try:
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
                logger.exception("Error queuing external image download %s", img_data["url"])
                messages.error(self.request, _("Error downloading image"))

    def _process_existing_photos(self, photo_id_list, order_map, start_order=0):
        """Process existing photos by associating them with the jersey and updating AVIF state."""
        photos = Photo.objects.filter(id__in=photo_id_list, user=self.request.user)

        base_item = self.object
        if hasattr(self.object, "base_item"):
            base_item = self.object.base_item

        has_unprocessed = False

        for idx, photo in enumerate(photos):
            photo.content_type = ContentType.objects.get_for_model(self.object)
            photo.object_id = self.object.id

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
            check_item_photo_processing.apply_async(
                args=[base_item.pk],
                countdown=5,
            )

    def _process_external_images_form(self, form):
        """
        Process external images provided by the API.

        Downloads images and associates them with the jersey.
        """
        main_img_url = form.cleaned_data.get("main_img_url")
        if main_img_url:
            try:
                photo = self._download_and_attach_image(self.object, main_img_url)
                if photo:
                    photo.order = 0
                    photo.save()
                    logger.info("Main image saved with ID: %s", photo.id)
                    messages.success(
                        self.request,
                        _("Main image downloaded and attached successfully"),
                    )
            except Exception:
                logger.exception("Error downloading main image %s", main_img_url)
                messages.error(self.request, _("Error downloading main image"))

        external_urls = form.cleaned_data.get("external_image_urls", "")
        if not external_urls:
            return

        urls = external_urls.split(",")
        for i, url in enumerate(urls, start=1):
            clean_url = url.strip()
            if not clean_url or clean_url == main_img_url:
                continue
            try:
                photo = self._download_and_attach_image(self.object, clean_url)
                if photo:
                    photo.order = i
                    photo.save()
            except Exception:
                logger.exception("Error downloading image %s", clean_url)
                messages.error(self.request, _("Error downloading image"))
