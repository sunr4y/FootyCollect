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


def home(request):
    """Home view with animated jersey cards in background."""
    from pathlib import Path

    from footycollect.collection.models import Jersey

    # Get most recent items from all users for the background animation
    # Only include items that have physical photos on disk
    try:
        all_jerseys = list(
            Jersey.objects.select_related(
                "base_item",
                "base_item__user",
                "base_item__club",
                "base_item__season",
                "base_item__brand",
                "base_item__main_color",
                "size",
            )
            .prefetch_related(
                "base_item__photos",
                "base_item__competitions",
                "base_item__secondary_colors",
            )
            .filter(base_item__photos__isnull=False)
            .distinct()
            .order_by("-base_item__created_at")[:500],  # Get most recent items
        )

        # Filter to only include items with physical photos on disk
        jerseys_with_photos = []
        for jersey in all_jerseys:
            photos = jersey.base_item.photos.all()
            for photo in photos:
                if photo.image:
                    try:
                        if Path(photo.image.path).exists():
                            jerseys_with_photos.append(jersey)
                            break
                    except (ValueError, AttributeError):
                        continue

        items = jerseys_with_photos

        # Distribute items across columns (40 columns)
        # Each column gets unique items starting at different positions
        num_columns = 40
        columns_items = []

        if items and len(items) > 0:
            import random

            # Shuffle items to ensure randomness
            shuffled_items = items.copy()
            random.shuffle(shuffled_items)

            for i in range(num_columns):
                column_items = []
                # Each column starts at a different offset to ensure uniqueness
                # Use a larger step to ensure columns are more different
                start_index = (i * max(1, len(shuffled_items) // num_columns)) % len(shuffled_items)

                # Create a unique sequence for this column by cycling through items
                # Use enough items to fill the column
                items_per_cycle = max(len(shuffled_items), 20)  # At least 20 items per cycle
                for j in range(items_per_cycle):
                    item_index = (start_index + j) % len(shuffled_items)
                    column_items.append(shuffled_items[item_index])

                # Duplicate the sequence 3 times for seamless infinite scroll
                column_items = column_items * 3
                columns_items.append(column_items)
        else:
            columns_items = [[] for _ in range(num_columns)]
    except (OSError, ValueError, AttributeError, TypeError, IndexError):
        logger.exception("Error in home view")
        columns_items = [[] for _ in range(40)]

    context = {
        "columns_items": columns_items,
    }
    return render(request, "pages/home.html", context)


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

    def get(self, request, *args, **kwargs):
        from django.core.cache import cache

        if not request.user.is_authenticated:
            return super().get(request, *args, **kwargs)

        page = request.GET.get("page", "1")
        cache_key = get_item_list_cache_key(request.user.pk, page)

        cached_response = cache.get(cache_key)
        if cached_response is not None:
            logger.info("ItemListView cache hit for user %s page %s", request.user.pk, page)
            track_item_list_cache_key(request.user.pk, cache_key)
            increment_item_list_cache_metric(is_hit=True)
            return cached_response

        response = super().get(request, *args, **kwargs)
        response.render()
        cache.set(cache_key, response, ITEM_LIST_CACHE_TIMEOUT)
        track_item_list_cache_key(request.user.pk, cache_key)
        increment_item_list_cache_metric(is_hit=False)
        logger.info("ItemListView cache miss; cached response for user %s page %s", request.user.pk, page)
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
            )
            .prefetch_related(
                "base_item__competitions",
                "base_item__photos",
                "base_item__secondary_colors",
            )
            .order_by("-base_item__created_at")
        )


class ItemDetailView(BaseItemDetailView):
    """Detail view for a specific item in the collection."""

    template_name = "collection/item_detail.html"

    def get_queryset(self):
        """Get queryset with optimizations for detail view."""
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

    def get_form_class(self):
        """Return the appropriate form class based on the item type."""
        if isinstance(self.object, Jersey):
            return JerseyForm
        # Add other form types as needed
        return JerseyForm

    def get_context_data(self, **kwargs):
        """Add context data for item update."""
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


class ItemDeleteView(BaseItemDeleteView):
    """Delete view for removing items from the collection."""

    template_name = "collection/item_confirm_delete.html"
    success_url = reverse_lazy("collection:item_list")

    def delete(self, request, *args, **kwargs):
        """Override delete to handle photo cleanup."""
        item = self.get_object()

        # Delete associated photos
        photos = item.photos.all()
        for photo in photos:
            photo.delete()

        messages.success(request, _("Item and associated photos deleted successfully."))
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

        except Exception:
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
            except Exception:
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
            except Exception:
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

        except Exception:
            logger.exception("Error updating jersey")
            messages.error(self.request, _("Error updating jersey. Please try again."))
            return self.form_invalid(form)
