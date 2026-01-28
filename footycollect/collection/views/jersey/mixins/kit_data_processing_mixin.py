"""
Mixin for handling kit data processing from FKAPI.

This mixin provides methods to fetch, extract, and assign kit data
from FKAPI to form instances.
"""

import logging

from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from footycollect.api.client import FKAPIClient
from footycollect.collection.models import Kit

logger = logging.getLogger(__name__)


class KitDataProcessingMixin:
    """Mixin for kit data processing functionality."""

    def _process_kit_data(self, form, kit_id):
        """Process kit data from FKAPI and update form instance."""
        try:
            kit_data = self._fetch_kit_data_from_api(kit_id)
            if not kit_data:
                return

            if not hasattr(form, "fkapi_data"):
                form.fkapi_data = {}
            form.fkapi_data.update(kit_data)

            self._add_kit_id_to_description(form, kit_id)
            self._extract_logo_data_from_kit(kit_data)
            self._find_and_assign_existing_kit(form, kit_id)

        except (ValueError, TypeError, KeyError, AttributeError):
            logger.exception("Error processing kit data for ID %s", kit_id)

    def _fetch_kit_data_from_api(self, kit_id):
        """Fetch kit data from FKAPI."""
        client = FKAPIClient()

        kit_data = client.get_kit_details(kit_id)

        if kit_data is None:
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
        if not hasattr(self, "fkapi_data"):
            self.fkapi_data = {}

        self._extract_brand_logo(kit_data)
        self._extract_team_data(kit_data)
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
            if "logo" in team_data:
                team_logo_url = team_data["logo"]
                if team_logo_url and team_logo_url != "https://www.footballkitarchive.com/static/logos/not_found.png":
                    logger.info("Found team logo URL: %s", team_logo_url)
                    if not hasattr(self, "fkapi_data"):
                        self.fkapi_data = {}
                    self.fkapi_data["team_logo"] = team_logo_url

            if "country" in team_data:
                team_country = team_data["country"]
                if team_country:
                    logger.info("Found team country: %s", team_country)
                    if not hasattr(self, "fkapi_data"):
                        self.fkapi_data = {}
                    self.fkapi_data["team_country"] = team_country
                    logger.info("Stored team_country in fkapi_data: %s", self.fkapi_data)
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
        form.instance.kit = kit
        self.kit = kit
        logger.info(
            "Assigned existing kit to jersey: %s (ID: %s)",
            kit.name,
            kit.id,
        )

        self._log_kit_debug_info(form, kit)
        self._assign_kit_entities(form, kit)
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
        has_brand = hasattr(form.instance, "brand") and form.instance.brand_id is not None
        if not has_brand and kit.brand:
            form.instance.brand = kit.brand
            logger.info("Assigned brand from kit: %s", kit.brand.name)

        has_club = hasattr(form.instance, "club") and form.instance.club_id is not None
        if not has_club and kit.team:
            form.instance.club = kit.team
            logger.info("Assigned club from kit: %s", kit.team.name)

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
