"""
Item-specific views for the collection app.

This module contains views that handle CRUD operations for items
in the collection, such as jerseys, shirts, etc.
"""

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from footycollect.collection.cache_utils import (
    ITEM_LIST_CACHE_TIMEOUT,
    get_item_list_cache_key,
    increment_item_list_cache_metric,
    invalidate_item_list_cache_for_user,
    track_item_list_cache_key,
)
from footycollect.collection.forms import JerseyForm, TestBrandForm, TestCountryForm
from footycollect.collection.models import Jersey
from footycollect.collection.services import get_photo_service

from .base import BaseItemCreateView, BaseItemDeleteView, BaseItemDetailView, BaseItemListView, BaseItemUpdateView

logger = logging.getLogger(__name__)


# =============================================================================
# FUNCTION-BASED VIEWS
# =============================================================================


def demo_country_view(request):
    """Demo view for country form."""
    form = TestCountryForm()
    return render(request, "collection/test_country.html", {"form": form})


def demo_brand_view(request):
    """Demo view for brand form."""
    form = TestBrandForm()
    context = {"form": form}
    return render(request, "collection/test_brand.html", context)


def _load_home_kits():
    """Load and process home kits data from JSON file."""
    import json

    from django.conf import settings

    data_path = settings.APPS_DIR / "static" / "data" / "home_kits_data.json"

    try:
        with data_path.open() as f:
            data = json.load(f)
        kits = data.get("kits", [])
    except FileNotFoundError:
        logger.warning("Home kits data file not found: %s", data_path)
        return []
    except json.JSONDecodeError:
        logger.exception("Invalid JSON in home kits data file")
        return []

    # Resolve URLs based on storage configuration
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    use_cdn = media_url.startswith("http")

    for kit in kits:
        for path_key, fallback_key, url_key in [
            ("image_path", "original_image_url", "image_url"),
            ("team_logo_path", "original_team_logo", "team_logo"),
            ("brand_logo_path", "original_brand_logo", "brand_logo"),
            ("brand_logo_dark_path", "original_brand_logo_dark", "brand_logo_dark"),
        ]:
            if use_cdn and kit.get(path_key):
                kit[url_key] = f"{media_url.rstrip('/')}/{kit[path_key]}"
            else:
                kit[url_key] = kit.get(fallback_key, "")

    return kits


def _distribute_kits_to_columns(kits, num_columns, kits_per_column):
    """Distribute kits across columns, avoiding same club in same column."""
    import random

    if not kits:
        return [[] for _ in range(num_columns)]

    random.seed(42)
    available = kits.copy()
    random.shuffle(available)

    columns = [[] for _ in range(num_columns)]
    columns_teams = [set() for _ in range(num_columns)]

    for col_idx in range(num_columns):
        for kit in available[:]:
            if len(columns[col_idx]) >= kits_per_column:
                break
            team = kit.get("team_name", "") or kit.get("name", "").split()[0]
            if team not in columns_teams[col_idx]:
                columns[col_idx].append(kit)
                columns_teams[col_idx].add(team)
                available.remove(kit)

    # Triple for infinite scroll animation
    return [col * 3 for col in columns]


def home(request):
    """Home view with curated jersey cards from external API."""
    kits = _load_home_kits()
    columns_items = _distribute_kits_to_columns(kits, num_columns=8, kits_per_column=5)
    return render(request, "pages/home.html", {"columns_items": columns_items, "use_cached_kits": True})


def test_dropzone(request):
    """Independent test view for Dropzone."""
    return render(request, "collection/dropzone_test_page.html")


def image_display_test(request):
    """Test view for comparing different image display solutions."""
    from footycollect.collection.services import get_item_service

    if request.user.is_authenticated:
        item_service = get_item_service()
        items = list(item_service.get_user_items(request.user)[:12])  # Limitar a 12 items para la prueba
    else:
        items = []

    context = {
        "items": items,
    }
    return render(request, "collection/image_display_test.html", context)


# =============================================================================
# CLASS-BASED VIEWS
# =============================================================================


