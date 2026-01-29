"""
Complex jersey-related views for the collection app.

This module contains the complex jersey views that were in the original views.py
file, including FKAPI integration and detailed jersey processing.
"""

import json
import logging
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
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
        """Override dispatch to log all requests."""
        # Only log on POST requests to avoid overhead on GET requests
        if request.method == "POST":
            logger.info("=== DISPATCH CALLED ===")
            logger.info("Method: %s", request.method)
            logger.info("User: %s", request.user)
            logger.info("Is authenticated: %s", request.user.is_authenticated)
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
        logger.info("=" * 60)
        logger.info("JerseyFKAPICreateView.post() START")
        logger.info("=" * 60)

        # Log what we received
        logger.debug("POST keys: %s", list(request.POST.keys()))
        logger.debug("POST main_color: %s", request.POST.get("main_color"))
        secondary_colors = (
            request.POST.getlist("secondary_colors")
            if hasattr(request.POST, "getlist")
            else request.POST.get("secondary_colors")
        )
        logger.debug("POST secondary_colors: %s", secondary_colors)
        logger.debug("POST country_code: %s", request.POST.get("country_code"))
        logger.debug("POST kit_id: %s", request.POST.get("kit_id"))

        # STEP 1: Make request.POST mutable BEFORE creating form
        self._make_post_mutable(request)

        # STEP 2: If we have a kit_id, fetch FKAPI data and merge it
        self._fetch_and_merge_fkapi_data(request)

        # Log final POST data
        logger.debug("Final POST main_color: %s", request.POST.get("main_color"))
        final_secondary = (
            request.POST.getlist("secondary_colors")
            if hasattr(request.POST, "getlist")
            else request.POST.get("secondary_colors")
        )
        logger.debug("Final POST secondary_colors: %s", final_secondary)
        logger.debug("Final POST country_code: %s", request.POST.get("country_code"))
        logger.debug("Final POST competitions: %s", request.POST.get("competitions"))

        # ============================================================
        # STEP 3: NOW create the form (it will use modified POST)
        # ============================================================
        self.object = None
        form = self.get_form()

        # Store kit_data on form for save() method
        if hasattr(request, "_fkapi_kit_data"):
            form.fkapi_data = request._fkapi_kit_data  # noqa: SLF001

        # ============================================================
        # STEP 4: Validate and process
        # ============================================================
        logger.debug("Form data main_color: %s", form.data.get("main_color"))
        form_secondary = (
            form.data.getlist("secondary_colors")
            if hasattr(form.data, "getlist")
            else form.data.get("secondary_colors")
        )
        logger.debug("Form data secondary_colors: %s", form_secondary)
        logger.debug("Form data country_code: %s", form.data.get("country_code"))

        if form.is_valid():
            logger.info("Form is VALID")
            cleaned_keys = (
                list(form.cleaned_data.keys())
                if hasattr(form, "cleaned_data") and isinstance(form.cleaned_data, dict)
                else "N/A"
            )
            logger.debug("cleaned_data keys: %s", cleaned_keys)
            cleaned_main_color = (
                form.cleaned_data.get("main_color")
                if hasattr(form, "cleaned_data") and isinstance(form.cleaned_data, dict)
                else "N/A"
            )
            logger.debug("cleaned_data main_color: %s", cleaned_main_color)
            cleaned_secondary = (
                form.cleaned_data.get("secondary_colors")
                if hasattr(form, "cleaned_data") and isinstance(form.cleaned_data, dict)
                else "N/A"
            )
            logger.debug("cleaned_data secondary_colors: %s", cleaned_secondary)
            cleaned_country = (
                form.cleaned_data.get("country_code")
                if hasattr(form, "cleaned_data") and isinstance(form.cleaned_data, dict)
                else "N/A"
            )
            logger.debug("cleaned_data country_code: %s", cleaned_country)
            self._preprocess_form_data(form)
            return self.form_valid(form)
        logger.error("Form is INVALID")
        logger.error("Form errors: %s", form.errors)
        logger.error("Form non_field_errors: %s", form.non_field_errors())
        return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("collection:item_detail", kwargs={"pk": self.object.pk})

    def get_form(self, form_class=None):
        """Get form instance with proper initialization."""
        if form_class is None:
            form_class = self.get_form_class()

        # Initialize form with proper kwargs
        kwargs = self.get_form_kwargs()
        form = form_class(**kwargs)

        # Log form initialization for debugging
        logger.info(
            "Form initialized: %s, instance: %s, has _meta: %s",
            form_class.__name__,
            form.instance,
            hasattr(form, "_meta"),
        )

        return form

    def get_form_kwargs(self):
        """Add user to form kwargs and ensure we use the modified POST."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        # Ensure form uses the modified request.POST (not a copy)
        # The super() method already sets data=request.POST, but we want to be explicit
        if "data" in kwargs:
            # Ensure the data is the mutable version we modified
            kwargs["data"] = self.request.POST
        data = kwargs.get("data", {})
        if isinstance(data, dict):
            logger.debug("get_form_kwargs - data keys: %s", list(data.keys()))
            logger.debug("get_form_kwargs - data main_color: %s", data.get("main_color"))
            logger.debug("get_form_kwargs - data country_code: %s", data.get("country_code"))
        else:
            logger.debug("get_form_kwargs - data type: %s", type(data))
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

        # Add options for Cotton components using services
        self._add_color_and_design_choices(context)
        return context

    def _add_color_and_design_choices(self, context):
        """Add color and design choices to context for Cotton components."""

        try:
            collection_service = get_collection_service()
            form_data = collection_service.get_form_data()
            logger.info("Form data from service: %s", form_data)
            context["color_choices"] = json.dumps(form_data["colors"]["main_colors"])
            context["design_choices"] = json.dumps(
                [{"value": d[0], "label": str(d[1])} for d in BaseItem.DESIGN_CHOICES],
            )
            logger.info("Color choices set to: %s", context["color_choices"])
        except (KeyError, AttributeError, ImportError) as e:
            logger.warning("Error getting form data: %s", str(e))
            context["color_choices"] = "[]"
            context["design_choices"] = "[]"

    def form_valid(self, form):  # noqa: PLR0915
        """
        Processes the form when it is valid.
        Creates the necessary entities from the API data
        and handles external images.
        """

        from django.conf import settings

        debug_log_path = Path(settings.BASE_DIR) / "debug_post.log"

        debug_msg = f"\n{'='*50}\n=== FORM_VALID CALLED (Timestamp: {__import__('datetime').datetime.now()}) ===\n"
        debug_msg += f"Form is_valid: {form.is_valid()}\n"
        debug_msg += f"Form errors: {form.errors}\n"
        debug_msg += f"{'='*50}\n"

        logger.debug(debug_msg)

        # Also write to file
        try:
            debug_path = Path(debug_log_path)
            with debug_path.open("a", encoding="utf-8") as f:
                f.write(debug_msg)
        except OSError:
            logger.exception("ERROR writing debug log in form_valid")

        logger.info("=== FORM_VALID CALLED ===")
        logger.info("Form is_valid: %s", form.is_valid())
        logger.info("Form errors: %s", form.errors)

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

            # Process external images first
            self._process_external_images(form, base_item)

            # Process uploaded photos through the dropzone (local photos start after externals)
            photo_ids = self.request.POST.get("photo_ids", "")
            if photo_ids:
                self._process_photo_ids(photo_ids, base_item, start_order=external_count)

            # Mark as not draft
            self.object.is_draft = False
            self.object.save()
            logger.info("Jersey marked as not draft")

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

    def _write_debug_log(self, form, method_name):
        """Write debug log for form processing."""

        from django.conf import settings

        datetime_now = __import__("datetime").datetime.now()
        debug_msg = f"\n{'='*50}\n=== {method_name} CALLED (Timestamp: {datetime_now}) ===\n"
        debug_msg += f"POST keys: {list(self.request.POST.keys())}\n"
        debug_msg += f"country_code: {self.request.POST.get('country_code')}\n"
        debug_msg += f"main_color: {self.request.POST.get('main_color')}\n"
        debug_msg += f"secondary_colors (get): {self.request.POST.get('secondary_colors')}\n"
        secondary_colors_getlist = (
            self.request.POST.getlist("secondary_colors") if hasattr(self.request.POST, "getlist") else "N/A"
        )
        debug_msg += f"secondary_colors (getlist): {secondary_colors_getlist}\n"
        debug_msg += f"kit_id: {self.request.POST.get('kit_id')}\n"
        cleaned_data_keys = list(form.cleaned_data.keys()) if hasattr(form, "cleaned_data") else "N/A"
        debug_msg += f"form.cleaned_data keys: {cleaned_data_keys}\n"
        cleaned_data_country = form.cleaned_data.get("country_code") if hasattr(form, "cleaned_data") else "N/A"
        debug_msg += f"form.cleaned_data country_code: {cleaned_data_country}\n"
        cleaned_data_main_color = form.cleaned_data.get("main_color") if hasattr(form, "cleaned_data") else "N/A"
        debug_msg += f"form.cleaned_data main_color: {cleaned_data_main_color}\n"
        cleaned_data_secondary = form.cleaned_data.get("secondary_colors") if hasattr(form, "cleaned_data") else "N/A"
        debug_msg += f"form.cleaned_data secondary_colors: {cleaned_data_secondary}\n"
        debug_msg += f"{'='*50}\n"

        logger.debug(debug_msg)

        debug_log_path = Path(settings.BASE_DIR) / "debug_post.log"
        try:
            with debug_log_path.open("a", encoding="utf-8") as f:
                f.write(debug_msg)
        except OSError:
            logger.exception("ERROR writing debug log")

    def _save_and_finalize(self, form):
        """Save the jersey and finalize related assignments."""
        self._write_debug_log(form, "_save_and_finalize")

        logger.info("=== _save_and_finalize CALLED ===")

        country_code_post = self.request.POST.get("country_code")
        main_color_post, secondary_colors_post = self._get_post_color_values()

        logger.info("=== DEBUG: Stored POST values BEFORE form.save() ===")
        logger.info("country_code_post: %s (type: %s)", country_code_post, type(country_code_post))
        logger.info("main_color_post: %s (type: %s)", main_color_post, type(main_color_post))
        logger.info("secondary_colors_post: %s (type: %s)", secondary_colors_post, type(secondary_colors_post))

        # Before saving, ensure country_code and colors are in cleaned_data
        # Use form.cleaned_data directly - the ensure methods will handle it
        self._ensure_country_code_in_cleaned_data(form)
        self._ensure_main_color_in_cleaned_data(form)
        self._ensure_secondary_colors_in_cleaned_data(form)

        # Save the jersey (this will create/get Kit via JerseyForm.save())
        response = super().form_valid(form)
        logger.info("Jersey saved with ID: %s", self.object.pk)

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

        logger.info("base_item.country: %s", base_item.country)
        logger.info("base_item.main_color: %s", base_item.main_color)
        logger.info("base_item.secondary_colors.count(): %s", base_item.secondary_colors.count())

        # Update BaseItem with country and colors if they weren't saved
        updated = False
        updated |= self._update_base_item_country(base_item, country_code_post, form)
        updated |= self._update_base_item_main_color(base_item, main_color_post, form)
        updated |= self._update_base_item_secondary_colors(base_item, secondary_colors_post, form)

        # Save BaseItem if updated
        if updated:
            base_item.save()
            logger.info("Updated BaseItem with country/colors")

        self._create_kit_if_needed(jersey, form)

        self._process_additional_competitions(form)

        return response

    def form_invalid(self, form):
        """Handle invalid form submission."""
        logger.exception("=== FORM_INVALID CALLED in JerseyFKAPICreateView ===")
        logger.exception("Form errors: %s", form.errors.as_json())
        logger.exception("Form non_field_errors: %s", form.non_field_errors())

        # Log all form data to see what was submitted
        logger.exception("Form data submitted:")
        for field_name in form.fields:
            value = form.data.get(field_name, "NOT_PROVIDED")
            logger.exception("  %s: %s", field_name, value)

        return super().form_invalid(form)
