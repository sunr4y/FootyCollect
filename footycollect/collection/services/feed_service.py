"""
Service for feed filtering and sorting logic.

This service handles filtering and sorting operations for the global kits feed.
"""

from contextlib import suppress
from typing import Any

from django.db.models import F, Q, QuerySet
from django.db.models.functions import Mod

from footycollect.collection.models import Jersey


class FeedFilterService:
    """Service for filtering and sorting the global kits feed."""

    def apply_filters(  # noqa: C901, PLR0915
        self, queryset: QuerySet[Jersey], filters_dict: dict[str, Any]
    ) -> QuerySet[Jersey]:
        """
        Apply filters to a Jersey queryset.

        Args:
            queryset: Base Jersey queryset (public items only)
            filters_dict: Dictionary of filter parameters

        Returns:
            Filtered queryset
        """
        if not filters_dict:
            return queryset

        if "country" in filters_dict:
            country = filters_dict["country"]
            if country and str(country).strip():
                queryset = queryset.filter(Q(base_item__club__country=country) | Q(base_item__country=country))

        if "club" in filters_dict:
            club_value = filters_dict["club"]
            if club_value and str(club_value).strip():
                try:
                    club_id = int(club_value)
                    queryset = queryset.filter(base_item__club__id=club_id)
                except (ValueError, TypeError):
                    queryset = queryset.filter(base_item__club__slug=club_value)

        if "brand" in filters_dict:
            brand_value = filters_dict["brand"]
            if brand_value and str(brand_value).strip():
                try:
                    brand_id = int(brand_value)
                    queryset = queryset.filter(base_item__brand__id=brand_id)
                except (ValueError, TypeError):
                    queryset = queryset.filter(base_item__brand__slug=brand_value)

        if "season" in filters_dict:
            season = filters_dict["season"]
            queryset = queryset.filter(base_item__season__year=season)

        if "competition" in filters_dict:
            competitions = filters_dict["competition"]
            if competitions:
                if isinstance(competitions, list):
                    competitions = [c for c in competitions if c]
                    if competitions:
                        queryset = queryset.filter(base_item__competitions__id__in=competitions).distinct()
                else:
                    queryset = queryset.filter(base_item__competitions__id=competitions).distinct()

        if "kit_type" in filters_dict:
            kit_type_value = filters_dict["kit_type"]
            if kit_type_value and str(kit_type_value).strip():
                try:
                    kit_type_id = int(kit_type_value)
                    queryset = queryset.filter(kit__type__id=kit_type_id)
                except (ValueError, TypeError):
                    queryset = queryset.filter(kit__type__name__icontains=kit_type_value)

        if "category" in filters_dict:
            category = filters_dict["category"]
            if category and str(category).strip():
                queryset = queryset.filter(kit__type__category=category)

        if filters_dict.get("has_nameset"):
            queryset = queryset.filter(has_nameset=True)

        if "main_color" in filters_dict:
            main_color_value = filters_dict["main_color"]
            if main_color_value and str(main_color_value).strip():
                try:
                    color_id = int(str(main_color_value).strip())
                    queryset = queryset.filter(base_item__main_color__id=color_id)
                except (ValueError, TypeError):
                    pass

        if "secondary_color" in filters_dict:
            secondary_colors = filters_dict["secondary_color"]
            if isinstance(secondary_colors, list):
                queryset = queryset.filter(base_item__secondary_colors__id__in=secondary_colors).distinct()
            elif isinstance(secondary_colors, str) and secondary_colors:
                try:
                    color_ids = [int(c.strip()) for c in secondary_colors.split(",") if c.strip().isdigit()]
                    if color_ids:
                        queryset = queryset.filter(base_item__secondary_colors__id__in=color_ids).distinct()
                except (ValueError, TypeError):
                    try:
                        color_id = int(secondary_colors)
                        queryset = queryset.filter(base_item__secondary_colors__id=color_id).distinct()
                    except (ValueError, TypeError):
                        pass

        if "q" in filters_dict:
            search_query = filters_dict["q"]
            if search_query and str(search_query).strip():
                queryset = queryset.filter(
                    Q(base_item__name__icontains=search_query)
                    | Q(base_item__club__name__icontains=search_query)
                    | Q(base_item__brand__name__icontains=search_query)
                )

        return queryset

    def apply_sorting(
        self, queryset: QuerySet[Jersey], sort_type: str = "random", seed: int | None = None
    ) -> QuerySet[Jersey]:
        """
        Apply sorting to a Jersey queryset.

        Args:
            queryset: Jersey queryset to sort
            sort_type: Type of sorting ('random', 'newest', 'popular')
            seed: Optional seed for random ordering to ensure consistent pagination

        Returns:
            Sorted queryset
        """
        if seed is not None:
            try:
                seed = int(seed) % 2147483647
            except (ValueError, TypeError):
                seed = None

        if sort_type == "newest":
            return queryset.order_by("-base_item__created_at")
        if sort_type == "popular":
            if hasattr(queryset.model.base_item.related.related_model, "view_count"):
                return queryset.order_by("-base_item__view_count")
            if seed is not None:
                return queryset.annotate(random_order=Mod(F("base_item_id") * seed, 2147483647)).order_by(
                    "random_order"
                )
            return queryset.order_by("?")
        if seed is not None:
            return queryset.annotate(random_order=Mod(F("base_item_id") * seed, 2147483647)).order_by("random_order")
        return queryset.order_by("?")

    def parse_filters_from_request(self, request) -> dict[str, Any]:  # noqa: C901
        """
        Parse filter parameters from request.GET.

        Args:
            request: Django request object

        Returns:
            Dictionary of normalized filter parameters
        """
        filters: dict[str, Any] = {}

        country = request.GET.get("country")
        if country and country.strip():
            filters["country"] = country.upper()

        club = request.GET.get("club")
        if club and club.strip():
            filters["club"] = club

        brand = request.GET.get("brand")
        if brand and brand.strip():
            filters["brand"] = brand

        season = request.GET.get("season")
        if season and season.strip():
            filters["season"] = season

        competition = request.GET.getlist("competition")
        if not competition:
            competition_str = request.GET.get("competition")
            if competition_str:
                with suppress(ValueError, TypeError):
                    competition = [int(c.strip()) for c in competition_str.split(",") if c.strip()]
        if competition:
            with suppress(ValueError, TypeError):
                filters["competition"] = [int(c) for c in competition if c]

        kit_type = request.GET.get("kit_type")
        if kit_type and kit_type.strip():
            filters["kit_type"] = kit_type

        category = request.GET.get("category")
        if category and category.strip():
            filters["category"] = category

        has_nameset = request.GET.get("has_nameset")
        if has_nameset and str(has_nameset).lower() in ("1", "true", "on", "yes"):
            filters["has_nameset"] = True

        main_color = request.GET.get("main_color")
        if main_color and main_color.strip():
            filters["main_color"] = main_color.strip()

        secondary_color = request.GET.get("secondary_color")
        if secondary_color and secondary_color.strip():
            filters["secondary_color"] = secondary_color.strip()

        q = request.GET.get("q")
        if q and q.strip():
            filters["q"] = q.strip()

        return filters

    def build_filter_url(self, base_url: str, filters_dict: dict[str, Any]) -> str:
        """
        Build URL with query parameters from filter dictionary.

        Args:
            base_url: Base URL without query parameters
            filters_dict: Dictionary of filter parameters

        Returns:
            URL with query parameters
        """
        from urllib.parse import urlencode

        if not filters_dict:
            return base_url

        params: dict[str, Any] = {}
        for key, value in filters_dict.items():
            if value is None:
                continue
            if isinstance(value, str):
                if not value.strip():
                    continue
                params[key] = value.strip()
            elif isinstance(value, list):
                non_empty_values = [v for v in value if v is not None and str(v).strip()]
                if non_empty_values:
                    params[key] = non_empty_values
            else:
                str_value = str(value).strip()
                if str_value and str_value not in ("null", "undefined", ""):
                    params[key] = str_value

        if params:
            return f"{base_url}?{urlencode(params, doseq=True)}"
        return base_url
