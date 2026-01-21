"""
Complex jersey-related views for the collection app.

This module contains the complex jersey views that were in the original views.py
file, including FKAPI integration and detailed jersey processing.
"""

import json
import logging

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

    def post(self, request, *args, **kwargs):
        """Override post to log POST requests and pre-process form data."""
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

        # Get the form and pre-process it before validation
        form = self.get_form()

        # Pre-process form data from API
        self._preprocess_form_data(form)

        # Check if form is valid after preprocessing
        if form.is_valid():
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
        """Add user to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
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

    def form_valid(self, form):
        """
        Processes the form when it is valid.
        Creates the necessary entities from the API data
        and handles external images.
        """
        logger.info("=== FORM_VALID CALLED ===")
        logger.info("Form is_valid: %s", form.is_valid())
        logger.info("Form errors: %s", form.errors)

        try:
            # Process related entities from the API
            self._process_new_entities(form)

            # Save and finalize
            response = self._save_and_finalize(form)

            # Refresh object from database to ensure base_item is available
            self.object.refresh_from_db()

            # Get base_item for photo associations (GenericRelation is on BaseItem)
            # Jersey uses MTI, so base_item is the BaseItem instance
            from footycollect.collection.models import BaseItem

            if isinstance(self.object, BaseItem):
                base_item = self.object
            else:
                # For Jersey, access through base_item attribute
                base_item = getattr(self.object, "base_item", None)
                if base_item is None:
                    # Fallback: try to get BaseItem directly
                    base_item = BaseItem.objects.get(pk=self.object.pk)

            logger.info(
                "Using base_item ID: %s (type: %s) for photo associations. Jersey ID: %s, Jersey type: %s",
                base_item.id if base_item else None,
                type(base_item).__name__ if base_item else None,
                self.object.id,
                type(self.object).__name__,
            )

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
            messages.error(self.request, _("Error creating jersey: {}").format(str(e)))
            return self.form_invalid(form)

        return response

    def _preprocess_form_data(self, form):
        """Pre-process form data from API before validation."""
        # Setup form instance
        self._setup_form_instance(form)

        # Process kit data if available
        kit_id = form.data.get("kit_id")
        if kit_id:
            self._process_kit_data(form, kit_id)

        # Fill form fields with API data
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
        if not (hasattr(self, "kit") and self.kit and "team" in self.kit):
            return

        api_country = self.kit["team"].get("country", "ES")
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
        """Extract brand logo from kit data."""
        if "brand" in kit_data and kit_data["brand"] and "logo" in kit_data["brand"]:
            brand_logo_url = kit_data["brand"]["logo"]
            if brand_logo_url and brand_logo_url != "https://www.footballkitarchive.com/static/logos/not_found.png":
                logger.info("Found brand logo URL: %s", brand_logo_url)
                self.fkapi_data["brand_logo"] = brand_logo_url

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
        if not form.instance.brand and kit.brand:
            form.instance.brand = kit.brand
            logger.info("Assigned brand from kit: %s", kit.brand.name)

        if not form.instance.club and kit.team:
            form.instance.club = kit.team
            logger.info("Assigned club from kit: %s", kit.team.name)

        if not form.instance.season and kit.season:
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

    def _save_and_finalize(self, form):
        """Save the jersey and finalize related assignments."""
        # Save the jersey
        response = super().form_valid(form)
        logger.info("Jersey saved with ID: %s", self.object.pk)

        # If we have a kit with competitions, assign them to the jersey
        if hasattr(self, "kit") and self.kit and self.kit.competition.exists():
            competitions = self.kit.competition.all()
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

        return response

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

        brand = Brand.objects.create(
            name=brand_name,
            id_fka=cleaned_data.get("id_fka") if cleaned_data.get("id_fka") else None,
            slug=cleaned_data.get("slug") if cleaned_data.get("slug") else slugify(brand_name),
            logo=brand_logo,
            logo_dark=cleaned_data.get("logo_dark") if cleaned_data.get("logo_dark") else "",
        )
        logger.info("Created new brand: %s (ID: %s) with logo: %s", brand_name, brand.id, brand_logo)
        return brand

    def _update_brand_logo(self, brand, brand_name):
        """Update existing brand with FKAPI logo if available."""
        if hasattr(self, "fkapi_data") and "brand_logo" in self.fkapi_data:
            brand_logo = self.fkapi_data["brand_logo"]
            if brand_logo and brand_logo != brand.logo:
                brand.logo = brand_logo
                brand.save(update_fields=["logo"])
                logger.info("Updated existing brand %s with logo: %s", brand_name, brand_logo)

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
        all_competitions = self.request.POST.get("all_competitions", "")
        if all_competitions and "," in all_competitions:
            # Save all competitions in description field
            form.instance.description = form.instance.description or ""
            form.instance.description += f"\nAdditional competitions: {all_competitions}"

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
