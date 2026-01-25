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
from footycollect.collection.services.item_service import ItemService
from footycollect.collection.services.photo_service import PhotoService
from footycollect.core.models import TypeK

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
            # Setup form instance
            self._setup_form_instance(form, user)

            # Process kit data if available
            kit_id = form.cleaned_data.get("kit_id")
            if kit_id:
                self._process_kit_data(form, kit_id)

            # Process related entities from the API
            self._process_new_entities(form)

            # Save the item
            item = form.save()

            # Process external images
            self._process_external_images(form, item)

            # Process uploaded photos through the dropzone
            photo_ids = form.data.get("photo_ids", "")
            if photo_ids:
                self._process_photo_ids(photo_ids, item)

            # Mark as not draft
            item.is_draft = False
            item.save()

            logger.info("Item created successfully with ID: %s", item.id)
            return item

    def _setup_form_instance(self, form, user: User) -> None:
        """Setup basic form instance attributes."""
        # Assign the current user
        form.instance.user = user

        # Assign country if selected
        if form.cleaned_data.get("country_code"):
            form.instance.country = form.cleaned_data["country_code"]
            logger.info("Set country to %s", form.cleaned_data["country_code"])

    def _process_kit_data(self, form, kit_id: str) -> None:
        """Process kit data from FKAPI and update form instance."""
        try:
            # Get kit data from FKAPI
            kit_data = self._fetch_kit_data_from_api(kit_id)
            if not kit_data:
                return

            # Store kit_data on form for later use in Kit creation
            if not hasattr(form, "fkapi_data"):
                form.fkapi_data = {}
            form.fkapi_data.update(kit_data)

            # Add kit ID to description for reference
            self._add_kit_id_to_description(form, kit_id)

            # Process kit information
            self._process_kit_information(form, kit_data)

        except (ValueError, TypeError, KeyError, AttributeError):
            logger.exception("Error processing kit data for kit_id %s", kit_id)
            raise

    def _fetch_kit_data_from_api(self, kit_id: str) -> dict[str, Any] | None:
        """Fetch kit data from FKAPI."""
        kit_data = self.fkapi_client.get_kit_details(kit_id)
        if kit_data is None:
            logger.warning("FKAPI unavailable for kit_id %s", kit_id)
        return kit_data

    def _add_kit_id_to_description(self, form, kit_id: str) -> None:
        """Add kit ID to description for reference."""
        current_description = form.cleaned_data.get("description", "")
        kit_reference = f"\n\n[Kit ID: {kit_id}]"

        if kit_reference not in current_description:
            form.cleaned_data["description"] = current_description + kit_reference

    def _process_kit_name(self, form, kit_data: dict[str, Any]) -> None:
        """Process kit name from API data."""
        if "name" in kit_data:
            form.cleaned_data["name"] = kit_data["name"]

    def _process_kit_description(self, form, kit_data: dict[str, Any]) -> None:
        """Process kit description from API data."""
        if "description" not in kit_data:
            return
        current_description = form.cleaned_data.get("description", "")
        api_description = kit_data["description"]
        if api_description and api_description not in current_description:
            form.cleaned_data["description"] = f"{current_description}\n\n{api_description}"

    def _process_kit_type(self, kit_data: dict[str, Any]) -> None:
        """Process kit type from API data."""
        type_obj = kit_data.get("type")
        if not type_obj:
            return

        if isinstance(type_obj, str):
            type_name = type_obj
            type_data = {}
        else:
            type_name = type_obj.get("name")
            type_data = type_obj

        if not type_name:
            return

        category = type_data.get("category", "match")
        if category == "jacket":
            logger.info("Skipping TypeK creation for jacket item: %s (handled as outerwear)", type_name)
            return

        logger.info("Processing kit type: %s", type_name)
        try:
            type_k = TypeK.objects.filter(name=type_name).first()
            if not type_k:
                type_k = TypeK.objects.filter(name__iexact=type_name).first()

            if type_k:
                self._update_existing_type_k(type_k, category, type_data, type_name)
            else:
                self._create_new_type_k(type_name, category, type_data)
        except Exception:
            logger.exception("Error creating kit type %s", type_name)

    def _update_existing_type_k(self, type_k: TypeK, category: str, type_data: dict[str, Any], type_name: str) -> None:
        """Update an existing TypeK object."""
        needs_update = False
        if category and type_k.category != category:
            type_k.category = category
            needs_update = True
        if "is_goalkeeper" in type_data and type_k.is_goalkeeper != type_data["is_goalkeeper"]:
            type_k.is_goalkeeper = type_data["is_goalkeeper"]
            needs_update = True

        if needs_update:
            type_k.save()
            logger.info("Updated kit type: %s (ID: %s)", type_name, type_k.id)
        else:
            logger.info("Found existing kit type: %s (ID: %s)", type_name, type_k.id)

    def _create_new_type_k(self, type_name: str, category: str, type_data: dict[str, Any]) -> None:
        """Create a new TypeK object."""
        type_k = TypeK.objects.create(
            name=type_name,
            category=category,
            is_goalkeeper=type_data.get("is_goalkeeper", False),
        )
        logger.info("Created new kit type: %s (ID: %s)", type_name, type_k.id)

    def _process_kit_information(self, form, kit_data: dict[str, Any]) -> None:
        """Process kit information from API data."""
        self._process_kit_name(form, kit_data)
        self._process_kit_description(form, kit_data)
        self._process_kit_type(kit_data)
        if "colors" in kit_data:
            self._process_kit_colors(form, kit_data["colors"])

    def _process_kit_colors(self, form, colors: list[dict[str, Any]]) -> None:
        """
        Process kit colors and set them in form.data (not cleaned_data).

        CRITICAL: Must set in form.data so clean methods can access via self.data
        Only set if not already present in POST data (POST data takes precedence)
        """
        if not colors:
            return

        # Make form.data mutable
        if hasattr(form.data, "_mutable"):
            form.data._mutable = True  # noqa: SLF001
        else:
            form.data = form.data.copy()

        # Only set main_color if not already in POST data
        # POST data from JavaScript takes precedence over API data
        if not form.data.get("main_color"):
            main_color = colors[0].get("name", "")
            if main_color:
                form.data["main_color"] = main_color
                logger.info("Set main_color in form.data from API: %s", main_color)
        else:
            logger.info("main_color already in form.data: %s (keeping POST value)", form.data.get("main_color"))

        # Only set secondary_colors if not already in POST data
        # POST data from JavaScript takes precedence over API data
        has_secondary_colors = form.data.get("secondary_colors") or (
            hasattr(form.data, "getlist") and form.data.getlist("secondary_colors")
        )
        if not has_secondary_colors:
            if len(colors) > 1:
                secondary_colors = [color.get("name", "") for color in colors[1:] if color.get("name")]
                if secondary_colors:
                    if hasattr(form.data, "setlist"):
                        form.data.setlist("secondary_colors", secondary_colors)
                    else:
                        # Fallback for non-QueryDict
                        form.data["secondary_colors"] = secondary_colors
                    logger.info("Set secondary_colors in form.data from API: %s", secondary_colors)
        else:
            existing = (
                form.data.getlist("secondary_colors")
                if hasattr(form.data, "getlist")
                else form.data.get("secondary_colors")
            )
            logger.info("secondary_colors already in form.data: %s (keeping POST value)", existing)

    def _process_new_entities(self, form) -> None:
        """Process new entities from the API."""
        # This method would handle creating new clubs, seasons, etc.
        # Implementation depends on specific requirements

    def _process_external_images(self, form, item) -> None:
        """Process external images from API data."""
        # This method would handle downloading and processing external images
        # Implementation depends on specific requirements

    def _process_photo_ids(self, photo_ids: str, item) -> None:
        """Process uploaded photos through the dropzone."""
        if not photo_ids:
            return

        try:
            # Parse photo IDs
            photo_id_list = [int(pid) for pid in photo_ids.split(",") if pid.strip()]

            # Associate photos with item
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
