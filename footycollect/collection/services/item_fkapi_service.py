"""
Service for item FKAPI processing business logic.

This service handles complex business operations related to item creation
with FKAPI integration, including kit processing and entity creation.
Works for all item types (jersey, shorts, outerwear, etc.).
"""

import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction

from footycollect.api.client import FKAPIClient
from footycollect.collection.models import (
    BaseItem,
    Photo,
)
from footycollect.collection.services.fkapi_kit_processor import FKAPIKitProcessor
from footycollect.collection.services.item_service import ItemService
from footycollect.collection.services.photo_service import PhotoService

User = get_user_model()
logger = logging.getLogger(__name__)


class ItemFKAPIService:
    """
    Service for item FKAPI processing business logic.

    This service handles complex operations related to item creation
    with FKAPI integration, including kit processing and entity creation.
    Works for all item types (jersey, shorts, outerwear, etc.).
    """

    def __init__(self):
        self.fkapi_client = FKAPIClient()
        self.kit_processor = FKAPIKitProcessor(self.fkapi_client)
        self.item_service = ItemService()
        self.photo_service = PhotoService()

    def process_item_creation(self, form, user: User, item_type: str = "jersey"):
        """
        Process item creation with FKAPI integration.

        Args:
            form: Validated form instance
            user: User creating the item
            item_type: Type of item (jersey, shorts, outerwear, etc.)

        Returns:
            Created item instance
        """
        with transaction.atomic():
            self._setup_form_instance(form, user)

            kit_id = form.cleaned_data.get("kit_id")
            if kit_id:
                self.kit_processor.process_kit_data(form, kit_id)

            self._process_new_entities(form)

            item = form.save()

            self._process_external_images(form, item)

            photo_ids = form.data.get("photo_ids", "")
            if photo_ids:
                self._process_photo_ids(photo_ids, item)

            item.is_draft = False
            item.save()

            logger.info("Item created successfully with ID: %s", item.id)
            return item

    def _setup_form_instance(self, form, user: User) -> None:
        """Setup basic form instance attributes."""
        form.instance.user = user

        if form.cleaned_data.get("country_code"):
            form.instance.country = form.cleaned_data["country_code"]
            logger.info("Set country to %s", form.cleaned_data["country_code"])

    def _process_new_entities(self, form) -> None:
        """Process new entities from the API."""

    def _process_external_images(self, form, item) -> None:
        """Process external images from API data."""

    def _process_photo_ids(self, photo_ids: str, item) -> None:
        """Process uploaded photos through the dropzone."""
        if not photo_ids:
            return

        try:
            photo_id_list = [int(pid) for pid in photo_ids.split(",") if pid.strip()]

            for photo_id in photo_id_list:
                photo = Photo.objects.get(id=photo_id)
                photo.content_object = item
                photo.save()

            logger.info("Associated %d photos with item %s", len(photo_id_list), item.id)

        except (ValueError, TypeError, KeyError):
            logger.exception("Error processing photo IDs %s", photo_ids)
            raise

    def get_form_data_for_item_creation(self, item_type: str = "jersey") -> dict[str, Any]:
        """
        Get form data for item creation.

        Args:
            item_type: Type of item (jersey, shorts, outerwear, etc.)

        Returns:
            Dictionary with form data
        """
        item_service = ItemService()
        form_data = item_service.get_form_data()

        return {
            "color_choices": form_data["colors"]["main_colors"],
            "design_choices": [{"value": d[0], "label": d[1]} for d in BaseItem.DESIGN_CHOICES],
        }