class PostCreateView(LoginRequiredMixin, View):
    """View for creating posts with file uploads."""

    template_name = "collection/item_create.html"
    form_class = JerseyForm
    success_url = reverse_lazy("collection:item_list")
    success_message = _("Item created successfully")

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        """Override post to log POST requests."""
        logger.info("=== POST METHOD CALLED ===")
        logger.info("POST data keys: %s", list(request.POST.keys()))
        logger.info("FILES data keys: %s", list(request.FILES.keys()))
        logger.info("CSRF token in POST: %s", "csrfmiddlewaretoken" in request.POST)
        logger.info("Content type: %s", request.content_type)
        logger.info("Request META keys: %s", list(request.META.keys()))

        # Log some POST data (be careful with sensitive data)
        for key, value in request.POST.items():
            if key != "csrfmiddlewaretoken":
                logger.info("POST %s: %s", key, value)

        form = self.form_class(request.POST)
        if form.is_valid():
            # Use service to create item with photos
            photo_service = get_photo_service()

            # Create item
            new_item = form.save(commit=False)
            new_item.base_item.user = request.user
            new_item.base_item.save()
            new_item.save()
            # No need for save_m2m() as JerseyForm doesn't have many-to-many fields

            # Process uploaded files using service
            photo_files = request.FILES.getlist("images")
            if photo_files:
                photo_service.create_photos_for_item(new_item, photo_files)

            messages.success(request, self.success_message)
            return JsonResponse(
                {
                    "url": reverse(
                        "collection:item_detail",
                        kwargs={"pk": new_item.pk},
                    ),
                },
            )

        return JsonResponse(
            {
                "error": form.errors.as_json(),
                "url": str(self.success_url),
            },
            status=400,
        )


class DropzoneTestView(TemplateView):
    """Template view for testing Dropzone functionality."""

    template_name = "collection/dropzone_test_page.html"


class JerseySelectView(LoginRequiredMixin, TemplateView):
    """View for browsing and selecting kit templates from the database."""

    template_name = "collection/jersey_select.html"

    # Performance optimization fields
    select_related_fields = ["user"]
    prefetch_related_fields = []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["help_text"] = _(
            "Browse available kit templates in our database. "
            "A 'kit' is the design/template (e.g., 'FC Barcelona 2020-21 Home Kit'). "
            "After selecting a kit, you'll add details about your specific physical item "
            "(size, condition, player name, photos, etc.). Multiple users can own the same kit "
            "but with different customizations!",
        )
        return context


# =============================================================================
# BASE ITEM VIEWS
# =============================================================================


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

        # Most Django backends keep queued messages in a private attribute.
        # Accessing it here is intentional so we can avoid consuming the
        # iterator. We mark it with noqa because this is a controlled use of
        # internals for performance/correctness.
        if hasattr(storage, "_queued_messages") and storage._queued_messages:  # noqa: SLF001
            return True

        # Some storage implementations keep data in a loaded/temporary buffer.
        if hasattr(storage, "_loaded_data") and storage._loaded_data:  # noqa: SLF001
            return True

        # As an additional safeguard, inspect the session directly using the
        # storage's own key when available.
        if hasattr(request, "session"):
            storage_key = getattr(storage, "storage_key", None) or getattr(
                storage,
                "_storage_key",
                None,
            )
            if storage_key and request.session.get(storage_key):
                return True
            # Fallback to the default key used by contrib.messages
            if request.session.get("django.contrib.messages", []):
                return True

        # If none of the above checks found messages, it's reasonable to treat
        # this request as message-free.
        return False

    def get(self, request, *args, **kwargs):
        from django.core.cache import cache

        if not request.user.is_authenticated:
            return super().get(request, *args, **kwargs)

        page = request.GET.get("page", "1")
        cache_key = get_item_list_cache_key(request.user.pk, page)

        # Check if there are messages in this request BEFORE checking cache.
        # Messages are request-specific and require fresh rendering. We use a
        # helper that avoids consuming the storage and is defensive across
        # different storage backends.
        has_messages = self._has_messages(request)

        # Only check cache if we're sure there are no messages
        if not has_messages:
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                logger.info("ItemListView cache hit for user %s page %s", request.user.pk, page)
                track_item_list_cache_key(request.user.pk, cache_key)
                increment_item_list_cache_metric(is_hit=True)
                return cached_response

        # Render fresh response (cache miss or messages present)
        response = super().get(request, *args, **kwargs)
        response.render()

        # Only cache responses that don't have messages
        # (Messages are transient and request-specific)
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

        # Get photos using the service (which uses the correct ContentType)
        photos = photo_service.get_item_photos(base_item)

        # Force evaluation of the queryset to ensure it's cached and available
        photos_list = list(photos)
        context["photos"] = photos_list

        # Ensure object is base_item so GenericRelation works in template
        context["object"] = base_item
        context["item"] = base_item

        # Log for debugging
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            "ItemDetailView: base_item ID=%s, photos count=%d, photos_list=%s",
            base_item.id,
            len(photos_list),
            [p.id for p in photos_list],
        )

        # Get related items from all item types
        related_items = self._get_related_items()
        context["related_items"] = related_items
        return context

    def _get_related_items(self):
        """Get related items from all item types with optimized queries."""
        from footycollect.collection.models import BaseItem, Jersey

        base_item = self.object if isinstance(self.object, BaseItem) else self.object.base_item

        if not base_item.club:
            return []

        # Optimized: Query BaseItem directly and get specific items via select_related
        # Since most items are jerseys, we'll optimize for that case
        # For other item types, we'll use a more generic approach
        related_base_items = (
            BaseItem.objects.filter(club=base_item.club)
            .exclude(id=base_item.id)
            .select_related("club", "season", "brand", "user", "main_color")
            .prefetch_related("competitions", "photos")
            .order_by("-created_at")[:5]
        )

        # Optimize: Prefetch Jersey objects for jersey items to avoid N+1
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

        # Get specific item instances efficiently
        related_items = []
        for related_base_item in related_base_items:
            if related_base_item.item_type == "jersey" and related_base_item.id in jerseys:
                related_items.append(jerseys[related_base_item.id])
            else:
                # For non-jersey items, use get_specific_item (will do one query per item)
                specific_item = related_base_item.get_specific_item()
                if specific_item:
                    related_items.append(specific_item)

        return related_items


