"""
Complex jersey-related views for the collection app.

This module contains the complex jersey views that were in the original views.py
file, including FKAPI integration and detailed jersey processing.
"""

import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView

from footycollect.collection.forms import JerseyFKAPIForm
from footycollect.collection.models import BaseItem, Jersey
from footycollect.collection.services import get_collection_service

from .jersey.mixins import (
    BaseItemUpdateMixin,
    ColorProcessingMixin,
    EntityProcessingMixin,
    FKAPIDataMixin,
    FormDataMixin,
    KitDataProcessingMixin,
    PhotoProcessingMixin,
)
from .photo_processor_mixin import PhotoProcessorMixin

logger = logging.getLogger(__name__)


class JerseyFKAPICreateView(
    BaseItemUpdateMixin,
    ColorProcessingMixin,
    EntityProcessingMixin,
    FKAPIDataMixin,
    FormDataMixin,
    KitDataProcessingMixin,
    PhotoProcessingMixin,
    PhotoProcessorMixin,
    LoginRequiredMixin,
    CreateView,
):
    """View for creating jerseys with FKAPI integration."""

    model = Jersey
    form_class = JerseyFKAPIForm
    template_name = "collection/jersey_fkapi_create.html"

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Optimized GET method that doesn't initialize photo processing."""
        # For GET requests, we don't need photo processing
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Handle POST request for automatic jersey creation.

        CRITICAL: Modify request.POST BEFORE creating the form.
        Django forms copy POST data at creation time, so modifications
        after get_form() won't affect the form.
        """
        # STEP 1: Make request.POST mutable BEFORE creating form
        self._make_post_mutable(request)

        # STEP 2: If we have a kit_id, fetch FKAPI data and merge it
        self._fetch_and_merge_fkapi_data(request)

        # STEP 3: NOW create the form (it will use modified POST)
        # ============================================================
        self.object = None
        form = self.get_form()

        # Store kit_data on form for save() method
        if hasattr(request, "_fkapi_kit_data"):
            form.fkapi_data = request._fkapi_kit_data  # noqa: SLF001

        # STEP 4: Validate and process
        if form.is_valid():
            self._preprocess_form_data(form)
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("collection:item_detail", kwargs={"pk": self.object.pk})

    def get_form(self, form_class=None):
        """Get form instance with proper initialization."""
        if form_class is None:
            form_class = self.get_form_class()

        # Initialize form with proper kwargs
        kwargs = self.get_form_kwargs()
        return form_class(**kwargs)

    def get_form_kwargs(self):
        """Add user to form kwargs and ensure we use the modified POST."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        # Ensure form uses the modified request.POST (not a copy)
        # The super() method already sets data=request.POST, but we want to be explicit
        if "data" in kwargs:
            kwargs["data"] = self.request.POST
        return kwargs

    def get_context_data(self, **kwargs):
        # For CreateView, we don't call super() to avoid DetailView's get_context_data
        context = {}

        # Add the form to context
        if hasattr(self, "form_class"):
            form = self.get_form()
            context["form"] = form
            # Convert color names to IDs for template if they come from API
            self._set_main_color_initial(form)
            self._set_secondary_colors_initial(form)

        self._add_color_and_design_choices(context)
        context["proxy_image_url"] = reverse("collection:proxy_image")
        context["proxy_image_hosts"] = json.dumps(getattr(settings, "ALLOWED_EXTERNAL_IMAGE_HOSTS", []))
        return context

    def _add_color_and_design_choices(self, context):
        """Add color and design choices to context for Cotton components."""
        try:
            collection_service = get_collection_service()
            form_data = collection_service.get_form_data()
            context["color_choices"] = json.dumps(form_data["colors"]["main_colors"])
            context["design_choices"] = json.dumps(
                [{"value": d[0], "label": str(d[1])} for d in BaseItem.DESIGN_CHOICES],
            )
        except (KeyError, AttributeError, ImportError) as e:
            logger.warning("Error getting form data: %s", type(e).__name__)
            context["color_choices"] = "[]"
            context["design_choices"] = "[]"
        return context

    def form_valid(self, form):
        """
        Processes the form when it is valid.
        Creates the necessary entities from the API data
        and handles external images.
        """
        try:
            # Ensure country_code, colors are in cleaned_data BEFORE processing entities
            self._ensure_form_cleaned_data(form)

            # Process related entities from the API
            self._process_new_entities(form)

            # Save and finalize
            response = self._save_and_finalize(form)

            # Refresh object from database to ensure base_item is available
            self.object.refresh_from_db()

            # Get base_item for photo associations
            base_item = self._get_base_item_for_photos()

            # Check if we have external images or photos that need processing
            has_external_images = bool(form.cleaned_data.get("main_img_url")) or bool(
                form.cleaned_data.get("external_image_urls")
            )
            has_photo_ids = bool(self.request.POST.get("photo_ids", ""))

            if has_external_images or has_photo_ids:
                base_item.is_processing_photos = True
                base_item.save(update_fields=["is_processing_photos"])

            # Count external images first to set correct order for local photos
            main_img_url = form.cleaned_data.get("main_img_url")
            external_urls = form.cleaned_data.get("external_image_urls", "")
            external_count = 0
            if main_img_url:
                external_count += 1
            if external_urls:
                urls = [u.strip() for u in external_urls.split(",") if u.strip() and u.strip() != main_img_url]
                external_count += len(urls)

            self._process_external_images(form, base_item)

            try:
                from footycollect.collection.services.logo_download import (
                    ensure_item_entity_logos_downloaded,
                )

                ensure_item_entity_logos_downloaded(base_item)
            except Exception:
                logger.exception("Error downloading club/brand logos for item")

            photo_ids = self.request.POST.get("photo_ids", "")
            if photo_ids:
                self._process_photo_ids(photo_ids, base_item, start_order=external_count)

            # Mark as not draft
            self.object.is_draft = False
            self.object.save()

            if has_external_images or has_photo_ids:
                from footycollect.collection.tasks import check_item_photo_processing

                check_item_photo_processing.apply_async(
                    args=[base_item.pk],
                    countdown=5,
                )

            messages.success(
                self.request,
                _("Jersey added to your collection successfully!"),
            )

        except (ValueError, TypeError, AttributeError, KeyError) as e:
            logger.exception("Error in form_valid")
            error_msg = _("Error creating jersey: %s") % str(e)
            messages.error(self.request, error_msg)
            return self.form_invalid(form)

        return response

    def _save_and_finalize(self, form):
        """Save the jersey and finalize related assignments."""
        country_code_post = self.request.POST.get("country_code")
        main_color_post, secondary_colors_post = self._get_post_color_values()

        # Before saving, ensure country_code and colors are in cleaned_data
        # Use form.cleaned_data directly - the ensure methods will handle it
        self._ensure_country_code_in_cleaned_data(form)
        self._ensure_main_color_in_cleaned_data(form)
        self._ensure_secondary_colors_in_cleaned_data(form)

        response = super().form_valid(form)

        # Get the created BaseItem and Jersey
        from footycollect.collection.models import Jersey

        base_item = self.object
        try:
            if hasattr(base_item, "base_item"):
                jersey = base_item
                base_item = base_item.base_item
            else:
                jersey = Jersey.objects.get(base_item=base_item)
        except (Jersey.DoesNotExist, AttributeError, TypeError):
            if hasattr(self.object, "base_item"):
                jersey = self.object
                base_item = self.object.base_item
            else:
                jersey = self.object
                base_item = getattr(self.object, "base_item", self.object)

        updated = False
        updated |= self._update_base_item_country(base_item, country_code_post, form)
        updated |= self._update_base_item_main_color(base_item, main_color_post, form)
        updated |= self._update_base_item_secondary_colors(base_item, secondary_colors_post, form)

        if updated:
            base_item.save()

        self._create_kit_if_needed(jersey, form)

        self._process_additional_competitions(form)

        return response

    def form_invalid(self, form):
        """Handle invalid form submission."""
        logger.warning("Jersey create form invalid: fields=%s", list(form.errors.keys()))

        return super().form_invalid(form)
