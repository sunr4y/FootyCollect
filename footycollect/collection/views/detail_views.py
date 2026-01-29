import logging

from footycollect.collection.services import get_photo_service

from .base import BaseItemDetailView

logger = logging.getLogger(__name__)


class ItemQuickViewView(BaseItemDetailView):
    """Quick view modal for item details."""

    template_name = "collection/item_quick_view.html"

    def get_queryset(self):
        """Get queryset with optimizations for quick view."""
        from django.db.models import Q

        from footycollect.collection.models import Jersey

        queryset = Jersey.objects.select_related(
            "base_item",
            "base_item__user",
            "base_item__club",
            "base_item__season",
            "base_item__brand",
            "base_item__main_color",
            "size",
            "kit",
            "kit__type",
        ).prefetch_related(
            "base_item__competitions",
            "base_item__photos",
            "base_item__secondary_colors",
        )

        if self.request.user.is_authenticated:
            queryset = queryset.filter(
                Q(base_item__user=self.request.user) | Q(base_item__is_private=False, base_item__is_draft=False)
            )
        else:
            queryset = queryset.filter(base_item__is_private=False, base_item__is_draft=False)

        return queryset

    def get_object(self, queryset=None):
        """Override to handle BaseItem pk lookup in Jersey queryset."""
        from django.http import Http404
        from django.utils.translation import gettext as _

        if queryset is None:
            queryset = self.get_queryset()

        pk = self.kwargs.get(self.pk_url_kwarg)
        if pk is not None:
            queryset = queryset.filter(base_item__pk=pk)

        try:
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            verbose_name = queryset.model._meta.verbose_name
            raise Http404(
                _("No %(verbose_name)s found matching the query") % {"verbose_name": verbose_name},
            ) from None

        return obj

    def get_context_data(self, **kwargs):
        """Add additional context data for quick view."""
        from django.views.generic.detail import SingleObjectMixin

        from footycollect.collection.models import BaseItem

        context = super(SingleObjectMixin, self).get_context_data(**kwargs)

        photo_service = get_photo_service()

        if isinstance(self.object, BaseItem):
            base_item = self.object
            context["specific_item"] = self.object.get_specific_item()
        else:
            base_item = self.object.base_item
            context["specific_item"] = self.object

        photos = photo_service.get_item_photos(base_item)
        context["photos"] = list(photos)
        context["object"] = base_item
        context["item"] = base_item

        return context


class ItemDetailView(BaseItemDetailView):
    """Detail view for a specific item in the collection."""

    template_name = "collection/item_detail.html"

    def get_queryset(self):
        """Get queryset with optimizations for detail view."""
        from django.db.models import Q

        from footycollect.collection.models import Jersey

        return (
            Jersey.objects.filter(
                Q(base_item__user=self.request.user) | Q(base_item__is_private=False, base_item__is_draft=False)
            )
            .select_related(
                "base_item",
                "base_item__user",
                "base_item__club",
                "base_item__season",
                "base_item__brand",
                "base_item__main_color",
                "size",
                "kit",
            )
            .prefetch_related(
                "base_item__competitions",
                "base_item__photos",
                "base_item__secondary_colors",
            )
        )

    def get_object(self, queryset=None):
        """Override to handle BaseItem pk lookup in Jersey queryset."""
        from django.http import Http404
        from django.utils.translation import gettext as _

        if queryset is None:
            queryset = self.get_queryset()

        pk = self.kwargs.get(self.pk_url_kwarg)
        if pk is not None:
            queryset = queryset.filter(base_item__pk=pk)

        try:
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            verbose_name = queryset.model._meta.verbose_name
            raise Http404(
                _("No %(verbose_name)s found matching the query") % {"verbose_name": verbose_name},
            ) from None

        return obj

    def get_context_data(self, **kwargs):
        """Add additional context data for the item detail."""
        from django.views.generic.detail import SingleObjectMixin

        from footycollect.collection.models import BaseItem

        context = super(SingleObjectMixin, self).get_context_data(**kwargs)

        photo_service = get_photo_service()

        if isinstance(self.object, BaseItem):
            base_item = self.object
            context["specific_item"] = self.object.get_specific_item()
        else:
            base_item = self.object.base_item
            context["specific_item"] = self.object

        photos = photo_service.get_item_photos(base_item)

        photos_list = list(photos)
        context["photos"] = photos_list

        context["object"] = base_item
        context["item"] = base_item

        logger.info(
            "ItemDetailView: base_item ID=%s, photos count=%d, photos_list=%s",
            base_item.id,
            len(photos_list),
            [p.id for p in photos_list],
        )

        related_items = self._get_related_items()
        context["related_items"] = related_items
        return context

    def _get_related_items(self):
        """Get related items from all item types with optimized queries."""
        from footycollect.collection.models import BaseItem, Jersey

        base_item = self.object if isinstance(self.object, BaseItem) else self.object.base_item

        if not base_item.club:
            return []

        related_base_items = (
            BaseItem.objects.filter(club=base_item.club)
            .exclude(id=base_item.id)
            .select_related("club", "season", "brand", "user", "main_color")
            .prefetch_related(
                "competitions",
                "photos",
                "jersey",
                "shorts",
                "outerwear",
                "tracksuit",
                "pants",
                "otheritem",
            )
            .order_by("-created_at")[:5]
        )

        jersey_ids = [item.id for item in related_base_items if item.item_type == "jersey"]
        jerseys = {}
        if jersey_ids:
            jerseys = {
                jersey.base_item_id: jersey
                for jersey in Jersey.objects.filter(base_item_id__in=jersey_ids).select_related(
                    "base_item",
                    "size",
                    "kit",
                    "kit__type",
                )
            }

        related_items = []
        for related_base_item in related_base_items:
            if related_base_item.item_type == "jersey" and related_base_item.id in jerseys:
                related_items.append(jerseys[related_base_item.id])
            else:
                specific_item = related_base_item.get_specific_item()
                if specific_item:
                    related_items.append(specific_item)

        return related_items


__all__ = [
    "ItemDetailView",
    "ItemQuickViewView",
]