class ItemCreateView(BaseItemCreateView):
    """Create view for adding new items to the collection."""

    template_name = "collection/item_form.html"
    success_url = reverse_lazy("collection:item_list")

    def get_form_class(self):
        """Return the appropriate form class based on the item type."""
        item_type = self.request.GET.get("type", "jersey")
        if item_type == "jersey":
            return JerseyForm
        # Add other form types as needed
        return JerseyForm

    def get_context_data(self, **kwargs):
        """Add context data for item creation."""
        context = super().get_context_data(**kwargs)

        # Add options for Cotton components using services
        try:
            import json

            from footycollect.collection.models import BaseItem
            from footycollect.collection.services import get_collection_service

            collection_service = get_collection_service()
            form_data = collection_service.get_form_data()
            context["color_choices"] = json.dumps(form_data["colors"]["main_colors"])
            context["design_choices"] = json.dumps(
                [{"value": d[0], "label": str(d[1])} for d in BaseItem.DESIGN_CHOICES],
            )
        except (KeyError, AttributeError, ImportError) as e:
            logger.warning("Error getting form data: %s", str(e))
            context["color_choices"] = "[]"
            context["design_choices"] = "[]"

        return context


class ItemUpdateView(BaseItemUpdateView):
    """Update view for editing existing items in the collection."""

    template_name = "collection/item_form.html"
    success_url = reverse_lazy("collection:item_list")

    def form_valid(self, form):
        """
        Handle form validation for item updates, including photo processing.

        This method:
        - associates uploaded photos from the Cotton photo manager
        - applies the current ordering
        - removes photos that were deleted in the UI
        """
        response = super().form_valid(form)

        photo_ids = self.request.POST.get("photo_ids", "")
        if not photo_ids:
            return response

        parsed = self._parse_photo_ids(photo_ids)
        if parsed is None:
            return response

        keep_ids, order_map, external_images = self._extract_photo_data(parsed)

        self._update_existing_photos(keep_ids, order_map)
        self._remove_deleted_photos(keep_ids)

        if external_images:
            logger.info("Ignoring external images on edit (not implemented): %s", external_images)

        return response

    def _parse_photo_ids(self, photo_ids):
        """Parse photo_ids JSON payload."""
        import json

        try:
            parsed = json.loads(photo_ids)
        except (TypeError, ValueError, json.JSONDecodeError):
            logger.warning("Invalid photo_ids payload for ItemUpdateView: %s", photo_ids)
            return None

        if not isinstance(parsed, list):
            logger.warning("Unexpected photo_ids structure for ItemUpdateView: %s", type(parsed))
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

        from django.contrib.contenttypes.models import ContentType

        from footycollect.collection.models import Photo

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
        # Add other form types as needed
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
        import json

        from footycollect.collection.models import BaseItem
        from footycollect.collection.services import get_collection_service

        try:
            collection_service = get_collection_service()
            form_data = collection_service.get_form_data()
            context["color_choices"] = json.dumps(form_data["colors"]["main_colors"])
            context["design_choices"] = json.dumps(
                [{"value": d[0], "label": str(d[1])} for d in BaseItem.DESIGN_CHOICES],
            )
        except (KeyError, AttributeError, ImportError) as e:
            logger.warning("Error getting form data: %s", str(e))
            context["color_choices"] = "[]"
            context["design_choices"] = "[]"

    def _add_initial_photos(self, context):
        """Pre-load existing photos for the photo manager."""
        import json

        try:
            photos = self.object.photos.order_by("order", "id")
            photo_list = [self._build_photo_dict(photo) for photo in photos]
            context["initial_photos"] = json.dumps(photo_list)
        except (AttributeError, ValueError, TypeError, OSError) as exc:
            logger.warning("Error building initial_photos for ItemUpdateView: %s", str(exc))
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
        import json

        try:
            base_item = self.get_object()
            kit = self._get_kit_from_base_item(base_item)

            initial_data = {
                "brand": self._get_entity_data(base_item, kit, "brand", "brand"),
                "club": self._get_entity_data(base_item, kit, "club", "team"),
                "season": self._get_season_data(base_item, kit),
                "competitions": self._get_competitions_data(base_item, kit),
            }
            # Remove None values
            initial_data = {k: v for k, v in initial_data.items() if v}

            context["autocomplete_initial_data"] = json.dumps(initial_data)
            logger.info("Autocomplete initial data for ItemUpdateView: %s", context["autocomplete_initial_data"])
        except (AttributeError, ValueError, TypeError, KeyError) as e:
            logger.warning("Error building autocomplete initial data for ItemUpdateView: %s", e)
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
        # Try from base_item first
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

        # Try from kit
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
        # Try from base_item first
        try:
            season = base_item.season
            if season:
                return {"id": season.id, "name": season.year, "logo": ""}
        except AttributeError:
            pass

        # Try from kit
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
        # Try from base_item first
        try:
            competitions = list(base_item.competitions.all())
            if competitions:
                return [
                    {"id": comp.id, "name": comp.name, "logo": getattr(comp, "logo", None) or ""}
                    for comp in competitions
                ]
        except AttributeError:
            pass

        # Try from kit
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
    success_url = reverse_lazy("collection:item_list")

    def get_success_url(self):
        """Return to the same page after deletion."""
        page = self.request.POST.get("page") or self.request.GET.get("page")
        base_url = reverse_lazy("collection:item_list")
        if page and page != "1":
            return f"{base_url}?page={page}"
        return base_url

    def delete(self, request, *args, **kwargs):
        """Override delete to handle photo cleanup."""
        item = self.get_object()

        # Delete associated photos
        photos = item.photos.all()
        for photo in photos:
            photo.delete()

        # Use a plain English success message so tests can assert on the word \"photo\"
        # (avoid translation changing the literal text).
        messages.success(request, "Item and associated photos deleted successfully.")

        # Invalidate cached item list pages for this user so the next render
        # isn't served from a stale cache that was generated before the message
        # was added. This is important for tests that assert on the presence
        # of the success message in the redirected response.
        invalidate_item_list_cache_for_user(request.user.pk)

        return super().delete(request, *args, **kwargs)


