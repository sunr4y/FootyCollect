"""
Celery tasks for the collection app.
"""

import logging
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests
from celery import shared_task
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.db.models import Max
from django.db.utils import OperationalError

from footycollect.core.utils.images import optimize_image

from .models import BaseItem, Photo

logger = logging.getLogger(__name__)


def _is_allowed_image_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        allowed = getattr(
            settings,
            "ALLOWED_EXTERNAL_IMAGE_HOSTS",
            ["cdn.footballkitarchive.com", "www.footballkitarchive.com"],
        )
        return hostname in [h.lower() for h in allowed]
    except (ValueError, AttributeError):
        return False


@shared_task
def cleanup_orphaned_photos():
    try:
        logger.info("Starting orphaned photos cleanup task")
        call_command(
            "cleanup_orphaned_photos",
            "--incomplete-only",
            "--older-than-hours=24",
            verbosity=1,
        )
    except (CommandError, OSError, OperationalError):
        logger.exception("Error in orphaned photos cleanup task")
        raise
    else:
        logger.info("Orphaned photos cleanup task completed successfully")
        return "Orphaned photos cleanup completed"


@shared_task
def cleanup_all_orphaned_photos():
    try:
        logger.info("Starting comprehensive orphaned photos cleanup task")
        call_command(
            "cleanup_orphaned_photos",
            verbosity=1,
        )
    except (CommandError, OSError, OperationalError):
        logger.exception("Error in comprehensive orphaned photos cleanup task")
        raise
    else:
        logger.info("Comprehensive orphaned photos cleanup task completed successfully")
        return "Comprehensive orphaned photos cleanup completed"


@shared_task
def cleanup_old_incomplete_photos():
    try:
        logger.info("Starting old incomplete photos cleanup task")
        call_command(
            "cleanup_orphaned_photos",
            "--incomplete-only",
            "--older-than-hours=168",
            verbosity=1,
        )
    except (CommandError, OSError, OperationalError):
        logger.exception("Error in old incomplete photos cleanup task")
        raise
    else:
        logger.info("Old incomplete photos cleanup task completed successfully")
        return "Old incomplete photos cleanup completed"


@shared_task
def download_external_image_and_attach(app_label, model_name, object_id, image_url, order=0):
    try:
        if not image_url.startswith("http"):
            image_url = f"https://{image_url}"

        if not _is_allowed_image_url(image_url):
            logger.warning("Blocked download from untrusted host: %s", image_url)
            msg = "URL from untrusted source: " + str(image_url)
            raise ValueError(msg)  # noqa: TRY301

        logger.info("Downloading image from URL: %s", image_url)

        image_name = Path(urlparse(image_url).path).name
        if not image_name:
            image_name = f"external_image_{uuid.uuid4().hex[:8]}.jpg"

        response = requests.get(image_url, stream=True, timeout=30)
        response.raise_for_status()

        img_temp = tempfile.NamedTemporaryFile(delete=True)
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                img_temp.write(chunk)
        img_temp.flush()

        model = ContentType.objects.get_by_natural_key(app_label, model_name).model_class()
        instance = model.objects.get(pk=object_id)

        photo = Photo(content_object=instance, user=instance.user)
        photo.image.save(image_name, File(img_temp), save=False)

        if order is not None:
            photo.order = order
        else:
            last_order = instance.photos.aggregate(Max("order"))["order__max"] or -1
            photo.order = last_order + 1

        photo.save()
        logger.info("Photo %s downloaded and attached to item %s", photo.id, object_id)

        check_item_photo_processing.apply_async(
            args=[object_id],
            countdown=3,
        )
    except (ValueError, requests.RequestException, OSError):
        logger.exception("Error downloading image %s", image_url)
        check_item_photo_processing.delay(object_id)
        raise
    else:
        return photo.id


@shared_task
def process_photo_to_avif(photo_id):
    try:
        photo = Photo.objects.get(pk=photo_id)
    except Photo.DoesNotExist:
        logger.warning("Photo %s does not exist", photo_id)
        return

    if not photo.image:
        logger.warning("Photo %s has no image to process", photo_id)
        return

    optimized = optimize_image(photo.image)
    if not optimized:
        logger.warning("Optimization returned no data for photo %s", photo_id)
        return

    photo.image_avif.save(optimized.name, optimized, save=False)
    photo.save(update_fields=["image_avif"])
    logger.info("Photo %s AVIF processing completed", photo_id)

    if photo.content_object:
        base_item = photo.content_object
        if hasattr(base_item, "base_item"):
            base_item = base_item.base_item
        check_item_photo_processing.apply_async(
            args=[base_item.pk],
            countdown=2,
        )


@shared_task
def check_item_photo_processing(item_id):
    try:
        base_item = BaseItem.objects.get(pk=item_id)
        photos = base_item.photos.all()

        if not photos.exists():
            with transaction.atomic():
                base_item.is_processing_photos = False
                base_item.save(update_fields=["is_processing_photos"])
            logger.info("No photos for item %s, marking as not processing", item_id)
            return

        photos_with_image = [photo for photo in photos if photo.image]

        if not photos_with_image:
            with transaction.atomic():
                base_item.is_processing_photos = False
                base_item.save(update_fields=["is_processing_photos"])
            logger.info("No photos with images for item %s, marking as not processing", item_id)
            return

        def is_photo_processed(photo):
            if not photo.image_avif:
                return False
            try:
                name = getattr(photo.image_avif, "name", None)
                return bool(name and str(name).strip())
            except (ValueError, AttributeError):
                return False

        all_processed = all(is_photo_processed(photo) for photo in photos_with_image)

        if all_processed:
            base_item.refresh_from_db()
            if base_item.is_processing_photos:
                with transaction.atomic():
                    base_item.is_processing_photos = False
                    base_item.save(update_fields=["is_processing_photos"])
                logger.info("All %d photos processed for item %s, flag updated", len(photos_with_image), item_id)
            else:
                logger.debug("Item %s already marked as not processing", item_id)
        else:
            unprocessed_count = sum(1 for photo in photos_with_image if not is_photo_processed(photo))
            logger.debug(
                "Item %s still has %d/%d photos processing",
                item_id,
                unprocessed_count,
                len(photos_with_image),
            )
    except BaseItem.DoesNotExist:
        logger.warning("Item %s does not exist", item_id)
    except Exception:
        logger.exception("Error checking photo processing for item %s", item_id)
