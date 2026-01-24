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
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView

from footycollect.api.client import FKAPIClient
from footycollect.collection.forms import JerseyFKAPIForm
from footycollect.collection.models import BaseItem, Brand, Club, Competition, Jersey, Kit, Photo, Season
from footycollect.collection.services import get_collection_service

from .photo_views import PhotoProcessorMixin

logger = logging.getLogger(__name__)


class JerseyFKAPICreateView(PhotoProcessorMixin, LoginRequiredMixin, CreateView):
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

    def _make_post_mutable(self, request):
        """Make request.POST mutable for modification."""
        if hasattr(request.POST, "_mutable"):
            if not request.POST._mutable:  # noqa: SLF001
                request.POST = request.POST.copy()
                request.POST._mutable = True  # noqa: SLF001
        elif hasattr(request.POST, "copy"):
            request.POST = request.POST.copy()
            if hasattr(request.POST, "_mutable"):
                request.POST._mutable = True  # noqa: SLF001

    def _process_competitions_from_api(self, competitions, request):
        """Process and add competitions from API data to request.POST."""
        if not competitions:
            return

        competition_ids = []
        for comp in competitions:
            if not isinstance(comp, dict):
                continue

            comp_id_fka = comp.get("id")
            comp_name = comp.get("name")
            if not comp_name:
                continue

            competition = None
            if comp_id_fka:
                competition = Competition.objects.filter(id_fka=comp_id_fka).first()
            if not competition:
                competition = Competition.objects.filter(name=comp_name).first()
            if not competition:
                from django.utils.text import slugify

                competition, _created = Competition.objects.get_or_create(
                    name=comp_name,
                    defaults={
                        "id_fka": comp_id_fka,
                        "slug": slugify(comp_name),
                    },
                )
                logger.debug(
                    "Created/found competition: %s (ID: %s, id_fka: %s)",
                    competition.name,
                    competition.id,
                    competition.id_fka,
                )
            elif comp_id_fka and not competition.id_fka:
                competition.id_fka = comp_id_fka
                competition.save(update_fields=["id_fka"])

            competition_ids.append(str(competition.id))
            logger.debug(
                "Added competition to list: %s (ID: %s, id_fka: %s)",
                competition.name,
                competition.id,
                comp_id_fka,
            )

        if competition_ids:
            request.POST["competitions"] = ",".join(competition_ids)
            logger.info(
                "Set competitions from API: %s (count: %s)",
                request.POST["competitions"],
                len(competition_ids),
            )
        else:
            logger.warning("No competition IDs collected from API data: %s", competitions)

    def _merge_fkapi_data_to_post(self, kit_data, request):
        """Merge FKAPI data into request.POST."""
        # Set colors from API if not already in POST
        colors = kit_data.get("colors", [])
        if colors:
            if not request.POST.get("main_color"):
                main_color = colors[0].get("name", "")
                if main_color:
                    request.POST["main_color"] = main_color
                    logger.debug("Set main_color from API: %s", main_color)

            has_secondary = (
                request.POST.getlist("secondary_colors")
                if hasattr(request.POST, "getlist")
                else request.POST.get("secondary_colors")
            )
            if not has_secondary:
                secondary_colors = [c.get("name", "") for c in colors[1:] if c.get("name")]
                if secondary_colors:
                    request.POST.setlist("secondary_colors", secondary_colors)
                    logger.debug("Set secondary_colors from API: %s", secondary_colors)

        # Set country from API if not already in POST
        if not request.POST.get("country_code"):
            team = kit_data.get("team", {})
            country = team.get("country", "")
            if country:
                request.POST["country_code"] = country
                logger.debug("Set country_code from API: %s", country)

        # Set competitions from API if not already in POST
        if not request.POST.get("competitions"):
            competitions = kit_data.get("competition", [])
            self._process_competitions_from_api(competitions, request)

        # Store kit_data on request for later use
        request._fkapi_kit_data = kit_data  # noqa: SLF001

    def _fetch_and_merge_fkapi_data(self, request):
        """Fetch FKAPI data and merge it into request.POST."""
        kit_id = request.POST.get("kit_id")
        if not kit_id:
            return

        try:
            from footycollect.api.client import FKAPIClient

            client = FKAPIClient()
            try:
                kit_id_int = int(kit_id)
            except (ValueError, TypeError):
                logger.warning("Invalid kit_id: %s, skipping FKAPI fetch", kit_id)
                return

            kit_data = client.get_kit_details(kit_id_int) if kit_id_int else None

            if kit_data:
                logger.debug("Fetched kit data for kit_id %s", kit_id)
                self._merge_fkapi_data_to_post(kit_data, request)

        except Exception:
            logger.exception("Error fetching kit data")

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
            context["form"] = self.get_form()

        # Add options for Cotton components using services
        try:
            import json

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
        return context

    def _ensure_country_code_in_cleaned_data(self, form):
        """Ensure country_code is in cleaned_data."""
        country_code = form.cleaned_data.get("country_code")
        if not country_code:
            if form.data.get("country_code"):
                country_code = form.data.get("country_code")
                form.cleaned_data["country_code"] = country_code
                logger.info("Set country_code in cleaned_data from form.data: %s", country_code)
            elif hasattr(self, "fkapi_data") and "team_country" in self.fkapi_data:
                country_code = self.fkapi_data["team_country"]
                form.cleaned_data["country_code"] = country_code
                logger.info("Set country_code in cleaned_data from fkapi_data: %s", country_code)

    def _ensure_main_color_in_cleaned_data(self, form):
        """Ensure main_color is in cleaned_data."""
        from footycollect.collection.models import Color

        main_color = form.cleaned_data.get("main_color")
        if not main_color and form.data.get("main_color"):
            main_color_str = form.data.get("main_color")
            if main_color_str:
                color_obj, _created = Color.objects.get_or_create(
                    name__iexact=main_color_str.strip(),
                    defaults={"name": main_color_str.strip().upper()},
                )
                form.cleaned_data["main_color"] = color_obj
                logger.info(
                    "Set main_color in cleaned_data from form.data: %s -> %s",
                    main_color_str,
                    color_obj.name,
                )

    def _ensure_secondary_colors_in_cleaned_data(self, form):
        """Ensure secondary_colors are in cleaned_data."""
        from footycollect.collection.models import Color

        secondary_colors = form.cleaned_data.get("secondary_colors", [])
        if not secondary_colors:
            if hasattr(form.data, "getlist"):
                secondary_colors_raw = form.data.getlist("secondary_colors")
            else:
                secondary_colors_raw = form.data.get("secondary_colors", [])
                if isinstance(secondary_colors_raw, str):
                    secondary_colors_raw = [c.strip() for c in secondary_colors_raw.split(",") if c.strip()]
                elif not isinstance(secondary_colors_raw, list):
                    secondary_colors_raw = []

            if secondary_colors_raw:
                color_objects = []
                for color_str in secondary_colors_raw:
                    if isinstance(color_str, str) and color_str.strip():
                        color_obj, _created = Color.objects.get_or_create(
                            name__iexact=color_str.strip(),
                            defaults={"name": color_str.strip().upper()},
                        )
                        color_objects.append(color_obj)
                if color_objects:
                    form.cleaned_data["secondary_colors"] = color_objects
                    logger.info(
                        "Set secondary_colors in cleaned_data from form.data: %s",
                        [c.name for c in color_objects],
                    )

    def _ensure_form_cleaned_data(self, form):
        """Ensure country_code and colors are in cleaned_data before processing."""
        self._ensure_country_code_in_cleaned_data(form)
        self._ensure_main_color_in_cleaned_data(form)
        self._ensure_secondary_colors_in_cleaned_data(form)

    def _get_base_item_for_photos(self):
        """Get base_item for photo associations."""
        from footycollect.collection.models import BaseItem

        if isinstance(self.object, BaseItem):
            base_item = self.object
        else:
            base_item = getattr(self.object, "base_item", None)
            if base_item is None:
                base_item = BaseItem.objects.get(pk=self.object.pk)

        logger.info(
            "Using base_item ID: %s (type: %s) for photo associations. Jersey ID: %s, Jersey type: %s",
            base_item.id if base_item else None,
            type(base_item).__name__ if base_item else None,
            self.object.id,
            type(self.object).__name__,
        )
        return base_item

    def form_valid(self, form):
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
        except Exception:
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

            # Process external images
            self._process_external_images(form, base_item)

            # Process uploaded photos through the dropzone
            photo_ids = self.request.POST.get("photo_ids", "")
            if photo_ids:
                self._process_photo_ids(photo_ids, base_item)

            # Mark as not draft
            self.object.is_draft = False
            self.object.save()
            logger.info("Jersey marked as not draft")

            messages.success(
                self.request,
                _("Jersey added to your collection successfully!"),
            )

        except Exception as e:
            logger.exception("Error in form_valid")
            logger.exception("Full traceback:")
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

    def _update_club_country(self, club):
        """Update club country from API data if different."""
        # Check if we have API data (dict) or use fkapi_data
        kit_data = None
        if hasattr(self, "fkapi_data") and self.fkapi_data and isinstance(self.fkapi_data, dict):
            # Try to get team data from fkapi_data
            if "team" in self.fkapi_data:
                kit_data = {"team": self.fkapi_data["team"]}
            elif "team_country" in self.fkapi_data:
                # If we only have team_country, use it directly
                api_country = self.fkapi_data["team_country"]
                if club.country != api_country:
                    old_country = club.country
                    club.country = api_country
                    club.save()
                    logger.info("Updated club %s country from %s to %s", club.name, old_country, api_country)
                return
        elif hasattr(self, "kit") and self.kit:
            # Check if self.kit is a dict (API data) or a Kit model instance
            if isinstance(self.kit, dict) and "team" in self.kit:
                kit_data = self.kit

        if not kit_data:
            return

        api_country = kit_data["team"].get("country", "ES")
        if club.country != api_country:
            old_country = club.country
            club.country = api_country
            club.save()
            logger.info("Updated club %s country from %s to %s", club.name, old_country, api_country)

    def _create_club_from_api_data(self, form):
        """Create club from API data."""
        from footycollect.core.models import Club

        country = "ES"  # Default fallback
        logo = ""  # Default empty logo

        if hasattr(self, "kit") and self.kit and "team" in self.kit:
            country = self.kit["team"].get("country", "ES")
            logo = self.kit["team"].get("logo", "")

        # Also check fkapi_data for logo
        if hasattr(self, "fkapi_data") and "team_logo" in self.fkapi_data:
            logo = self.fkapi_data["team_logo"]
            logger.info("Using team logo from fkapi_data: %s", logo)

        return Club.objects.create(
            name=form.data["club_name"],
            country=country,
            slug=form.data["club_name"].lower().replace(" ", "-"),
            logo=logo,
        )

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

    def _fill_season_field(self, form):
        """Fill season field from API data."""
        if not form.data.get("season_name") or form.data.get("season"):
            return

        from footycollect.core.models import Season

        try:
            season = Season.objects.get(year=form.data["season_name"])
            form.data["season"] = season.id
        except Season.DoesNotExist:
            season = Season.objects.create(
                year=form.data["season_name"],
                first_year=form.data["season_name"][:4],
                second_year=form.data["season_name"][-2:],
            )
            form.data["season"] = season.id

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

        except Exception:
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

    def _ensure_country_in_cleaned_data(self, cleaned_data, country_code_post, form):
        """Ensure country_code is in cleaned_data."""
        if not cleaned_data.get("country_code"):
            if country_code_post:
                cleaned_data["country_code"] = country_code_post
                logger.info("Set country_code in cleaned_data from POST: %s", country_code_post)
            elif form.data.get("country_code"):
                cleaned_data["country_code"] = form.data.get("country_code")
                logger.info("Set country_code in cleaned_data from form.data: %s", form.data.get("country_code"))
            elif hasattr(self, "fkapi_data") and "team_country" in self.fkapi_data:
                cleaned_data["country_code"] = self.fkapi_data["team_country"]
                logger.info("Set country_code in cleaned_data from fkapi_data: %s", self.fkapi_data["team_country"])

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
        except Exception:
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
                except Exception:
                    logger.exception("Error creating/finding Color")

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
                except Exception:
                    logger.exception("Error creating/finding Color")
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
        except Exception:
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
        except Exception:
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
                except Exception:
                    logger.exception("Error adding competition %s", comp_name)

    def _process_new_entities(self, form):
        """
        Create or find related entities based on API data.
        Update the form with found or created entities.
        """
        cleaned_data = form.cleaned_data

        # Process each entity type
        self._process_brand_entity(form, cleaned_data)
        self._process_club_entity(form, cleaned_data)
        self._process_season_entity(form, cleaned_data)
        self._process_competition_entity(form, cleaned_data)

    def _process_brand_entity(self, form, cleaned_data):
        """Process brand entity creation or retrieval."""
        if not cleaned_data.get("brand_name"):
            return

        brand_name = cleaned_data.get("brand_name")
        try:
            brand = self._find_or_create_brand(brand_name, cleaned_data)
            form.instance.brand = brand
            logger.info("Set brand to %s", brand)
        except Exception:
            logger.exception("Error creating brand %s", brand_name)
            messages.error(self.request, _("Error processing brand information"))
            raise

    def _find_or_create_brand(self, brand_name, cleaned_data):
        """Find existing brand or create new one."""
        # Try to find the brand first by exact name
        brand = Brand.objects.filter(name=brand_name).first()
        if not brand:
            # If not found, search by similar name (case insensitive)
            brand = Brand.objects.filter(name__iexact=brand_name).first()
        if not brand:
            # If still not found, create it
            brand = self._create_new_brand(brand_name, cleaned_data)
        else:
            # Update existing brand with FKAPI logo if available
            self._update_brand_logo(brand, brand_name)
        return brand

    def _create_new_brand(self, brand_name, cleaned_data):
        """Create a new brand with logo from FKAPI or form."""
        # Get logo from FKAPI data if available
        brand_logo = ""
        if hasattr(self, "fkapi_data") and "brand_logo" in self.fkapi_data:
            brand_logo = self.fkapi_data["brand_logo"]
            logger.info("Using brand logo from FKAPI: %s", brand_logo)
        else:
            # No FKAPI data - try to get from form
            brand_logo = cleaned_data.get("logo", "")

        # Get logo_dark from FKAPI data if available
        brand_logo_dark = ""
        if hasattr(self, "fkapi_data") and "brand_logo_dark" in self.fkapi_data:
            brand_logo_dark = self.fkapi_data["brand_logo_dark"]
            logger.info("Using brand logo_dark from FKAPI: %s", brand_logo_dark)
        else:
            # No FKAPI data - try to get from form
            brand_logo_dark = cleaned_data.get("logo_dark", "")

        brand = Brand.objects.create(
            name=brand_name,
            id_fka=cleaned_data.get("id_fka") if cleaned_data.get("id_fka") else None,
            slug=cleaned_data.get("slug") if cleaned_data.get("slug") else slugify(brand_name),
            logo=brand_logo,
            logo_dark=brand_logo_dark,
        )
        logger.info(
            "Created new brand: %s (ID: %s) with logo: %s, logo_dark: %s",
            brand_name,
            brand.id,
            brand_logo,
            brand_logo_dark,
        )
        return brand

    def _update_brand_logo(self, brand, brand_name):
        """Update existing brand with FKAPI logo and logo_dark if available."""
        updated = False
        update_fields = []

        if hasattr(self, "fkapi_data") and "brand_logo" in self.fkapi_data:
            brand_logo = self.fkapi_data["brand_logo"]
            if brand_logo and brand_logo != brand.logo:
                brand.logo = brand_logo
                update_fields.append("logo")
                updated = True
                logger.info("Updated existing brand %s with logo: %s", brand_name, brand_logo)

        if hasattr(self, "fkapi_data") and "brand_logo_dark" in self.fkapi_data:
            brand_logo_dark = self.fkapi_data["brand_logo_dark"]
            if brand_logo_dark and brand_logo_dark != brand.logo_dark:
                brand.logo_dark = brand_logo_dark
                update_fields.append("logo_dark")
                updated = True
                logger.info("Updated existing brand %s with logo_dark: %s", brand_name, brand_logo_dark)

        if updated:
            brand.save(update_fields=update_fields)

    def _process_club_entity(self, form, cleaned_data):
        """Process club entity creation or retrieval."""
        if not cleaned_data.get("club_name"):
            return

        club_name = cleaned_data.get("club_name")
        try:
            club = self._find_or_create_club(club_name, cleaned_data)
            form.instance.club = club
            logger.info("Set club to %s", club)
        except Exception:
            logger.exception("Error creating club %s", club_name)
            messages.error(self.request, _("Error processing club information"))
            raise

    def _find_or_create_club(self, club_name, cleaned_data):
        """Find existing club or create new one."""
        # Try to find the club first by exact name
        club = Club.objects.filter(name=club_name).first()
        if club:
            logger.info("Found existing club with exact name: %s (ID: %s)", club.name, club.id)
            # Update country if we have API data and it's different
            if hasattr(self, "fkapi_data") and "team_country" in self.fkapi_data:
                api_country = self.fkapi_data["team_country"]
                if club.country != api_country:
                    old_country = club.country
                    club.country = api_country
                    club.save()
                    logger.info("Updated club %s country from %s to %s", club.name, old_country, api_country)
        else:
            # If not found, search by similar name (case insensitive)
            club = Club.objects.filter(name__iexact=club_name).first()
            if club:
                logger.info("Found existing club with case-insensitive name: %s (ID: %s)", club.name, club.id)
                # Update country if we have API data and it's different
                if hasattr(self, "fkapi_data") and "team_country" in self.fkapi_data:
                    api_country = self.fkapi_data["team_country"]
                    if club.country != api_country:
                        old_country = club.country
                        club.country = api_country
                        club.save()
                        logger.info("Updated club %s country from %s to %s", club.name, old_country, api_country)
            else:
                # If still not found, create it
                club = self._create_new_club(club_name, cleaned_data)
        return club

    def _create_new_club(self, club_name, cleaned_data):
        """Create a new club with logo and country from FKAPI or form."""
        # Get logo and country from FKAPI data if available
        team_logo = ""
        team_country = None

        logger.info("=== DEBUGGING _create_new_club ===")
        logger.info("Club name: %s", club_name)
        logger.info("Has fkapi_data: %s", hasattr(self, "fkapi_data"))
        if hasattr(self, "fkapi_data"):
            logger.info("fkapi_data keys: %s", list(self.fkapi_data.keys()))
            logger.info("fkapi_data content: %s", self.fkapi_data)
        else:
            logger.warning("No fkapi_data found - this might be the issue!")

        if hasattr(self, "fkapi_data"):
            if "team_logo" in self.fkapi_data:
                team_logo = self.fkapi_data["team_logo"]
                logger.info("Using team logo from FKAPI: %s", team_logo)
            if "team_country" in self.fkapi_data:
                team_country = self.fkapi_data["team_country"]
                logger.info("Using team country from FKAPI: %s", team_country)

        # Fallback to form data if no FKAPI data
        if not team_logo:
            team_logo = cleaned_data.get("logo", "")
        if not team_country:
            team_country = cleaned_data.get("country_code")

        # Final fallback - if still no country, try to get it from kit data
        if not team_country and hasattr(self, "kit") and self.kit and "team" in self.kit:
            team_country = self.kit["team"].get("country")
            logger.info("Using country from kit data as final fallback: %s", team_country)

        # Ultimate fallback
        if not team_country:
            team_country = "ES"  # Default fallback
            logger.warning("No country found, using default: %s", team_country)

        club = Club.objects.create(
            name=club_name,
            id_fka=cleaned_data.get("id_fka") if cleaned_data.get("id_fka") else None,
            slug=cleaned_data.get("slug") if cleaned_data.get("slug") else slugify(club_name),
            logo=team_logo,
            logo_dark=cleaned_data.get("logo_dark") if cleaned_data.get("logo_dark") else "",
            country=team_country,
        )
        logger.info(
            "Created new club: %s (ID: %s) with logo: %s, country: %s",
            club_name,
            club.id,
            team_logo,
            team_country,
        )
        return club

    def _process_season_entity(self, form, cleaned_data):
        """Process season entity creation or retrieval."""
        season_name = cleaned_data.get("season_name")
        if not season_name:
            return

        try:
            season, created = Season.objects.get_or_create(
                year=season_name,
                defaults={
                    "year": season_name,
                    "first_year": season_name.split("-")[0],
                    "second_year": season_name.split("-")[1] if "-" in season_name else "",
                },
            )
            form.instance.season = season
            logger.info("Set season to %s", season.year)
        except Exception:
            logger.exception("Error creating season %s", season_name)
            raise

    def _process_competition_entity(self, form, cleaned_data):
        """Process competition entity creation or retrieval."""
        if not cleaned_data.get("competition_name"):
            return

        competition_name = cleaned_data.get("competition_name")
        try:
            competition = self._find_or_create_competition(competition_name, cleaned_data)
            form.instance.competition = competition
            self.competition = competition
            logger.info("Set competition to %s (ID: %s)", competition.name, competition.id)

            # Process additional competitions if they exist
            self._process_additional_competitions(form)
        except Exception:
            logger.exception("Error creating competition %s", competition_name)
            messages.error(self.request, _("Error processing competition information"))
            raise

    def _find_or_create_competition(self, competition_name, cleaned_data):
        """Find existing competition or create new one."""
        # Try to find the competition first by exact name
        competition = Competition.objects.filter(name=competition_name).first()
        if not competition:
            # If not found, search by similar name (case insensitive)
            competition = Competition.objects.filter(name__iexact=competition_name).first()
        if not competition:
            # If still not found, create it
            competition = Competition.objects.create(
                name=competition_name,
                id_fka=cleaned_data.get("id_fka") if cleaned_data.get("id_fka") else None,
                slug=cleaned_data.get("slug") if cleaned_data.get("slug") else slugify(competition_name),
                logo=cleaned_data.get("logo") if cleaned_data.get("logo") else "",
                logo_dark=cleaned_data.get("logo_dark") if cleaned_data.get("logo_dark") else "",
            )
            logger.info("Created new competition: %s (ID: %s)", competition_name, competition.id)
        return competition

    def _process_additional_competitions(self, form):
        """Process additional competitions from form data."""
        from footycollect.core.models import Competition

        all_competitions = self.request.POST.get("all_competitions", "")
        if all_competitions and "," in all_competitions:
            competition_names = [name.strip() for name in all_competitions.split(",") if name.strip()]
            for comp_name in competition_names:
                comp, _created = Competition.objects.get_or_create(
                    name=comp_name,
                    defaults={"slug": slugify(comp_name)},
                )
                if hasattr(self.object, "competitions"):
                    self.object.competitions.add(comp)
                    logger.info("Added competition %s to jersey", comp.name)

    def _process_external_images(self, form, base_item=None):
        """
        Process external images provided by the API.
        Download images and associate them with the jersey.

        Args:
            form: The form instance
            base_item: The BaseItem instance to associate photos with (defaults to self.object.base_item)
        """
        if base_item is None:
            base_item = self.object.base_item if hasattr(self.object, "base_item") else self.object

        # Process main image if it exists
        main_img_url = form.cleaned_data.get("main_img_url")
        if main_img_url:
            try:
                photo = self._download_and_attach_image(base_item, main_img_url)
                if photo:
                    # Set as main image
                    photo.order = 0
                    photo.save()
                    logger.info("Main image saved with ID: %s", photo.id)
                    messages.success(
                        self.request,
                        _("Main image downloaded and attached successfully"),
                    )
            except Exception:
                logger.exception("Error downloading main image %s", main_img_url)
                messages.error(
                    self.request,
                    _("Error downloading main image"),
                )

        # Process additional external images
        external_urls = form.cleaned_data.get("external_image_urls", "")
        if external_urls:
            urls = external_urls.split(",")
            # Start from 1 to keep 0 for main image
            for i, url in enumerate(urls, start=1):
                clean_url = url.strip()
                if clean_url and clean_url != main_img_url:  # Avoid duplicates with main image
                    try:
                        photo = self._download_and_attach_image(base_item, clean_url)
                        if photo:
                            # Set order to maintain image order
                            photo.order = i
                            photo.save()
                    except Exception:
                        logger.exception("Error downloading image %s", clean_url)
                        messages.error(
                            self.request,
                            _("Error downloading image"),
                        )

    def _process_photo_ids(self, photo_ids, base_item=None):
        """
        Process photo IDs uploaded through the dropzone.
        Associate existing photos with the jersey.

        Args:
            photo_ids: String with JSON of photos or IDs separated by commas
            base_item: The BaseItem instance to associate photos with (defaults to self.object.base_item)
        """
        if base_item is None:
            base_item = self.object.base_item if hasattr(self.object, "base_item") else self.object

        try:
            # Parse photo IDs and external images
            photo_id_list, external_images, order_map = self._parse_photo_ids(photo_ids)
            if not photo_id_list and not external_images:
                return

            # Process external images first
            self._process_external_images_from_photo_ids(external_images, base_item)

            # Process existing photos
            self._associate_existing_photos(photo_id_list, order_map, base_item)

        except Exception:
            logger.exception("Error processing photo IDs")
            raise

    def _parse_photo_ids(self, photo_ids):
        """Parse photo_ids string and return photo IDs, external images, and order mapping."""
        if not isinstance(photo_ids, str):
            logger.warning("Unexpected photo_ids type: %s", type(photo_ids))
            return [], [], {}

        if not photo_ids.strip():
            logger.warning("Empty photo_ids string provided")
            return [], [], {}

        # Try to parse as JSON first
        try:
            photo_data = json.loads(photo_ids)
            logger.info("Parsed photo_ids as JSON: %s", photo_data)
            return self._extract_photo_data_from_json(photo_data)
        except json.JSONDecodeError:
            # If not JSON, assume it's a comma-separated list
            photo_id_list = [pid.strip() for pid in photo_ids.split(",") if pid.strip()]
            logger.info("Parsed photo_ids as comma-separated list: %s", photo_id_list)
            return photo_id_list, [], {}

    def _extract_photo_data_from_json(self, photo_data):
        """Extract photo IDs, external images, and order mapping from JSON data."""
        photo_id_list = []
        external_images = []
        order_map = {}

        for item in photo_data:
            if isinstance(item, dict):
                if "id" in item:
                    photo_id = str(item["id"])
                    photo_id_list.append(photo_id)
                    if "order" in item:
                        order_map[photo_id] = item["order"]
                elif "url" in item:
                    external_images.append(item)
            else:
                photo_id_list.append(str(item))

        return photo_id_list, external_images, order_map

    def _process_external_images_from_photo_ids(self, external_images, base_item=None):
        """Process external images from photo IDs data.

        Args:
            external_images: List of external image data dictionaries
            base_item: The BaseItem instance to associate photos with (defaults to self.object.base_item)
        """
        if base_item is None:
            base_item = self.object.base_item if hasattr(self.object, "base_item") else self.object

        if not external_images:
            return

        logger.info("Processing external images: %s", external_images)
        for img_data in external_images:
            try:
                photo = self._download_and_attach_image(base_item, img_data["url"])
                if photo:
                    photo.order = img_data.get("order", 0)
                    photo.save()
                    logger.info(
                        "External image downloaded and attached with ID: %s, order: %s",
                        photo.id,
                        photo.order,
                    )
            except Exception:
                logger.exception("Error downloading external image %s", img_data["url"])
                messages.error(self.request, _("Error downloading image"))

    def _associate_existing_photos(self, photo_id_list, order_map, base_item=None):
        """Associate existing photos with the jersey and set their order.

        Args:
            photo_id_list: List of photo IDs to associate
            order_map: Dictionary mapping photo IDs to their order
            base_item: The BaseItem instance to associate photos with (defaults to self.object.base_item)
        """
        if base_item is None:
            base_item = self.object.base_item if hasattr(self.object, "base_item") else self.object

        if not photo_id_list:
            return

        logger.info("Attempting to associate existing photos, IDs: %s", photo_id_list)

        # Ensure photo IDs are integers and unique
        try:
            photo_ids_int = list({int(pid) for pid in photo_id_list if str(pid).isdigit()})
        except Exception:
            logger.exception("Failed to parse photo IDs as integers (input was: %s)", photo_id_list)
            return

        if not photo_ids_int:
            logger.warning("No valid photo IDs found to associate.")
            return

        # Query for photos belonging to the current user
        photos = Photo.objects.filter(id__in=photo_ids_int, user=self.request.user)

        # Log how many photos were found
        logger.info("Found %d photos matching IDs %s for user %s", len(photos), photo_ids_int, self.request.user)

        if not photos.exists():
            logger.warning("No photos found with IDs %s for user %s", photo_ids_int, self.request.user)
            # Try without user filter to see if photos exist
            all_photos = Photo.objects.filter(id__in=photo_ids_int)
            logger.info("Total photos with these IDs (any user): %d", all_photos.count())
            return

        # Get ContentType for BaseItem model (not the instance)
        from footycollect.collection.models import BaseItem

        content_type = ContentType.objects.get_for_model(BaseItem)

        for photo in photos:
            # Associate the photo with the base_item (GenericRelation is on BaseItem, not Jersey)
            photo.content_type = content_type
            photo.object_id = base_item.id

            # Set the order
            photo.order = order_map.get(str(photo.id), photo.order or 0)

            photo.save()
            logger.info(
                "Associated photo %s with base_item %s (jersey %s), order: %s, content_type: %s",
                photo.id,
                base_item.id,
                self.object.id,
                photo.order,
                content_type,
            )

            # Verify the association was saved correctly
            photo.refresh_from_db()
            logger.info(
                "Photo %s after save - content_type_id: %s, object_id: %s",
                photo.id,
                photo.content_type_id,
                photo.object_id,
            )

        logger.info("Processed %s photos for jersey %s (base_item %s)", len(photos), self.object.id, base_item.id)

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