class JerseyCreateView(BaseItemCreateView):
    """Create view specifically for jerseys."""

    model = Jersey
    form_class = JerseyForm
    template_name = "collection/item_form.html"
    success_url = reverse_lazy("collection:item_list")

    def get_context_data(self, **kwargs):
        """Add context data for jersey creation."""
        context = super().get_context_data(**kwargs)
        context["item_type"] = "jersey"
        context["is_manual_mode"] = True
        context["help_text"] = _(
            "Use this form to add a jersey that is not in our kit database. "
            "Search for clubs, seasons, and competitions. If they don't exist, you can create them. "
            "This is perfect for fantasy clubs, custom jerseys, or rare items not in the database.",
        )

        # Add translated labels for autocomplete components
        context["label_brand"] = _("Brand")
        context["label_club"] = _("Club")
        context["label_season"] = _("Season")
        context["label_competitions"] = _("Competitions")
        context["help_brand"] = _(
            "Search for a brand from the external database. If not found, you can create it manually.",
        )
        context["help_club"] = _("Search for a club. If not found, you can create it manually.")
        context["help_season"] = _("Search for a season (e.g., 2020-21). If not found, you can create it manually.")
        context["help_competitions"] = _(
            "Search for competitions from the external database. If not found, you can create them manually.",
        )

        # Add options for Cotton components using services
        try:
            import json

            from footycollect.collection.models import BaseItem
            from footycollect.collection.services import get_collection_service

            collection_service = get_collection_service()
            form_data = collection_service.get_form_data()
            context["color_choices"] = json.dumps(form_data["colors"]["main_colors"])
            context["design_choices"] = json.dumps(
                [{"value": d[0], "label": str(d[1])} for d in BaseItem.DESIGN_CHOICES],
            )
        except (KeyError, AttributeError, ImportError) as e:
            logger.warning("Error getting form data: %s", str(e))
            context["color_choices"] = "[]"
            context["design_choices"] = "[]"

        return context

    def form_valid(self, form):
        """Handle form validation for jersey creation."""
        try:
            with transaction.atomic():
                # JerseyForm.save() creates both BaseItem and Jersey objects
                # It needs the user in the form's user attribute
                form.user = self.request.user

                # Save the jersey (this creates BaseItem and Jersey)
                base_item = form.save()

                # Set self.object for CreateView's redirect
                self.object = base_item

                # Process any additional data
                self._process_post_creation(form)

                messages.success(self.request, _("Jersey created successfully!"))

                # Redirect to success URL
                from django.http import HttpResponseRedirect

                return HttpResponseRedirect(self.get_success_url())

        except (ValueError, TypeError, AttributeError):
            logger.exception("Error creating jersey")
            messages.error(
                self.request,
                _("Error creating jersey."),
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        """Handle form validation errors."""
        logger.warning("Form validation failed. Errors: %s", form.errors)
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)

    def _process_post_creation(self, form):
        """Process any additional data after jersey creation."""
        from django.utils.text import slugify

        from footycollect.core.models import Brand, Competition

        brand_name = self.request.POST.get("brand_name")
        if brand_name and not self.object.brand:
            try:
                brand, created = Brand.objects.get_or_create(
                    name=brand_name,
                    defaults={"slug": slugify(brand_name)},
                )
                self.object.brand = brand
                self.object.save()
                if created:
                    logger.info("Created new brand %s for jersey", brand.name)
                else:
                    logger.info("Found existing brand %s for jersey", brand.name)
            except (ValueError, TypeError):
                logger.exception("Error creating brand %s", brand_name)

        competition_name = self.request.POST.get("competition_name")
        if competition_name:
            try:
                competition, created = Competition.objects.get_or_create(
                    name=competition_name,
                    defaults={"slug": slugify(competition_name)},
                )
                if competition not in self.object.competitions.all():
                    self.object.competitions.add(competition)
                    if created:
                        logger.info("Created and added new competition %s to jersey", competition.name)
                    else:
                        logger.info("Added existing competition %s to jersey", competition.name)
            except (ValueError, TypeError):
                logger.exception("Error adding competition %s", competition_name)


class JerseyUpdateView(BaseItemUpdateView):
    """Update view specifically for jerseys."""

    model = Jersey
    form_class = JerseyForm
    template_name = "collection/item_form.html"
    success_url = reverse_lazy("collection:item_list")

    def get_context_data(self, **kwargs):
        """Add context data for jersey editing."""
        context = super().get_context_data(**kwargs)
        context["item_type"] = "jersey"
        context["is_edit"] = True
        return context

    def form_valid(self, form):
        """Handle form validation for jersey updates."""
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                messages.success(self.request, _("Jersey updated successfully!"))
                return response

        except (ValueError, TypeError, AttributeError):
            logger.exception("Error updating jersey")
            messages.error(self.request, _("Error updating jersey. Please try again."))
            return self.form_invalid(form)
