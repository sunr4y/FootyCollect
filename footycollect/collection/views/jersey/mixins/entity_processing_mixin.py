"""
Mixin for handling entity (brand, club, season, competition) processing.

This mixin provides methods to find or create entities from form data
and FKAPI data during jersey creation.
"""

import logging

from django.contrib import messages
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from footycollect.collection.models import Brand, Club, Competition, Season
from footycollect.core.models import Competition as CoreCompetition

logger = logging.getLogger(__name__)


class EntityProcessingMixin:
    """Mixin for entity processing functionality."""

    def _process_new_entities(self, form):
        """Process brand, club, season, and competition entities."""
        cleaned_data = form.cleaned_data
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
        except (ValueError, TypeError, AttributeError):
            logger.exception("Error creating brand %s", brand_name)
            messages.error(self.request, _("Error processing brand information"))
            raise

    def _find_or_create_brand(self, brand_name, cleaned_data):
        """Find existing brand or create new one."""
        brand = Brand.objects.filter(name=brand_name).first()
        if not brand:
            brand = Brand.objects.filter(name__iexact=brand_name).first()
        if not brand:
            brand = self._create_new_brand(brand_name, cleaned_data)
        else:
            self._update_brand_logo(brand, brand_name)
        return brand

    def _create_new_brand(self, brand_name, cleaned_data):
        """Create a new brand with logo from FKAPI or form."""
        brand_logo = ""
        if hasattr(self, "fkapi_data") and "brand_logo" in self.fkapi_data:
            brand_logo = self.fkapi_data["brand_logo"]
            logger.info("Using brand logo from FKAPI: %s", brand_logo)
        else:
            brand_logo = cleaned_data.get("logo", "")

        brand_logo_dark = ""
        if hasattr(self, "fkapi_data") and "brand_logo_dark" in self.fkapi_data:
            brand_logo_dark = self.fkapi_data["brand_logo_dark"]
            logger.info("Using brand logo_dark from FKAPI: %s", brand_logo_dark)
        else:
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
        except (ValueError, TypeError, AttributeError):
            logger.exception("Error creating club %s", club_name)
            messages.error(self.request, _("Error processing club information"))
            raise

    def _find_or_create_club(self, club_name, cleaned_data):
        """Find existing club or create new one."""
        club = Club.objects.filter(name=club_name).first()
        if club:
            logger.info("Found existing club with exact name: %s (ID: %s)", club.name, club.id)
            if hasattr(self, "fkapi_data") and "team_country" in self.fkapi_data:
                api_country = self.fkapi_data["team_country"]
                if club.country != api_country:
                    old_country = club.country
                    club.country = api_country
                    club.save()
                    logger.info("Updated club %s country from %s to %s", club.name, old_country, api_country)
        else:
            club = Club.objects.filter(name__iexact=club_name).first()
            if club:
                logger.info("Found existing club with case-insensitive name: %s (ID: %s)", club.name, club.id)
                if hasattr(self, "fkapi_data") and "team_country" in self.fkapi_data:
                    api_country = self.fkapi_data["team_country"]
                    if club.country != api_country:
                        old_country = club.country
                        club.country = api_country
                        club.save()
                        logger.info("Updated club %s country from %s to %s", club.name, old_country, api_country)
            else:
                club = self._create_new_club(club_name, cleaned_data)
        return club

    def _create_new_club(self, club_name, cleaned_data):
        """Create a new club with logo and country from FKAPI or form."""
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

        if not team_logo:
            team_logo = cleaned_data.get("logo", "")
        if not team_country:
            team_country = cleaned_data.get("country_code")

        if not team_country and hasattr(self, "kit") and self.kit and "team" in self.kit:
            team_country = self.kit["team"].get("country")
            logger.info("Using country from kit data as final fallback: %s", team_country)

        if not team_country:
            team_country = "ES"
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
        except (ValueError, TypeError, AttributeError):
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

            self._process_additional_competitions(form)
        except (ValueError, TypeError, AttributeError):
            logger.exception("Error creating competition %s", competition_name)
            messages.error(self.request, _("Error processing competition information"))
            raise

    def _find_or_create_competition(self, competition_name, cleaned_data):
        """Find existing competition or create new one."""
        competition = Competition.objects.filter(name=competition_name).first()
        if not competition:
            competition = Competition.objects.filter(name__iexact=competition_name).first()
        if not competition:
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
            competition_names = [name.strip() for name in all_competitions.split(",") if name.strip()]
            for comp_name in competition_names:
                comp, _created = CoreCompetition.objects.get_or_create(
                    name=comp_name,
                    defaults={"slug": slugify(comp_name)},
                )
                if hasattr(self.object, "competitions"):
                    self.object.competitions.add(comp)
                    logger.info("Added competition %s to jersey", comp.name)

    def _create_club_from_api_data(self, form):
        """Create club from API data."""
        from footycollect.core.models import Club

        country = "ES"
        logo = ""

        if hasattr(self, "kit") and self.kit and "team" in self.kit:
            country = self.kit["team"].get("country", "ES")
            logo = self.kit["team"].get("logo", "")

        if hasattr(self, "fkapi_data") and "team_logo" in self.fkapi_data:
            logo = self.fkapi_data["team_logo"]
            logger.info("Using team logo from fkapi_data: %s", logo)

        return Club.objects.create(
            name=form.data["club_name"],
            country=country,
            slug=form.data["club_name"].lower().replace(" ", "-"),
            logo=logo,
        )

    def _update_club_country(self, club):
        """Update club country from API data if different."""
        kit_data = None
        if hasattr(self, "fkapi_data") and self.fkapi_data and isinstance(self.fkapi_data, dict):
            if "team" in self.fkapi_data:
                kit_data = {"team": self.fkapi_data["team"]}
            elif "team_country" in self.fkapi_data:
                api_country = self.fkapi_data["team_country"]
                if club.country != api_country:
                    old_country = club.country
                    club.country = api_country
                    club.save()
                    logger.info("Updated club %s country from %s to %s", club.name, old_country, api_country)
                return
        elif hasattr(self, "kit") and self.kit:
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
