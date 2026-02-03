"""
Feed views for displaying global kits feed with filtering capabilities.
"""

import json

from django.db.models import QuerySet
from django.views.generic import ListView

from footycollect.collection.models import Jersey
from footycollect.collection.services.feed_service import FeedFilterService


def _get_feed_filter_choices():
    from footycollect.collection.models import Color
    from footycollect.collection.utils_i18n import get_color_display_name
    from footycollect.core.models import TypeK

    kit_type_choices = list(TypeK.objects.filter(category="match").values_list("name", flat=True).distinct())
    category_choices = [choice[0] for choice in TypeK._meta.get_field("category").choices]
    colors = Color.objects.all().order_by("name")
    color_choices_list = [
        {"value": str(c.id), "label": get_color_display_name(c.name), "hex_value": c.hex_value or "#000000"}
        for c in colors
    ]
    return {
        "kit_type_choices": kit_type_choices,
        "category_choices": category_choices,
        "color_choices_json": json.dumps(color_choices_list),
    }


def _main_color_display(main_color_value):
    from footycollect.collection.models import Color
    from footycollect.collection.utils_i18n import get_color_display_name

    try:
        color = Color.objects.filter(id=int(main_color_value)).first()
        return get_color_display_name(color.name) if color else None
    except (ValueError, TypeError):
        return None


def _secondary_color_display(secondary_color_value):
    from footycollect.collection.models import Color
    from footycollect.collection.utils_i18n import get_color_display_name

    try:
        if not isinstance(secondary_color_value, str) or not secondary_color_value:
            return None
        ids = [int(x.strip()) for x in secondary_color_value.split(",") if x.strip().isdigit()]
        if not ids:
            return None
        return [get_color_display_name(c.name) for c in Color.objects.filter(id__in=ids).order_by("name")]
    except (ValueError, TypeError):
        return None


def _build_filter_display_names(filters):
    from django.utils.translation import gettext as _

    out = {}
    if filters.get("club"):
        out["club"] = filters["club"]
    if filters.get("brand"):
        out["brand"] = filters["brand"]
    if filters.get("competition"):
        out["competition"] = filters["competition"]
    main = _main_color_display(filters.get("main_color"))
    if main is not None:
        out["main_color"] = main
    sec = _secondary_color_display(filters.get("secondary_color"))
    if sec is not None:
        out["secondary_color"] = sec
    if filters.get("has_nameset"):
        out["has_nameset"] = _("Has nameset")
    return out


def _build_autocomplete_initial_data(filters):
    from footycollect.core.models import Brand, Club

    out = {}
    if filters.get("club"):
        try:
            club = Club.objects.filter(id=int(filters["club"])).first()
            if club:
                out["club"] = {"id": club.id, "name": club.name, "logo": club.logo_display_url or ""}
        except (ValueError, TypeError):
            pass
    if filters.get("brand"):
        try:
            brand = Brand.objects.filter(id=int(filters["brand"])).first()
            if brand:
                out["brand"] = {"id": brand.id, "name": brand.name, "logo": brand.logo_display_url or ""}
        except (ValueError, TypeError):
            pass
    return out


class FeedView(ListView):
    """View for displaying global kits feed with advanced filtering."""

    model = Jersey
    template_name = "collection/feed.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self) -> QuerySet[Jersey]:
        """
        Get queryset of public jerseys with optimizations.

        Returns:
            QuerySet of public Jersey objects
        """
        queryset = (
            Jersey.objects.filter(base_item__is_private=False, base_item__is_draft=False)
            .select_related(
                "base_item",
                "base_item__user",
                "base_item__club",
                "base_item__season",
                "base_item__brand",
                "base_item__main_color",
                "size",
                "kit",
                "kit__type",
            )
            .prefetch_related(
                "base_item__competitions",
                "base_item__photos",
                "base_item__secondary_colors",
            )
        )

        filter_service = FeedFilterService()
        filters = filter_service.parse_filters_from_request(self.request)
        queryset = filter_service.apply_filters(queryset, filters)

        sort_type = self.request.GET.get("sort", "random")

        if sort_type == "random":
            import hashlib

            filter_str = str(sorted(filters.items())) + str(sort_type)
            seed_hash = int(hashlib.sha256(filter_str.encode()).hexdigest()[:8], 16) % 2147483647
            if seed_hash == 0:
                seed_hash = 123456789

            seed_key = f"feed_random_seed_{hashlib.sha256(filter_str.encode()).hexdigest()[:8]}"

            if not self.request.session.get(seed_key):
                self.request.session[seed_key] = seed_hash
                session_seed = seed_hash
            else:
                session_seed = self.request.session[seed_key]

            return filter_service.apply_sorting(queryset, sort_type, seed=session_seed)

        return filter_service.apply_sorting(queryset, sort_type)

    def get_context_data(self, **kwargs):
        """Add filter state and other context data."""
        context = super().get_context_data(**kwargs)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            context["is_ajax"] = True

        filter_service = FeedFilterService()
        filters = filter_service.parse_filters_from_request(self.request)
        sort_type = self.request.GET.get("sort", "random")

        context["active_filters"] = filters
        context["sort_type"] = sort_type
        context["filter_count"] = sum(
            1 for v in filters.values() if v and v != "" and (not isinstance(v, list) or len(v) > 0)
        )

        choices = _get_feed_filter_choices()
        context["kit_type_choices"] = choices["kit_type_choices"]
        context["category_choices"] = choices["category_choices"]
        context["color_choices_json"] = choices["color_choices_json"]

        context["filter_display_names"] = _build_filter_display_names(filters)
        context["autocomplete_initial_data"] = json.dumps(_build_autocomplete_initial_data(filters))

        return context
