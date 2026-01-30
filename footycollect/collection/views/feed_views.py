"""
Feed views for displaying global kits feed with filtering capabilities.
"""

from django.db.models import QuerySet
from django.views.generic import ListView

from footycollect.collection.models import Jersey
from footycollect.collection.services.feed_service import FeedFilterService


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

    def get_context_data(self, **kwargs):  # noqa: C901, PLR0912, PLR0915
        """Add filter state and other context data."""
        context = super().get_context_data(**kwargs)

        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            context["is_ajax"] = True

        filter_service = FeedFilterService()
        filters = filter_service.parse_filters_from_request(self.request)
        sort_type = self.request.GET.get("sort", "random")

        context["active_filters"] = filters
        context["sort_type"] = sort_type
        filter_count = len([v for v in filters.values() if v and v != "" and (not isinstance(v, list) or len(v) > 0)])
        context["filter_count"] = filter_count

        from footycollect.collection.models import Color
        from footycollect.core.models import Brand, Club, TypeK

        context["kit_type_choices"] = TypeK.objects.filter(category="match").values_list("name", flat=True).distinct()
        context["category_choices"] = [choice[0] for choice in TypeK._meta.get_field("category").choices]

        colors = Color.objects.all().order_by("name")
        color_choices_list = [
            {"value": str(color.id), "label": color.name, "hex_value": color.hex_value or "#000000"}
            for color in colors
        ]
        import json

        context["color_choices_json"] = json.dumps(color_choices_list)

        filter_display_names = {}
        if filters.get("club"):
            filter_display_names["club"] = filters["club"]

        if filters.get("brand"):
            filter_display_names["brand"] = filters["brand"]

        if filters.get("competition"):
            filter_display_names["competition"] = filters["competition"]

        if filters.get("main_color"):
            try:
                color_id = int(filters["main_color"])
                color = Color.objects.filter(id=color_id).first()
                if color:
                    filter_display_names["main_color"] = color.name
            except (ValueError, TypeError):
                pass

        if filters.get("secondary_color"):
            try:
                if isinstance(filters["secondary_color"], str) and filters["secondary_color"]:
                    color_ids = [int(c.strip()) for c in filters["secondary_color"].split(",") if c.strip().isdigit()]
                    if color_ids:
                        colors = Color.objects.filter(id__in=color_ids).values_list("name", flat=True)
                        filter_display_names["secondary_color"] = list(colors)
            except (ValueError, TypeError):
                pass

        context["filter_display_names"] = filter_display_names

        import json

        autocomplete_initial_data = {}
        if filters.get("club"):
            try:
                club_id = int(filters["club"])
                club = Club.objects.filter(id=club_id).first()
                if club:
                    autocomplete_initial_data["club"] = {
                        "id": club.id,
                        "name": club.name,
                        "logo": club.logo_display_url or "",
                    }
            except (ValueError, TypeError):
                pass

        if filters.get("brand"):
            try:
                brand_id = int(filters["brand"])
                brand = Brand.objects.filter(id=brand_id).first()
                if brand:
                    autocomplete_initial_data["brand"] = {
                        "id": brand.id,
                        "name": brand.name,
                        "logo": brand.logo_display_url or "",
                    }
            except (ValueError, TypeError):
                pass

        context["autocomplete_initial_data"] = json.dumps(autocomplete_initial_data)

        return context
