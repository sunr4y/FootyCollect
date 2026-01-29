import logging

from footycollect.collection.cache_utils import (
    ITEM_LIST_CACHE_TIMEOUT,
    get_item_list_cache_key,
    increment_item_list_cache_metric,
    track_item_list_cache_key,
)

from .base import BaseItemListView

logger = logging.getLogger(__name__)


class ItemListView(BaseItemListView):
    """List view for all items in the user's collection."""

    template_name = "collection/item_list.html"

    def _has_messages(self, request):
        """
        Safely determine if there are any messages attached to this request.

        This helper is careful to avoid *iterating* over the storage so that
        messages are not consumed before templates render them. It also tries
        multiple strategies to work across different storage backends and
        Django versions.
        """
        from django.contrib.messages import get_messages

        storage = get_messages(request)

        if hasattr(storage, "_queued_messages") and storage._queued_messages:  # noqa: SLF001
            return True

        if hasattr(storage, "_loaded_data") and storage._loaded_data:  # noqa: SLF001
            return True

        if hasattr(request, "session"):
            storage_key = getattr(storage, "storage_key", None) or getattr(
                storage,
                "_storage_key",
                None,
            )
            if storage_key and request.session.get(storage_key):
                return True
            if request.session.get("django.contrib.messages", []):
                return True

        return False

    def get(self, request, *args, **kwargs):
        from django.core.cache import cache

        if not request.user.is_authenticated:
            return super().get(request, *args, **kwargs)

        page = request.GET.get("page", "1")
        cache_key = get_item_list_cache_key(request.user.pk, page)

        has_messages = self._has_messages(request)

        if not has_messages:
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                logger.info("ItemListView cache hit for user %s page %s", request.user.pk, page)
                track_item_list_cache_key(request.user.pk, cache_key)
                increment_item_list_cache_metric(is_hit=True)
                return cached_response

        response = super().get(request, *args, **kwargs)
        response.render()

        if not has_messages:
            cache.set(cache_key, response, ITEM_LIST_CACHE_TIMEOUT)
            track_item_list_cache_key(request.user.pk, cache_key)
            increment_item_list_cache_metric(is_hit=False)
            logger.info("ItemListView cache miss; cached response for user %s page %s", request.user.pk, page)
        else:
            logger.info("ItemListView skipping cache due to messages for user %s page %s", request.user.pk, page)
            increment_item_list_cache_metric(is_hit=False)

        return response

    def get_queryset(self):
        """Get all items for the current user with optimizations."""
        from footycollect.collection.models import Jersey

        return (
            Jersey.objects.filter(base_item__user=self.request.user)
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
            .order_by("-base_item__created_at")
        )


__all__ = [
    "ItemListView",
]
