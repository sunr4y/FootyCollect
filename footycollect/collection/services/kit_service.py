"""
Service for Kit creation and management.

This service handles Kit creation and linking for jerseys, ensuring
that every jersey has a corresponding Kit record.
"""

import logging
from typing import Any

from django.utils.text import slugify

from footycollect.collection.models import BaseItem, Jersey
from footycollect.core.models import Kit, TypeK

logger = logging.getLogger(__name__)


class KitService:
    """Service for Kit creation and management."""

    def get_or_create_kit_for_jersey(
        self,
        base_item: BaseItem,
        jersey: Jersey,
        fkapi_data: dict[str, Any] | None = None,
        kit_id: str | None = None,
    ) -> Kit:
        """
        Get or create a Kit for a jersey.

        Args:
            base_item: The BaseItem instance
            jersey: The Jersey instance
            fkapi_data: Optional FKAPI data dictionary
            kit_id: Optional FKAPI kit ID

        Returns:
            Kit instance (existing or newly created)
        """
        if fkapi_data is None:
            fkapi_data = {}

        kit_id_fka = None
        if kit_id:
            try:
                kit_id_fka = int(kit_id)
            except (ValueError, TypeError):
                logger.warning("Invalid kit_id format: %s", kit_id)

        if kit_id_fka:
            kit = Kit.objects.filter(id_fka=kit_id_fka).first()
            if kit:
                logger.info("Found existing kit with id_fka: %s", kit_id_fka)
                return kit

        kit_name = self._build_kit_name(base_item, fkapi_data)
        kit_slug = self._build_kit_slug(base_item, kit_name, fkapi_data)
        lookup_params, defaults = self._build_kit_params(base_item, kit_name, kit_slug, kit_id_fka, fkapi_data)

        kit, created = Kit.objects.get_or_create(
            **lookup_params,
            defaults=defaults,
        )

        if created:
            logger.info("Created new kit: %s (ID: %s, slug: %s)", kit.name, kit.id, kit.slug)
        else:
            logger.info("Found existing kit: %s (ID: %s, slug: %s)", kit.name, kit.id, kit.slug)
            main_img_url = self._get_main_img_url(base_item, fkapi_data)
            self._update_existing_kit_image(kit, main_img_url)

        if base_item.competitions.exists():
            kit.competition.set(base_item.competitions.all())
            logger.info("Set competitions for kit %s", kit.id)

        return kit

    def _build_kit_params(self, base_item, kit_name, kit_slug, kit_id_fka, fkapi_data):
        """Build lookup_params and defaults for Kit creation."""
        lookup_params = {"slug": kit_slug}

        defaults = {
            "name": kit_name,
            "team": base_item.club,
            "season": base_item.season,
            "brand": base_item.brand,
        }

        if kit_id_fka:
            lookup_params["id_fka"] = kit_id_fka
            defaults["id_fka"] = kit_id_fka

        type_k = self._get_or_create_type_k(base_item, fkapi_data)
        if type_k:
            defaults["type"] = type_k

        main_img_url = self._get_main_img_url(base_item, fkapi_data)
        if main_img_url:
            defaults["main_img_url"] = main_img_url
        else:
            defaults["main_img_url"] = "https://www.footballkitarchive.com/static/logos/not_found.png"

        return lookup_params, defaults

    def _update_existing_kit_image(self, kit, main_img_url):
        """Update main_img_url for existing kit if needed."""
        if main_img_url and (
            not kit.main_img_url or kit.main_img_url == "https://www.footballkitarchive.com/static/logos/not_found.png"
        ):
            kit.main_img_url = main_img_url
            kit.save(update_fields=["main_img_url"])
            logger.info("Updated main_img_url for existing kit %s", kit.id)

    def _build_kit_name(self, base_item: BaseItem, fkapi_data: dict[str, Any]) -> str:
        """Build a kit name from base_item and optional FKAPI data."""
        if fkapi_data.get("name"):
            return fkapi_data["name"]

        parts = []
        if base_item.brand:
            parts.append(base_item.brand.name)
        if base_item.club:
            parts.append(base_item.club.name)
        if base_item.season:
            parts.append(str(base_item.season))

        if parts:
            return " ".join(parts)

        return f"Kit for {base_item.name}"

    def _build_kit_slug(self, base_item: BaseItem, kit_name: str, fkapi_data: dict[str, Any]) -> str:
        """Build a kit slug from kit_name and optional FKAPI data."""
        if fkapi_data.get("slug"):
            return fkapi_data["slug"]

        base_slug = slugify(kit_name)
        if not base_slug:
            base_slug = slugify(base_item.name)

        slug = base_slug
        counter = 1
        while Kit.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def _extract_type_info(self, fkapi_data: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
        """Extract type name and data from FKAPI data."""
        type_obj = fkapi_data.get("type")
        if not type_obj:
            return None

        if isinstance(type_obj, str):
            return (type_obj, {})
        type_name = type_obj.get("name")
        return (type_name, type_obj) if type_name else None

    def _find_existing_type_k(self, type_name: str) -> TypeK | None:
        """Find existing TypeK by name (exact or case-insensitive)."""
        type_k = TypeK.objects.filter(name=type_name).first()
        if not type_k:
            type_k = TypeK.objects.filter(name__iexact=type_name).first()
        return type_k

    def _update_type_k_if_needed(
        self,
        type_k: TypeK,
        category: str,
        type_data: dict[str, Any],
        type_name: str,
    ) -> None:
        """Update TypeK if category or is_goalkeeper changed."""
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

    def _get_or_create_type_k(self, base_item: BaseItem, fkapi_data: dict[str, Any]) -> TypeK | None:
        """Get or create TypeK from FKAPI data with full type information.

        Note: Items with category="jacket" are not kits and should be handled as outerwear.
        This method returns None for jacket items.
        """
        type_info = self._extract_type_info(fkapi_data)
        if not type_info:
            return None

        type_name, type_data = type_info
        category = type_data.get("category", "match")
        if category == "jacket":
            logger.info("Skipping TypeK creation for jacket item: %s (handled as outerwear)", type_name)
            return None

        logger.info("Processing kit type: %s", type_name)

        try:
            type_k = self._find_existing_type_k(type_name)
            if type_k:
                self._update_type_k_if_needed(type_k, category, type_data, type_name)
            else:
                type_k = TypeK.objects.create(
                    name=type_name,
                    category=category,
                    is_goalkeeper=type_data.get("is_goalkeeper", False),
                )
                logger.info("Created new kit type: %s (ID: %s)", type_name, type_k.id)
        except (ValueError, TypeError):
            logger.exception("Error creating kit type %s", type_name)
            return None
        else:
            return type_k

    def _get_main_img_url(self, base_item: BaseItem, fkapi_data: dict[str, Any]) -> str:
        """Get main image URL from FKAPI data or base_item photos."""
        if fkapi_data.get("main_img_url"):
            return fkapi_data["main_img_url"]

        main_photo = base_item.photos.order_by("order").first()
        if main_photo:
            return main_photo.get_image_url()

        return ""
