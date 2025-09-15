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

from footycollect.collection.forms import JerseyForm, TestBrandForm, TestCountryForm
from footycollect.collection.models import BaseItem, Jersey, OtherItem, Outerwear, Pants, Shorts, Tracksuit
from footycollect.collection.services import get_photo_service

from .base import BaseItemCreateView, BaseItemDeleteView, BaseItemDetailView, BaseItemListView, BaseItemUpdateView

logger = logging.getLogger(__name__)


# =============================================================================
# FUNCTION-BASED VIEWS
# =============================================================================


def test_country_view(request):
    """Test view for country form."""
    form = TestCountryForm()
    return render(request, "collection/test_country.html", {"form": form})


def test_brand_view(request):
    """Test view for brand form."""
    form = TestBrandForm()
    context = {"form": form}
    return render(request, "collection/test_brand.html", context)


def home(request):
    """Home view showing all photos."""
    photo_service = get_photo_service()
    photos = photo_service.photo_repository.get_all()
    context = {"photos": photos}
    return render(request, "collection/item_create.html", context)


def test_dropzone(request):
    """Independent test view for Dropzone."""
    return render(request, "collection/dropzone_test_page.html")


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

        form = self.form_class(request.POST, instance=BaseItem(), user=request.user)
        if form.is_valid():
            # Use service to create item with photos
            photo_service = get_photo_service()

            # Create item - form.save() already handles the BaseItem creation
            new_item = form.save()

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
    """View for selecting a jersey from the database (first step)."""

    template_name = "collection/jersey_select.html"

    # Performance optimization fields
    select_related_fields = ["user"]
    prefetch_related_fields = []

    def get_context_data(self, **kwargs):
        # No need to add additional context for the grid layout
        # The grid is populated dynamically via JavaScript/Alpine.js
        return super().get_context_data(**kwargs)


# =============================================================================
# BASE ITEM VIEWS
# =============================================================================


class ItemListView(BaseItemListView):
    """List view for all items in the user's collection."""

    template_name = "collection/item_list.html"

    def get_queryset(self):
        """Get all items for the current user with optimizations."""
        from footycollect.collection.models import BaseItem

        return (
            BaseItem.objects.filter(user=self.request.user, item_type="jersey")
            .select_related(
                "club",
                "season",
                "brand",
            )
            .prefetch_related("competitions", "photos")
            .order_by("-created_at")
        )


class ItemDetailView(BaseItemDetailView):
    """Detail view for a specific item in the collection."""

    template_name = "collection/item_detail.html"

    def get_context_data(self, **kwargs):
        """Add additional context data for the item detail."""
        context = super().get_context_data(**kwargs)

        # Get related items from all item types
        related_items = self._get_related_items()
        context["related_items"] = related_items[:5]
        return context

    def _get_related_items(self):
        """Get related items from all item types."""

        # Get all item types
        item_models = [Jersey, Shorts, Outerwear, Tracksuit, Pants, OtherItem]
        related_items = []

        # Get items from each model type
        for model in item_models:
            try:
                if hasattr(model, "base_item"):
                    # For MTI models, filter through base_item
                    items = model.objects.filter(
                        base_item__club=self.object.club,
                    ).exclude(base_item__id=self.object.id)
                else:
                    # For BaseItem itself
                    items = model.objects.filter(
                        club=self.object.club,
                    ).exclude(id=self.object.id)
                related_items.extend(items)
            except (AttributeError, ValueError) as e:
                # Skip if model doesn't have required fields
                logger.debug("Skipping model %s due to missing fields: %s", model.__name__, e)
                continue

        # Sort by creation date and return
        # Handle both BaseItem and MTI models
        def get_created_at(item):
            if hasattr(item, "created_at"):
                return item.created_at
            if hasattr(item, "base_item") and hasattr(item.base_item, "created_at"):
                return item.base_item.created_at
            # Fallback to current time if no created_at found
            from django.utils import timezone

            return timezone.now()

        return sorted(related_items, key=get_created_at, reverse=True)


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
        return context

    def form_valid(self, form):
        """Handle form validation for jersey creation."""
        try:
            with transaction.atomic():
                # Set the user
                form.instance.user = self.request.user

                # Save the jersey
                response = super().form_valid(form)

                # Process any additional data
                self._process_post_creation(form)

                messages.success(self.request, _("Jersey created successfully!"))
                return response

        except Exception:
            logger.exception("Error creating jersey")
            messages.error(self.request, _("Error creating jersey. Please try again."))
            return self.form_invalid(form)

    def _process_post_creation(self, form):
        """Process any additional data after jersey creation."""
        # This method can be extended to handle additional processing


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
