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
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView

from footycollect.api.client import FKAPIClient
from footycollect.collection.forms import JerseyFKAPIForm
from footycollect.collection.models import BaseItem, Competition, Jersey, Kit
from footycollect.collection.services import get_collection_service

from .jersey.mixins import (
    EntityProcessingMixin,
    FKAPIDataMixin,
    FormDataMixin,
    PhotoProcessingMixin,
)
from .photo_views import PhotoProcessorMixin

logger = logging.getLogger(__name__)


class JerseyFKAPICreateView(
    EntityProcessingMixin,
    FKAPIDataMixin,
    FormDataMixin,
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

    def _preprocess_form_data(self, form):
        """
        Preprocess form data before validation.
        Sets up form instance and processes kit data if available.
        """
        self._setup_form_instance(form)
        kit_id = form.data.get("kit_id")
        if kit_id:
            self._process_kit_data(form, kit_id)
        self._fill_form_with_api_data(form)

    def _fill_form_with_api_data(self, form):
        """Fill form fields with data from API."""
        # Create a mutable copy of form.data
        try:
            form.data = form.data.copy()
        except AttributeError:
            # If copy doesn't exist, create a mutable dict
            form.data = dict(form.data)

        # Fill name field if empty
        if not form.data.get("name") and form.instance.name:
            form.data["name"] = form.instance.name

        # Fill other fields from API data
        self._fill_club_field(form)
        self._fill_brand_field(form)
        self._fill_season_field(form)

    def _fill_club_field(self, form):
        """Fill club field from API data."""
        if not form.data.get("club_name") or form.data.get("club"):
            return

        from footycollect.core.models import Club

        try:
            club = Club.objects.get(name=form.data["club_name"])
            self._update_club_country(club)
            form.data["club"] = club.id
        except Club.DoesNotExist:
            club = self._create_club_from_api_data(form)
            form.data["club"] = club.id

    def _fill_brand_field(self, form):
        """Fill brand field from API data."""
        if not form.data.get("brand_name") or form.data.get("brand"):
            return

        from footycollect.core.models import Brand

        try:
            brand = Brand.objects.get(name=form.data["brand_name"])
            form.data["brand"] = brand.id
        except Brand.DoesNotExist:
            # Check if brand with same slug already exists
            slug = form.data["brand_name"].lower().replace(" ", "-")
            try:
                brand = Brand.objects.get(slug=slug)
                form.data["brand"] = brand.id
            except Brand.DoesNotExist:
                brand = Brand.objects.create(
                    name=form.data["brand_name"],
                    slug=slug,
                )
                form.data["brand"] = brand.id

    def _setup_form_instance(self, form):
        """Setup basic form instance attributes."""
        # For STI structure, we need to create BaseItem first
        # The form will handle creating both BaseItem and Jersey

        # Ensure form has an instance
        if form.instance is None:
            # Check if form is a ModelForm and has _meta
            if hasattr(form, "_meta") and form._meta is not None and hasattr(form._meta, "model"):
                form.instance = form._meta.model()
            else:
                # For non-ModelForm or if _meta is None, create a BaseItem instance
                from footycollect.collection.models import BaseItem

                form.instance = BaseItem()

        # Set item_type for BaseItem
        form.instance.item_type = "jersey"

        # Fill required fields from form data (use form.data before validation)
        if not form.instance.name:
            # Try to get name from form data
            name = form.data.get("name")
            if not name:
                # Generate name from API data
                club_name = form.data.get("club_name", "")
                season_name = form.data.get("season_name", "")
                if club_name and season_name:
                    form.instance.name = f"{club_name} {season_name}"
                else:
                    form.instance.name = "Jersey"
            else:
                form.instance.name = name

        # Also set the form field value
        if not form.data.get("name") and form.instance.name:
            form.data = form.data.copy()
            form.data["name"] = form.instance.name

        # Set user
        if hasattr(self, "request") and self.request and hasattr(self.request, "user"):
            form.instance.user = self.request.user

        # Assign country if selected
        if form.data.get("country_code"):
            form.instance.country = form.data["country_code"]
            logger.info("Set country to %s", form.data["country_code"])

    def _process_kit_data(self, form, kit_id):
        """Process kit data from FKAPI and update form instance."""
        try:
            # Get kit data from FKAPI
            kit_data = self._fetch_kit_data_from_api(kit_id)
            if not kit_data:
                return

            # Store kit_data on form for Kit service to use
            if not hasattr(form, "fkapi_data"):
                form.fkapi_data = {}
            form.fkapi_data.update(kit_data)

            # Add kit ID to description for reference
            self._add_kit_id_to_description(form, kit_id)

            # Extract and store logo data from API
            self._extract_logo_data_from_kit(kit_data)

            # Try to find existing kit in database
            self._find_and_assign_existing_kit(form, kit_id)

        except (ValueError, TypeError, KeyError, AttributeError):
            logger.exception("Error processing kit data for ID %s", kit_id)
            # Don't raise - continue with form processing

    def _fetch_kit_data_from_api(self, kit_id):
        """Fetch kit data from FKAPI."""
        client = FKAPIClient()

        kit_data = client.get_kit_details(kit_id)

        if kit_data is None:
            # FKAPI is not available - log warning and continue without external data
            logger.warning(
                "FKAPI not available for kit ID %s. Returning None to allow graceful degradation.",
                kit_id,
            )
            messages.warning(
                self.request,
                _("External kit data temporarily unavailable. Jersey will be created with basic information."),
            )
            return None

        logger.info("Processing kit ID: %s", kit_id)
        logger.info("Kit data from FKAPI: %s", kit_data)
        return kit_data

    def _add_kit_id_to_description(self, form, kit_id):
        """Add kit ID to form description."""
        form.instance.description = form.instance.description or ""
        form.instance.description += f"\nKit ID from API: {kit_id}"

    def _extract_logo_data_from_kit(self, kit_data):
        """Extract logo data from kit and store in fkapi_data."""
        # Initialize fkapi_data if not exists
        if not hasattr(self, "fkapi_data"):
            self.fkapi_data = {}

        # Extract brand logo
        self._extract_brand_logo(kit_data)

        # Extract team logo and country
        self._extract_team_data(kit_data)

        # Extract competition logos
        self._extract_competition_logos(kit_data)

    def _extract_brand_logo(self, kit_data):
        """Extract brand logo and logo_dark from kit data."""
        if kit_data.get("brand"):
            brand_data = kit_data["brand"]
            if "logo" in brand_data:
                brand_logo_url = brand_data["logo"]
                if (
                    brand_logo_url
                    and brand_logo_url != "https://www.footballkitarchive.com/static/logos/not_found.png"
                ):
                    logger.info("Found brand logo URL: %s", brand_logo_url)
                    self.fkapi_data["brand_logo"] = brand_logo_url
            if "logo_dark" in brand_data:
                brand_logo_dark_url = brand_data["logo_dark"]
                if (
                    brand_logo_dark_url
                    and brand_logo_dark_url != "https://www.footballkitarchive.com/static/logos/not_found.png"
                ):
                    logger.info("Found brand logo_dark URL: %s", brand_logo_dark_url)
                    self.fkapi_data["brand_logo_dark"] = brand_logo_dark_url

    def _extract_team_data(self, kit_data):
        """Extract team logo and country from kit data."""
        logger.info("=== DEBUGGING _extract_team_data ===")
        logger.info("Kit data: %s", kit_data)

        team_data = kit_data.get("team")
        if team_data:
            logger.info("Team data found: %s", team_data)
            # Extract team logo
            if "logo" in team_data:
                team_logo_url = team_data["logo"]
                if team_logo_url and team_logo_url != "https://www.footballkitarchive.com/static/logos/not_found.png":
                    logger.info("Found team logo URL: %s", team_logo_url)
                    # Store for later use in _process_new_entities
                    if not hasattr(self, "fkapi_data"):
                        self.fkapi_data = {}
                    self.fkapi_data["team_logo"] = team_logo_url

            # Extract team country
            if "country" in team_data:
                team_country = team_data["country"]
                if team_country:
                    logger.info("Found team country: %s", team_country)
                    # Store for later use in _process_new_entities
                    if not hasattr(self, "fkapi_data"):
                        self.fkapi_data = {}
                    self.fkapi_data["team_country"] = team_country
                    logger.info("Stored team_country in fkapi_data: %s", self.fkapi_data)
                    # Also set country_code in form data if not already set
                    if hasattr(self, "form") and self.form:
                        if not self.form.data.get("country_code"):
                            form_data = self.form.data.copy()
                            form_data["country_code"] = team_country
                            self.form.data = form_data
                            logger.info("Set country_code in form.data to: %s", team_country)
        else:
            logger.warning("No team data found in kit_data")

    def _extract_competition_logos(self, kit_data):
        """Extract competition logos from kit data."""
        if kit_data.get("competition"):
            for comp in kit_data["competition"]:
                if comp and "logo" in comp:
                    comp_logo_url = comp["logo"]
                    if (
                        comp_logo_url
                        and comp_logo_url != "https://www.footballkitarchive.com/static/logos/not_found.png"
                    ):
                        logger.info("Found competition logo URL: %s", comp_logo_url)
                        if "competition_logos" not in self.fkapi_data:
                            self.fkapi_data["competition_logos"] = []
                        self.fkapi_data["competition_logos"].append(comp_logo_url)

    def _find_and_assign_existing_kit(self, form, kit_id):
        """Find existing kit in database and assign it."""
        try:
            kit = Kit.objects.get(id_fka=kit_id)
            logger.info("Found existing kit with id_fka: %s", kit_id)
            self._assign_existing_kit(form, kit, kit_id)
        except Kit.DoesNotExist:
            logger.warning("No kit found with id_fka: %s", kit_id)

    def _assign_existing_kit(self, form, kit, kit_id):
        """Assign existing kit and its related entities."""
        logger.info(
            "Found existing kit with id_fka: %s - %s (ID: %s)",
            kit_id,
            kit.name,
            kit.id,
        )
        # Assign the kit directly
        form.instance.kit = kit
        self.kit = kit
        logger.info(
            "Assigned existing kit to jersey: %s (ID: %s)",
            kit.name,
            kit.id,
        )

        # DEBUG: Logging competition data
        self._log_kit_debug_info(form, kit)

        # Assign other related entities
        self._assign_kit_entities(form, kit)

        # Assign kit competitions
        self._assign_kit_competitions(form, kit)

    def _log_kit_debug_info(self, form, kit):
        """Log debug information about kit and form data."""
        logger.info("Kit competitions: %s", kit.competition.all())
        logger.info(
            "Form competition data: %s",
            form.cleaned_data.get("competitions"),
        )
        logger.info(
            "Competition name from form: %s",
            form.cleaned_data.get("competition_name"),
        )
        logger.info(
            "Competition names from form: %s",
            form.cleaned_data.get("competition_names"),
        )

    def _assign_kit_entities(self, form, kit):
        """Assign related entities from kit to form instance."""
        # Check if form.instance has brand attribute (it might not exist yet)
        has_brand = hasattr(form.instance, "brand") and form.instance.brand_id is not None
        if not has_brand and kit.brand:
            form.instance.brand = kit.brand
            logger.info("Assigned brand from kit: %s", kit.brand.name)

        # Check if form.instance has club attribute (it might not exist yet)
        has_club = hasattr(form.instance, "club") and form.instance.club_id is not None
        if not has_club and kit.team:
            form.instance.club = kit.team
            logger.info("Assigned club from kit: %s", kit.team.name)

        # Check if form.instance has season attribute (it might not exist yet)
        has_season = hasattr(form.instance, "season") and form.instance.season_id is not None
        if not has_season and kit.season:
            form.instance.season = kit.season
            logger.info("Assigned season from kit: %s", kit.season.year)

    def _assign_kit_competitions(self, form, kit):
        """Assign competitions from kit to form instance."""
        if kit.competition.exists():
            competitions = kit.competition.all()
            logger.info(
                "Found %s competitions in kit: %s",
                competitions.count(),
                [c.name for c in competitions],
            )
            form.instance.competitions.set(competitions)
            logger.info("Assigned competitions from kit to jersey")
        else:
            logger.warning("No competitions found in kit")

    def _get_post_color_values(self):
        """Extract color values from POST data."""
        main_color_post = self.request.POST.get("main_color")
        secondary_colors_post = (
            self.request.POST.getlist("secondary_colors") if hasattr(self.request.POST, "getlist") else []
        )
        if not secondary_colors_post:
            secondary_colors_post = self.request.POST.get("secondary_colors")
            if secondary_colors_post and isinstance(secondary_colors_post, str):
                secondary_colors_post = [c.strip() for c in secondary_colors_post.split(",") if c.strip()]
        return main_color_post, secondary_colors_post

    def _is_string_list(self, value):
        """Check if value is a list of strings."""
        if not value:
            return False
        try:
            if hasattr(value, "__getitem__") and len(value) > 0:
                return isinstance(value[0], str)
        except (TypeError, IndexError, AttributeError):
            pass
        return False

    def _get_secondary_colors_from_sources(self, secondary_colors_post, form):
        """Get secondary colors from POST or form data."""
        if secondary_colors_post:
            return secondary_colors_post
        if hasattr(form.data, "getlist"):
            return form.data.getlist("secondary_colors")
        return form.data.get("secondary_colors", [])

    def _convert_secondary_colors_to_objects(self, secondary_colors_val):
        """Convert secondary colors list to Color objects."""
        from footycollect.collection.models import Color

        if isinstance(secondary_colors_val, str):
            secondary_colors_val = [c.strip() for c in secondary_colors_val.split(",") if c.strip()]

        color_objects = []
        for color in secondary_colors_val:
            if isinstance(color, str):
                color_obj, _created = Color.objects.get_or_create(
                    name__iexact=color.strip(),
                    defaults={"name": color.strip().upper()},
                )
                color_objects.append(color_obj)
            elif isinstance(color, Color):
                color_objects.append(color)
        return color_objects

    def _update_base_item_country(self, base_item, country_code_post, form):
        """Update BaseItem country if missing."""
        if base_item.country:
            return False

        logger.info("BaseItem has no country, trying to set it...")
        country_code = country_code_post
        logger.info("country_code from stored POST: %s", country_code)
        if not country_code:
            country_code = form.cleaned_data.get("country_code")
            logger.info("country_code from cleaned_data: %s", country_code)
        has_fkapi_data = hasattr(self, "fkapi_data") and self.fkapi_data and "team_country" in self.fkapi_data
        if not country_code and has_fkapi_data:
            country_code = self.fkapi_data["team_country"]
            logger.info("country_code from fkapi_data: %s", country_code)

        if not country_code:
            logger.warning("No country_code found in any source")
            return False

        from footycollect.core.models import Country

        try:
            country = Country.objects.get(code=country_code)
            base_item.country = country
            logger.info("Set country on BaseItem: %s (ID: %s)", country_code, country.id)
        except Country.DoesNotExist:
            logger.warning("Country not found: %s", country_code)
            return False
        except (ValueError, TypeError, AttributeError):
            logger.exception("Error setting country")
            return False
        else:
            return True

    def _update_base_item_main_color(self, base_item, main_color_post, form):
        """Update BaseItem main_color if missing."""
        from footycollect.collection.models import Color

        if base_item.main_color:
            return False

        logger.info("BaseItem has no main_color, trying to set it...")
        main_color = form.cleaned_data.get("main_color")
        logger.info("main_color from cleaned_data: %s", main_color)
        if not main_color and main_color_post:
            main_color_str = main_color_post
            logger.info("main_color_str from stored POST: %s", main_color_str)
            if main_color_str:
                try:
                    color_obj, _created = Color.objects.get_or_create(
                        name__iexact=main_color_str.strip(),
                        defaults={"name": main_color_str.strip().upper()},
                    )
                    main_color = color_obj
                    logger.info("Created/found Color object: %s (ID: %s)", color_obj.name, color_obj.id)
                except (ValueError, TypeError):
                    logger.exception("Error creating/finding main Color")

        if not main_color:
            logger.warning("No main_color found in any source")
            return False

        base_item.main_color = main_color
        logger.info("Set main_color on BaseItem: %s", main_color.name)
        return True

    def _process_secondary_colors_from_post(self, secondary_colors_post):
        """Process secondary colors from POST data into Color objects."""
        from footycollect.collection.models import Color

        if not secondary_colors_post:
            return []

        secondary_colors_raw = secondary_colors_post
        logger.info(
            "secondary_colors_raw from stored POST: %s (type: %s)",
            secondary_colors_raw,
            type(secondary_colors_raw),
        )

        if isinstance(secondary_colors_raw, str):
            secondary_colors_raw = [c.strip() for c in secondary_colors_raw.split(",") if c.strip()]
        elif not isinstance(secondary_colors_raw, list):
            secondary_colors_raw = []

        logger.info("Processed secondary_colors_raw: %s", secondary_colors_raw)
        if not secondary_colors_raw:
            return []

        color_objects = []
        for color_str in secondary_colors_raw:
            if isinstance(color_str, str) and color_str.strip():
                try:
                    color_obj, _created = Color.objects.get_or_create(
                        name__iexact=color_str.strip(),
                        defaults={"name": color_str.strip().upper()},
                    )
                    color_objects.append(color_obj)
                    logger.info("Created/found Color object: %s (ID: %s)", color_obj.name, color_obj.id)
                except (ValueError, TypeError):
                    logger.exception("Error creating/finding secondary Color")
        return color_objects

    def _update_base_item_secondary_colors(self, base_item, secondary_colors_post, form):
        """Update BaseItem secondary_colors if missing."""
        if base_item.secondary_colors.exists():
            return False

        logger.info("BaseItem has no secondary_colors, trying to set them...")
        secondary_colors = form.cleaned_data.get("secondary_colors", [])
        logger.info("secondary_colors from cleaned_data: %s", secondary_colors)

        if not secondary_colors and secondary_colors_post:
            secondary_colors = self._process_secondary_colors_from_post(secondary_colors_post)

        if not secondary_colors:
            logger.warning("No secondary_colors found in any source")
            return False

        base_item.secondary_colors.set(secondary_colors)
        logger.info("Set secondary_colors on BaseItem: %s", [c.name for c in secondary_colors])
        return True

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

        # Process additional competitions if they exist
        self._process_additional_competitions(form)

        return response

    def _create_kit_if_needed(self, jersey, form):
        """Create Kit if jersey doesn't have one."""
        if jersey.kit:
            return

        try:
            self._create_and_link_kit(jersey, form)
        except (ValueError, TypeError, AttributeError):
            logger.exception("Error creating Kit in _save_and_finalize")
            # Don't raise - allow jersey creation to continue without kit

    def _create_and_link_kit(self, jersey, form):
        """Create and link Kit to jersey."""
        from footycollect.collection.services.kit_service import KitService

        kit_service = KitService()
        kit_id = form.cleaned_data.get("kit_id")
        fkapi_data = getattr(form, "fkapi_data", {})
        fkapi_keys = list(fkapi_data.keys()) if fkapi_data else []
        logger.info(
            "Creating Kit in _save_and_finalize - kit_id: %s, fkapi_data keys: %s",
            kit_id,
            fkapi_keys,
        )
        kit = kit_service.get_or_create_kit_for_jersey(
            base_item=self.object,
            jersey=jersey,
            fkapi_data=fkapi_data,
            kit_id=kit_id,
        )
        jersey.kit = kit
        jersey.save()
        logger.info("Created/linked Kit %s to Jersey %s", kit.id, jersey.id)

        # If we have a kit with competitions, assign them to the jersey
        if jersey.kit and jersey.kit.competition.exists():
            competitions = jersey.kit.competition.all()
            self.object.competitions.add(*competitions)
            logger.info(
                "Added %s competitions from kit to jersey",
                competitions.count(),
            )

        # CORREGIDO: Guardar las competiciones del formulario en el ManyToManyField
        if hasattr(self, "competition") and self.competition:
            self.object.competitions.add(self.competition)
            logger.info("Added competition %s to jersey competitions", self.competition.name)

        # CORREGIDO: Procesar competiciones adicionales del formulario
        all_competitions = self.request.POST.get("all_competitions", "")
        if all_competitions and "," in all_competitions:
            competition_names = [name.strip() for name in all_competitions.split(",") if name.strip()]
            for comp_name in competition_names:
                try:
                    comp, created = Competition.objects.get_or_create(
                        name=comp_name,
                        defaults={"slug": slugify(comp_name)},
                    )
                    self.object.competitions.add(comp)
                    logger.info("Added additional competition %s to jersey", comp.name)
                except (ValueError, TypeError):
                    logger.exception("Error adding competition %s", comp_name)

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
