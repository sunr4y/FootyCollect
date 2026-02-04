"""
CRUD views for collection items.

ItemCreateView, ItemUpdateView, ItemDeleteView with photo and form context handling.
"""

import json
import logging

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse_lazy
from django.utils.translation import gettext as _

from footycollect.collection.cache_utils import invalidate_item_list_cache_for_user
from footycollect.collection.forms import JerseyForm
from footycollect.collection.models import Jersey, Photo

from .base import (
    URL_NAME_ITEM_LIST,
    BaseItemCreateView,
    BaseItemDeleteView,
    BaseItemUpdateView,
    get_color_and_design_choices,
)

logger = logging.getLogger(__name__)


class ItemCreateView(BaseItemCreateView):
    """Create view for adding new items to the collection."""

    template_name = "collection/item_form.html"
    success_url = reverse_lazy(URL_NAME_ITEM_LIST)

    def get_form_class(self):
        """Return the appropriate form class based on the item type."""
        return JerseyForm

    def get_context_data(self, **kwargs):
        """Add context data for item creation."""
        context = super().get_context_data(**kwargs)
        context.update(get_color_and_design_choices())
        return context


class ItemUpdateView(BaseItemUpdateView):
    """Update view for editing existing items in the collection."""

    template_name = "collection/item_form.html"
    success_url = reverse_lazy(URL_NAME_ITEM_LIST)

    def form_valid(self, form):
        """Handle form validation for item updates, including photo processing."""
        response = super().form_valid(form)
        photo_ids = self.request.POST.get("photo_ids", "")
        if photo_ids:
            parsed = self._parse_photo_ids(photo_ids)
            if parsed is not None:
                keep_ids, order_map, _ = self._extract_photo_data(parsed)
                self._update_existing_photos(keep_ids, order_map)
                self._remove_deleted_photos(keep_ids)
        return response

    def _parse_photo_ids(self, photo_ids):
        """Parse photo_ids JSON payload."""
        try:
            parsed = json.loads(photo_ids)
        except (TypeError, ValueError):
            logger.warning("Invalid photo_ids payload for ItemUpdateView (length=%s)", len(photo_ids))
            return None

        if not isinstance(parsed, list):
            logger.warning("Unexpected photo_ids structure for ItemUpdateView (non-list)")
            return None

        return parsed

    def _extract_photo_data(self, parsed):
        """Extract keep_ids, order_map, and external_images from parsed payload."""
        keep_ids: set[int] = set()
        order_map: dict[int, int] = {}
        external_images: list[dict] = []

        for item in parsed:
            if not isinstance(item, dict):
                continue

            photo_id = item.get("id")
            order = item.get("order", 0)
            is_external = item.get("external", False)
            url = item.get("url")

            if is_external and url:
                external_images.append({"url": url, "order": order})
            elif photo_id:
                try:
                    pid_int = int(photo_id)
                    keep_ids.add(pid_int)
                    order_map[pid_int] = order
                except (TypeError, ValueError):
                    continue

        return keep_ids, order_map, external_images

    def _update_existing_photos(self, keep_ids, order_map):
        """Attach existing photos and update their order."""
        if not keep_ids:
            return

        photos = Photo.objects.filter(id__in=keep_ids, user=self.request.user)
        content_type = ContentType.objects.get_for_model(self.object)

        for photo in photos:
            photo.content_type = content_type
            photo.object_id = self.object.id
            if photo.id in order_map:
                photo.order = order_map[photo.id]
            photo.save()

    def _remove_deleted_photos(self, keep_ids):
        """Remove photos that were not included in the payload (user deleted them)."""
        try:
            existing_photos = self.object.photos.filter(user=self.request.user)
            photos_to_delete = existing_photos.exclude(id__in=keep_ids) if keep_ids else existing_photos

            if photos_to_delete.exists():
                photos_to_delete.delete()
        except (OSError, AttributeError):
            logger.exception("Error cleaning up removed photos in ItemUpdateView")

    def get_form_class(self):
        """Return the appropriate form class based on the item type."""
        if isinstance(self.object, Jersey):
            return JerseyForm
        return JerseyForm

    def get_context_data(self, **kwargs):
        """Add context data for item update."""
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True

        self._add_color_and_design_choices(context)
        self._add_initial_photos(context)
        self._add_autocomplete_initial_data(context)

        return context

    def _add_color_and_design_choices(self, context):
        """Add color and design choices for Cotton components."""
        context.update(get_color_and_design_choices())
        return context

    def _add_initial_photos(self, context):
        """Pre-load existing photos for the photo manager."""
        try:
            photos = self.object.photos.order_by("order", "id")
            photo_list = [self._build_photo_dict(photo) for photo in photos]
            context["initial_photos"] = json.dumps(photo_list)
        except (AttributeError, ValueError, TypeError, OSError) as exc:
            logger.warning("Error building initial_photos for ItemUpdateView: %s", type(exc).__name__)
            context["initial_photos"] = "[]"

    def _build_photo_dict(self, photo):
        """Build a dictionary representation of a photo."""
        try:
            url = photo.get_image_url()
            thumbnail_url = getattr(photo.thumbnail, "url", None) or url
        except (AttributeError, ValueError):
            url = f"/media/item_photos/{photo.image.name}" if photo.image.name else ""
            thumbnail_url = url

        return {
            "id": photo.id,
            "url": url,
            "thumbnail_url": thumbnail_url,
            "order": photo.order,
            "uploading": False,
        }

    def _add_autocomplete_initial_data(self, context):
        """Pre-load initial values for autocomplete components."""
        try:
            base_item = self.get_object()
            kit = self._get_kit_from_base_item(base_item)

            initial_data = {
                "brand": self._get_entity_data(base_item, kit, "brand", "brand"),
                "club": self._get_entity_data(base_item, kit, "club", "team"),
                "season": self._get_season_data(base_item, kit),
                "competitions": self._get_competitions_data(base_item, kit),
            }
            initial_data = {k: v for k, v in initial_data.items() if v}

            context["autocomplete_initial_data"] = json.dumps(initial_data)
        except (AttributeError, ValueError, TypeError, KeyError) as e:
            logger.warning("Error building autocomplete initial data for ItemUpdateView: %s", type(e).__name__)
            context["autocomplete_initial_data"] = "{}"

    def _get_kit_from_base_item(self, base_item):
        """Try to get kit from base_item's jersey."""
        try:
            if hasattr(base_item, "jersey"):
                jersey = base_item.jersey
                if jersey and hasattr(jersey, "kit") and jersey.kit:
                    return jersey.kit
        except AttributeError:
            pass
        return None

    def _get_entity_data(self, base_item, kit, base_item_attr, kit_attr):
        """Get entity data (brand/club) from base_item or kit."""
        try:
            entity = getattr(base_item, base_item_attr, None)
            if entity:
                return {
                    "id": entity.id,
                    "name": entity.name,
                    "logo": getattr(entity, "logo", None) or "",
                }
        except AttributeError:
            pass

        if kit:
            try:
                entity = getattr(kit, kit_attr, None)
                if entity:
                    return {
                        "id": entity.id,
                        "name": entity.name,
                        "logo": getattr(entity, "logo", None) or "",
                    }
            except AttributeError:
                pass

        return None

    def _get_season_data(self, base_item, kit):
        """Get season data from base_item or kit."""
        try:
            season = base_item.season
            if season:
                return {"id": season.id, "name": season.year, "logo": ""}
        except AttributeError:
            pass

        if kit:
            try:
                season = kit.season
                if season:
                    return {"id": season.id, "name": season.year, "logo": ""}
            except AttributeError:
                pass

        return None

    def _get_competitions_data(self, base_item, kit):
        """Get competitions data from base_item or kit."""
        try:
            competitions = list(base_item.competitions.all())
            if competitions:
                return [
                    {"id": comp.id, "name": comp.name, "logo": getattr(comp, "logo", None) or ""}
                    for comp in competitions
                ]
        except AttributeError:
            pass

        if kit:
            try:
                competitions = list(kit.competition.all())
                if competitions:
                    return [
                        {"id": comp.id, "name": comp.name, "logo": getattr(comp, "logo", None) or ""}
                        for comp in competitions
                    ]
            except AttributeError:
                pass

        return None


class ItemDeleteView(BaseItemDeleteView):
    """Delete view for removing items from the collection."""

    template_name = "collection/item_confirm_delete.html"
    success_url = reverse_lazy(URL_NAME_ITEM_LIST)

    def get_success_url(self):
        """Return to the same page after deletion."""
        page = self.request.POST.get("page") or self.request.GET.get("page")
        base_url = reverse_lazy(URL_NAME_ITEM_LIST)
        if page and page != "1":
            return f"{base_url}?page={page}"
        return base_url

    success_message = _("Item and associated photos deleted successfully.")

    def delete(self, request, *args, **kwargs):
        """Override delete to handle photo cleanup."""
        item = self.get_object()

        photos = item.photos.all()
        for photo in photos:
            photo.delete()

        invalidate_item_list_cache_for_user(request.user.pk)

        return super().delete(request, *args, **kwargs)


__all__ = [
    "ItemCreateView",
    "ItemDeleteView",
    "ItemUpdateView",
]
