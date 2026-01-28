"""
Mixin for handling FKAPI data fetching and merging into request.POST.

This mixin provides methods to fetch kit data from FKAPI and merge it
into the request.POST data before form creation.
"""

import logging

from django.utils.text import slugify

from footycollect.collection.models import Competition

logger = logging.getLogger(__name__)


class FKAPIDataMixin:
    """Mixin for FKAPI data fetching and merging functionality."""

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
        self._merge_main_color(kit_data, request)
        self._merge_secondary_colors(kit_data, request)
        self._merge_country(kit_data, request)
        self._merge_competitions(kit_data, request)
        request._fkapi_kit_data = kit_data  # noqa: SLF001

    def _merge_main_color(self, kit_data, request):
        """Set main color from API if not already in POST."""
        if request.POST.get("main_color"):
            return

        primary_color = kit_data.get("primary_color")
        if primary_color and isinstance(primary_color, dict):
            main_color = primary_color.get("name", "")
        else:
            colors = kit_data.get("colors", [])
            main_color = colors[0].get("name", "") if colors else ""

        if main_color:
            request.POST["main_color"] = main_color
            logger.debug("Set main_color from API: %s", main_color)

    def _merge_secondary_colors(self, kit_data, request):
        """Set secondary colors from API if not already in POST."""
        has_secondary = (
            request.POST.getlist("secondary_colors")
            if hasattr(request.POST, "getlist")
            else request.POST.get("secondary_colors")
        )
        if has_secondary:
            return

        secondary_colors = self._extract_secondary_colors(kit_data)

        if secondary_colors:
            request.POST.setlist("secondary_colors", secondary_colors)
            logger.debug("Set secondary_colors from API: %s", secondary_colors)

    def _extract_secondary_colors(self, kit_data):
        """Extract secondary colors from kit_data (new or old format)."""
        secondary_color = kit_data.get("secondary_color")
        if secondary_color:
            if isinstance(secondary_color, list):
                return [c.get("name", "") for c in secondary_color if c.get("name")]
            if isinstance(secondary_color, dict):
                name = secondary_color.get("name", "")
                return [name] if name else []

        colors = kit_data.get("colors", [])
        if colors and len(colors) > 1:
            return [c.get("name", "") for c in colors[1:] if c.get("name")]
        return []

    def _merge_country(self, kit_data, request):
        """Set country from API if not already in POST."""
        if request.POST.get("country_code"):
            return

        team = kit_data.get("team", {})
        country = team.get("country", "")
        if country:
            request.POST["country_code"] = country
            logger.debug("Set country_code from API: %s", country)

    def _merge_competitions(self, kit_data, request):
        """Set competitions from API if not already in POST."""
        if request.POST.get("competitions"):
            return
        competitions = kit_data.get("competition", [])
        self._process_competitions_from_api(competitions, request)

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

        except (ValueError, TypeError, KeyError, AttributeError):
            logger.exception("Error fetching kit data")
