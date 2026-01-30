"""
Mixin for handling photo processing in jersey creation.

This mixin provides methods to process external images, associate existing photos,
and handle photo IDs from various sources (JSON, comma-separated, etc.).

Note: This mixin assumes the class using it also has PhotoProcessorMixin
which provides the _download_and_attach_image method.
"""

import json
import logging

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from footycollect.collection.models import BaseItem, Photo

logger = logging.getLogger(__name__)


class PhotoProcessingMixin:
    """Mixin for photo processing functionality."""

    def _get_base_item_for_photos(self):
        """Get base_item for photo associations."""
        from footycollect.collection.models import BaseItem

        if isinstance(self.object, BaseItem):
            base_item = self.object
        else:
            base_item = getattr(self.object, "base_item", None)
            if base_item is None:
                base_item = BaseItem.objects.get(pk=self.object.pk)

        logger.info(
            "Using base_item ID: %s (type: %s) for photo associations. Jersey ID: %s, Jersey type: %s",
            base_item.id if base_item else None,
            type(base_item).__name__ if base_item else None,
            self.object.id,
            type(self.object).__name__,
        )
        return base_item

    def _process_external_images(self, form, base_item=None):
        """
        Process external images provided by the API.
        Download images and associate them with the jersey.

        Args:
            form: The form instance
            base_item: The BaseItem instance to associate photos with (defaults to self.object.base_item)
        """
        if base_item is None:
            base_item = self._get_base_item_for_photos()

        # Process main image if it exists (order=0)
        main_img_url = form.cleaned_data.get("main_img_url")
        if main_img_url:
            try:
                self._download_and_attach_image(base_item, main_img_url, order=0)
                logger.info("Main image queued for download with order=0")
            except Exception:
                logger.exception("Error queuing main image download %s", main_img_url)
                messages.error(
                    self.request,
                    _("Error downloading main image"),
                )

        # Process additional external images (order=1, 2, 3...)
        external_urls = form.cleaned_data.get("external_image_urls", "")
        if external_urls:
            urls = [u.strip() for u in external_urls.split(",") if u.strip() and u.strip() != main_img_url]
            for i, url in enumerate(urls, start=1):
                try:
                    self._download_and_attach_image(base_item, url, order=i)
                    logger.info("External image queued for download with order=%s", i)
                except Exception:
                    logger.exception("Error queuing external image download %s", url)
                    messages.error(
                        self.request,
                        _("Error downloading image"),
                    )

    def _process_photo_ids(self, photo_ids, base_item=None, start_order=0):
        """
        Process photo IDs uploaded through the dropzone.
        Associate existing photos with the jersey.

        Args:
            photo_ids: String with JSON of photos or IDs separated by commas
            base_item: The BaseItem instance to associate photos with (defaults to self.object.base_item)
            start_order: Starting order for local photos (after external images)
        """
        if base_item is None:
            base_item = self._get_base_item_for_photos()

        try:
            # Parse photo IDs and external images
            photo_id_list, external_images, order_map = self._parse_photo_ids(photo_ids)
            if not photo_id_list and not external_images:
                return

            # Process external images first (they get order 0, 1, 2...)
            external_count = len(external_images)
            self._process_external_images_from_photo_ids(external_images, base_item)

            # Process existing photos (local photos start after externals)
            self._associate_existing_photos(
                photo_id_list, order_map, base_item, start_order=start_order + external_count
            )

        except (ValueError, TypeError, KeyError):
            logger.exception("Error processing photo IDs")
            raise

    def _parse_photo_ids(self, photo_ids):
        """Parse photo_ids string and return photo IDs, external images, and order mapping."""
        if not isinstance(photo_ids, str):
            logger.warning("Unexpected photo_ids type: %s", type(photo_ids))
            return [], [], {}

        if not photo_ids.strip():
            logger.warning("Empty photo_ids string provided")
            return [], [], {}

        # Try to parse as JSON first
        try:
            photo_data = json.loads(photo_ids)
            logger.info("Parsed photo_ids as JSON: %s", photo_data)
            return self._extract_photo_data_from_json(photo_data)
        except json.JSONDecodeError:
            # If not JSON, assume it's a comma-separated list
            photo_id_list = [pid.strip() for pid in photo_ids.split(",") if pid.strip()]
            logger.info("Parsed photo_ids as comma-separated list: %s", photo_id_list)
            return photo_id_list, [], {}

    def _extract_photo_data_from_json(self, photo_data):
        """Extract photo IDs, external images, and order mapping from JSON data."""
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

    def _process_external_images_from_photo_ids(self, external_images, base_item=None):
        """Process external images from photo IDs data.

        Args:
            external_images: List of external image data dictionaries
            base_item: The BaseItem instance to associate photos with (defaults to self.object.base_item)
        """
        if base_item is None:
            base_item = self._get_base_item_for_photos()

        if not external_images:
            return

        logger.info("Processing external images: %s", external_images)
        for idx, img_data in enumerate(external_images):
            try:
                order = img_data.get("order", idx)
                self._download_and_attach_image(base_item, img_data["url"], order=order)
                logger.info(
                    "External image queued for download: %s, order: %s",
                    img_data["url"],
                    order,
                )
            except Exception:
                logger.exception("Error queuing external image download %s", img_data["url"])
                messages.error(self.request, _("Error downloading image"))

    def _associate_existing_photos(self, photo_id_list, order_map, base_item=None, start_order=0):
        """Associate existing photos with the jersey and set their order.

        Args:
            photo_id_list: List of photo IDs to associate
            order_map: Dictionary mapping photo IDs to their order
            base_item: The BaseItem instance to associate photos with (defaults to self.object.base_item)
            start_order: Starting order for local photos (after external images)
        """
        if base_item is None:
            base_item = self._get_base_item_for_photos()

        if not photo_id_list:
            return

        logger.info("Attempting to associate existing photos, IDs: %s, start_order: %s", photo_id_list, start_order)

        # Ensure photo IDs are integers and unique
        try:
            photo_ids_int = list({int(pid) for pid in photo_id_list if str(pid).isdigit()})
        except (ValueError, TypeError):
            logger.exception("Failed to parse photo IDs as integers (input was: %s)", photo_id_list)
            return

        if not photo_ids_int:
            logger.warning("No valid photo IDs found to associate.")
            return

        # Query for photos belonging to the current user
        photos = Photo.objects.filter(id__in=photo_ids_int, user=self.request.user)

        # Log how many photos were found
        logger.info("Found %d photos matching IDs %s for user %s", len(photos), photo_ids_int, self.request.user)

        if not photos.exists():
            logger.warning("No photos found with IDs %s for user %s", photo_ids_int, self.request.user)
            # Try without user filter to see if photos exist
            all_photos = Photo.objects.filter(id__in=photo_ids_int)
            logger.info("Total photos with these IDs (any user): %d", all_photos.count())
            return

        # Get ContentType for BaseItem model (not the instance)
        content_type = ContentType.objects.get_for_model(BaseItem)

        for idx, photo in enumerate(photos):
            # Associate the photo with the base_item (GenericRelation is on BaseItem, not Jersey)
            photo.content_type = content_type
            photo.object_id = base_item.id

            # Set the order: use order_map if provided, otherwise use start_order + index
            if str(photo.id) in order_map:
                mapped_order = order_map[str(photo.id)]
                photo.order = start_order + mapped_order if mapped_order is not None else start_order + idx
            else:
                photo.order = start_order + idx

            photo.save()
            logger.info(
                "Associated photo %s with base_item %s (jersey %s), order: %s, content_type: %s",
                photo.id,
                base_item.id,
                self.object.id,
                photo.order,
                content_type,
            )

            # Verify the association was saved correctly
            photo.refresh_from_db()
            logger.info(
                "Photo %s after save - content_type_id: %s, object_id: %s",
                photo.id,
                photo.content_type_id,
                photo.object_id,
            )

        logger.info("Processed %s photos for jersey %s (base_item %s)", len(photos), self.object.id, base_item.id)
