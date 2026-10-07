"""
Service for item-related business logic.

This service handles complex business operations related to items,
orchestrating between repositories and implementing business rules.
"""

import re
from typing import Any

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count, QuerySet
from django_countries import countries

from footycollect.collection.models import BaseItem, Jersey
from footycollect.collection.repositories import ColorRepository, ItemRepository, PhotoRepository

User = get_user_model()

HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$")


class ItemService:
    """
    Service for item-related business logic.

    This service handles complex operations that involve multiple repositories
    and implements business rules for item management.
    """

    _COUNTRY_NAME_MAP: dict[str, str] | None = None
    _DESIGN_LABEL_MAP: dict[str, str] | None = None

    def __init__(self):
        self.item_repository = ItemRepository()
        self.photo_repository = PhotoRepository()
        self.color_repository = ColorRepository()

    def create_item_with_photos(
        self,
        _user: User,
        item_data: dict[str, Any],
        photos: list[Any] | None = None,
    ) -> Jersey:
        """
        Create an item with associated photos.

        Args:
            _user: User creating the item (kept for API consistency; item user comes from item_data).
            item_data: Dictionary containing item data
            photos: List of photo files

        Returns:
            Created item instance

        Raises:
            ValueError: If item data is invalid
        """
        with transaction.atomic():
            # Create the item
            item = self.item_repository.create(**item_data)

            # Handle photos if provided
            if photos:
                self._process_item_photos(item, photos)

            return item

    def create_item(
        self,
        _user: User,
        item_data: dict[str, Any],
    ) -> Jersey:
        """
        Backwards-compatible wrapper for creating an item.

        The _user parameter is accepted for future use but item creation
        is currently delegated directly to the repository.
        """
        return self.item_repository.create(**item_data)

    def update_item_with_photos(
        self,
        item_id: int,
        item_data: dict[str, Any],
        photos: list[Any] | None = None,
    ) -> Jersey | None:
        """
        Update an item with new photos.

        Args:
            item_id: ID of the item to update
            item_data: Dictionary containing updated item data
            photos: List of new photo files

        Returns:
            Updated item instance or None if not found
        """
        with transaction.atomic():
            # Update the item
            item = self.item_repository.update(item_id, **item_data)
            if not item:
                return None

            # Handle photos if provided
            if photos:
                self._process_item_photos(item, photos)

            return item

    def update_item(
        self,
        item: Jersey,
        item_data: dict[str, Any],
    ) -> Jersey | None:
        """
        Backwards-compatible wrapper for updating an item instance.
        """
        return self.item_repository.update(item.pk, **item_data)

    def delete_item_with_photos(self, item_id: int) -> bool:
        """
        Delete an item and all its associated photos.

        Args:
            item_id: ID of the item to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        with transaction.atomic():
            item = self.item_repository.get_by_id(item_id)
            if not item:
                return False

            # Delete all photos first
            self.photo_repository.delete_photos_by_item(item)

            # Delete the item
            return self.item_repository.delete(item_id)

    def get_user_items(self, user: User) -> QuerySet[BaseItem]:
        """
        Get all items for a user.

        Args:
            user: User instance

        Returns:
            QuerySet of user's items
        """
        return self.item_repository.get_user_items(user)

    def _build_collection_summary(self, user: User) -> dict[str, Any]:
        """
        Build the core collection summary analytics for a user.
        """
        items = self.item_repository.get_user_items(user)

        return {
            "total_items": items.count(),
            "by_type": self.item_repository.get_user_item_count_by_type(user),
            "by_condition": self._get_items_by_condition(items),
            "by_brand": self._get_items_by_brand(items),
            "by_club": self._get_items_by_club(items),
        }

    def get_user_geo_stats(self, user: User, top_limit: int = 10) -> dict[str, Any]:
        """
        Get per-user geo/brand/design/color statistics and top lists.
        """
        items = self.item_repository.get_user_items(user)

        if not items.exists():
            return self._build_empty_geo_stats()

        summary_counts = self._build_geo_summary_counts(items)
        country_name_map = self._build_country_name_map()
        design_label_map = self._build_design_label_map()

        top_lists = self._build_geo_top_lists(
            items=items,
            top_limit=top_limit,
            country_name_map=country_name_map,
            design_label_map=design_label_map,
        )

        return {
            "summary_counts": summary_counts,
            **top_lists,
        }

    def _build_geo_summary_counts(self, items: QuerySet[BaseItem]) -> dict[str, int]:
        clubs_count = items.filter(club__isnull=False).values("club_id").distinct().count()
        countries_count = items.exclude(country__isnull=True).exclude(country="").values("country").distinct().count()
        competitions_count = items.filter(competitions__isnull=False).values("competitions__id").distinct().count()
        brands_count = items.filter(brand__isnull=False).values("brand_id").distinct().count()
        designs_count = items.exclude(design="").values("design").distinct().count()
        colors_count = items.filter(main_color__isnull=False).values("main_color_id").distinct().count()

        return {
            "clubs": clubs_count,
            "countries": countries_count,
            "competitions": competitions_count,
            "brands": brands_count,
            "designs": designs_count,
            "colors": colors_count,
        }

    def _build_country_name_map(self) -> dict[str, str]:
        if ItemService._COUNTRY_NAME_MAP is None:
            ItemService._COUNTRY_NAME_MAP = dict(countries)
        return ItemService._COUNTRY_NAME_MAP

    def _build_design_label_map(self) -> dict[str, str]:
        if ItemService._DESIGN_LABEL_MAP is None:
            ItemService._DESIGN_LABEL_MAP = dict(BaseItem.DESIGN_CHOICES)
        return ItemService._DESIGN_LABEL_MAP

    def _build_geo_top_lists(
        self,
        items: QuerySet,
        top_limit: int,
        country_name_map: dict[str, str],
        design_label_map: dict[str, str],
    ) -> dict[str, Any]:
        club_stats = (
            items.filter(club__isnull=False)
            .values(
                "club_id",
                "club__name",
                "club__slug",
                "club__logo_file",
                "club__logo",
                "club__logo_dark_file",
                "club__logo_dark",
            )
            .annotate(item_count=Count("id"))
            .order_by("-item_count", "club__name")[:top_limit]
        )
        country_stats = (
            items.exclude(country__isnull=True)
            .exclude(country="")
            .values("country")
            .annotate(item_count=Count("id"))
            .order_by("-item_count", "country")[:top_limit]
        )
        competition_stats = (
            items.filter(competitions__isnull=False)
            .values(
                "competitions__id",
                "competitions__name",
                "competitions__slug",
                "competitions__logo",
                "competitions__logo_dark",
            )
            .annotate(item_count=Count("id"))
            .order_by("-item_count", "competitions__name")[:top_limit]
        )
        brand_stats = (
            items.filter(brand__isnull=False)
            .values(
                "brand_id",
                "brand__name",
                "brand__slug",
                "brand__logo_file",
                "brand__logo",
                "brand__logo_dark_file",
                "brand__logo_dark",
            )
            .annotate(item_count=Count("id"))
            .order_by("-item_count", "brand__name")[:top_limit]
        )
        design_stats = (
            items.exclude(design="")
            .values("design")
            .annotate(item_count=Count("id"))
            .order_by("-item_count", "design")[:top_limit]
        )
        color_stats = (
            items.filter(main_color__isnull=False)
            .values(
                "main_color_id",
                "main_color__name",
                "main_color__hex_value",
            )
            .annotate(item_count=Count("id"))
            .order_by("-item_count", "main_color__name")[:top_limit]
        )

        top_clubs = [self._build_club_entry(row) for row in club_stats]
        top_countries = [self._build_country_entry(row, country_name_map) for row in country_stats]
        top_competitions = [self._build_competition_entry(row) for row in competition_stats]
        top_brands = [self._build_brand_entry(row) for row in brand_stats]
        top_designs = [self._build_design_entry(row, design_label_map) for row in design_stats]
        top_colors = [self._build_color_entry(row) for row in color_stats]

        return {
            "top_club": self._first_or_none(top_clubs),
            "top_country": self._first_or_none(top_countries),
            "top_competition": self._first_or_none(top_competitions),
            "top_brand": self._first_or_none(top_brands),
            "top_design": self._first_or_none(top_designs),
            "top_color": self._first_or_none(top_colors),
            "top_clubs": top_clubs,
            "top_countries": top_countries,
            "top_competitions": top_competitions,
            "top_brands": top_brands,
            "top_designs": top_designs,
            "top_colors": top_colors,
        }

    def _build_club_entry(self, raw: dict[str, Any]) -> dict[str, Any]:
        path = raw.get("club__logo_file")
        logo_url = default_storage.url(path) if path else (raw.get("club__logo") or "")
        path_dark = raw.get("club__logo_dark_file")
        logo_dark_url = default_storage.url(path_dark) if path_dark else (raw.get("club__logo_dark") or "")
        return {
            "label": raw.get("club__name") or "",
            "slug_or_code": raw.get("club__slug"),
            "count": raw.get("item_count", 0),
            "id": raw.get("club_id"),
            "logo_url": logo_url,
            "logo_dark_url": logo_dark_url,
        }

    def _build_country_entry(
        self,
        raw: dict[str, Any],
        country_name_map: dict[str, str],
    ) -> dict[str, Any]:
        code = raw.get("country")
        return {
            "label": country_name_map.get(code, code or ""),
            "slug_or_code": code,
            "count": raw.get("item_count", 0),
            "code": code,
        }

    def _build_competition_entry(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "label": raw.get("competitions__name") or "",
            "slug_or_code": raw.get("competitions__slug"),
            "count": raw.get("item_count", 0),
            "id": raw.get("competitions__id"),
            "logo_url": raw.get("competitions__logo") or "",
            "logo_dark_url": raw.get("competitions__logo_dark") or "",
        }

    def _build_brand_entry(self, raw: dict[str, Any]) -> dict[str, Any]:
        path = raw.get("brand__logo_file")
        logo_url = default_storage.url(path) if path else (raw.get("brand__logo") or "")
        path_dark = raw.get("brand__logo_dark_file")
        logo_dark_url = default_storage.url(path_dark) if path_dark else (raw.get("brand__logo_dark") or "")
        return {
            "label": raw.get("brand__name") or "",
            "slug_or_code": raw.get("brand__slug"),
            "count": raw.get("item_count", 0),
            "id": raw.get("brand_id"),
            "logo_url": logo_url,
            "logo_dark_url": logo_dark_url,
        }

    def _build_design_entry(
        self,
        raw: dict[str, Any],
        design_label_map: dict[str, str],
    ) -> dict[str, Any]:
        code = raw.get("design")
        return {
            "label": design_label_map.get(code, code or ""),
            "slug_or_code": code,
            "count": raw.get("item_count", 0),
            "code": code,
        }

    def _build_color_entry(self, raw: dict[str, Any]) -> dict[str, Any]:
        hex_val = raw.get("main_color__hex_value")
        if hex_val and not HEX_COLOR_RE.match(hex_val):
            hex_val = None
        return {
            "label": raw.get("main_color__name") or "",
            "slug_or_code": raw.get("main_color_id"),
            "count": raw.get("item_count", 0),
            "id": raw.get("main_color_id"),
            "hex_value": hex_val,
        }

    @staticmethod
    def _first_or_none(items_list: list[dict[str, Any]]) -> dict[str, Any] | None:
        return items_list[0] if items_list else None

    def _build_empty_geo_stats(self) -> dict[str, Any]:
        empty_counts = {
            "clubs": 0,
            "countries": 0,
            "competitions": 0,
            "brands": 0,
            "designs": 0,
            "colors": 0,
        }
        return {
            "summary_counts": empty_counts,
            "top_club": None,
            "top_country": None,
            "top_competition": None,
            "top_brand": None,
            "top_design": None,
            "top_color": None,
            "top_clubs": [],
            "top_countries": [],
            "top_competitions": [],
            "top_brands": [],
            "top_designs": [],
            "top_colors": [],
        }

    def get_user_collection_summary(self, user: User) -> dict[str, Any]:
        """
        Get a summary of the user's collection.

        Args:
            user: User instance

        Returns:
            Dictionary with collection summary
        """
        return {
            **self._build_collection_summary(user),
            "recent_items": self.item_repository.get_recent_items(limit=5, user=user),
        }

    def get_user_item_count(self, user: User) -> int:
        """
        Get total item count for a user.
        """
        return self.item_repository.get_user_items(user).count()

    def get_public_items(self) -> QuerySet[BaseItem]:
        """
        Get all public items.
        """
        return self.item_repository.get_public_items()

    def get_recent_items(self, limit: int = 5, user: User | None = None) -> QuerySet[BaseItem]:
        """
        Get recent items, optionally filtered by user.
        """
        return self.item_repository.get_recent_items(limit=limit, user=user)

    def get_user_item_count_by_type(self, user: User) -> dict[str, int]:
        """
        Get item count by type for a user.
        """
        return self.item_repository.get_user_item_count_by_type(user)

    def get_items_by_club(self, user: User) -> QuerySet[BaseItem]:
        """
        Get all items for a user ordered by club.
        """
        return self.item_repository.get_user_items(user).order_by("club__name", "-created_at")

    def get_items_by_season(self, user: User) -> QuerySet[BaseItem]:
        """
        Get all items for a user ordered by season.
        """
        return self.item_repository.get_user_items(user).order_by("season__name", "-created_at")

    def get_item_analytics(self, user: User) -> dict[str, Any]:
        """
        Get analytics for items in a user's collection.
        """
        return self._build_collection_summary(user)

    def search_items_advanced(
        self,
        query: str,
        user: User = None,
        filters: dict[str, Any] | None = None,
    ) -> QuerySet[Jersey]:
        """
        Advanced search for items with multiple filters.

        Args:
            query: Search query string
            user: Optional user to limit search to their items
            filters: Dictionary of additional filters

        Returns:
            QuerySet of matching items
        """
        items = self.item_repository.get_user_items(user) if user else self.item_repository.get_public_items()

        # Apply text search
        if query:
            items = self.item_repository.search_items(query, user)

        # Apply additional filters
        if filters:
            items = self._apply_filters(items, filters)

        return items

    def search_items(
        self,
        user: User | None,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> QuerySet[Jersey]:
        """
        Backwards-compatible search wrapper used by CollectionService.
        """
        return self.search_items_advanced(query=query, user=user, filters=filters)

    def reorder_item_photos(self, item_id: int, photo_orders: list[tuple[int, int]]) -> bool:
        """
        Reorder photos for an item.

        Args:
            item_id: ID of the item
            photo_orders: List of (photo_id, new_order) tuples

        Returns:
            True if successful, False otherwise
        """
        item = self.item_repository.get_by_id(item_id)
        if not item:
            return False

        return self.photo_repository.reorder_photos(item, photo_orders)

    def get_item_with_photos(self, item_id: int) -> Jersey | None:
        """
        Get an item with its photos.

        Args:
            item_id: ID of the item

        Returns:
            Item instance with photos or None if not found
        """
        item = self.item_repository.get_by_id(item_id)
        if item:
            # Add photos to the item
            item.photos_list = self.photo_repository.get_photos_by_item(item)
        return item

    def _process_item_photos(self, item: Jersey, photos: list[Any]) -> None:
        """
        Process and save photos for an item.

        Args:
            item: Item instance
            photos: List of photo files
        """
        for index, photo_file in enumerate(photos):
            self.photo_repository.create(
                image=photo_file,
                content_object=item,
                order=index,
                uploaded_by=item.user,
            )

    def _get_items_by_condition(self, items: QuerySet[Jersey]) -> dict[str, int]:
        """Get count of items by condition."""
        return dict(items.values("condition").annotate(count=Count("condition")).values_list("condition", "count"))

    def _get_items_by_brand(self, items: QuerySet[Jersey]) -> dict[str, int]:
        """Get count of items by brand."""
        return dict(items.values("brand__name").annotate(count=Count("brand")).values_list("brand__name", "count"))

    def _get_items_by_club(self, items: QuerySet[Jersey]) -> dict[str, int]:
        """Get count of items by club."""
        return dict(items.values("club__name").annotate(count=Count("club")).values_list("club__name", "count"))

    def _apply_filters(self, items: QuerySet[Jersey], filters: dict[str, Any]) -> QuerySet[Jersey]:
        """Apply additional filters to items queryset."""
        if "brand" in filters:
            items = items.filter(brand__name__icontains=filters["brand"])
        if "club" in filters:
            items = items.filter(club__name__icontains=filters["club"])
        if "condition" in filters:
            items = items.filter(condition=filters["condition"])
        if "is_draft" in filters:
            items = items.filter(is_draft=filters["is_draft"])
        if "is_private" in filters:
            items = items.filter(is_private=filters["is_private"])
        if filters.get("fit"):
            items = items.filter(fit=filters["fit"])

        return items
