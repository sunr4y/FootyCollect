import logging

from dal import autocomplete
from django.utils.html import escape, format_html
from django_countries import countries

from .models import Brand, Club, Competition, Season

logger = logging.getLogger(__name__)

DEFAULT_LOGO_URL = "https://www.footballkitarchive.com/static/logos/not_found.png"
SEASON_PARTS_LENGTH = 2


class BrandAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete for brands using FKAPI external database."""

    MIN_QUERY_LENGTH = 2

    def get_queryset(self):  # noqa: C901
        from django.utils.text import slugify

        from footycollect.api.client import FKAPIClient

        if not self.q or len(self.q) < self.MIN_QUERY_LENGTH:
            return Brand.objects.none()

        # Search in external FKAPI
        client = FKAPIClient()
        api_results = client.search_brands(self.q)

        # For each result, get or create the brand in local database
        brand_ids = []
        for api_brand in api_results:
            brand_name = api_brand.get("name") if isinstance(api_brand, dict) else api_brand
            if not brand_name:
                continue

            # Get logo from API or use default
            logo = ""
            if isinstance(api_brand, dict):
                logo = api_brand.get("logo") or ""
            if not logo:
                logo = DEFAULT_LOGO_URL

            # Get logo_dark from API or use default
            logo_dark = ""
            if isinstance(api_brand, dict):
                logo_dark = api_brand.get("logo_dark") or ""
            if not logo_dark:
                logo_dark = DEFAULT_LOGO_URL

            brand, created = Brand.objects.get_or_create(
                name=brand_name,
                defaults={
                    "slug": slugify(brand_name),
                    "logo": logo,
                    "logo_dark": logo_dark,
                    "id_fka": api_brand.get("id") if isinstance(api_brand, dict) else None,
                },
            )

            # Update logo if brand already existed but didn't have one
            updated = False
            if not created:
                if not brand.logo or brand.logo == DEFAULT_LOGO_URL:
                    brand.logo = logo
                    updated = True
                if not brand.logo_dark or brand.logo_dark == DEFAULT_LOGO_URL:
                    brand.logo_dark = logo_dark
                    updated = True
                if updated:
                    brand.save(update_fields=["logo", "logo_dark"])

            brand_ids.append(brand.id)

        # Return queryset with found/created brands
        if brand_ids:
            return Brand.objects.filter(id__in=brand_ids).order_by("name")
        return Brand.objects.none()

    def get_result_label(self, item):
        """Return HTML with logo and name."""
        logo_html = ""
        if item.logo:
            logo_html = format_html(
                '<img src="{}" alt="{}" '
                'style="width: 20px; height: 20px; margin-right: 8px; '
                'object-fit: contain; vertical-align: middle;" />',
                escape(item.logo),
                escape(item.name),
            )
        return format_html(
            "{}{}",
            logo_html,
            escape(item.name),
        )

    def get_result_value(self, item):
        """Return the value for the result."""
        return item.id

    def get_results(self, context):
        """Override to return HTML formatted results for Select2."""
        results = []
        for item in context["object_list"]:
            html_label = self.get_result_label(item)
            results.append(
                {
                    "id": self.get_result_value(item),
                    "text": str(item),  # Plain text fallback
                    "html": str(html_label),  # HTML version for dropdown
                    "selected_text": str(html_label),  # HTML version for selected item
                },
            )
        return results


class CountryAutocomplete(autocomplete.Select2ListView):
    def get_list(self):
        countries_list = list(countries)

        if self.q:
            countries_list = [(code, name) for code, name in countries_list if self.q.lower() in str(name).lower()]

        return self.get_countries_list(countries_list)

    def get_countries_list(self, countries_list):
        return [
            (
                code,
                format_html(
                    '<i class="fi fi-{code}"></i> {name}',
                    code=escape(code.lower()),
                    name=escape(str(name)),
                ),
            )
            for code, name in countries_list
        ]

    def get_results(self, context):
        return super().get_results(context)

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ClubAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete for clubs using FKAPI external database."""

    MIN_QUERY_LENGTH = 2

    def get_queryset(self):  # noqa: C901, PLR0912
        from django.utils.text import slugify

        from footycollect.api.client import FKAPIClient

        if not self.q or len(self.q) < self.MIN_QUERY_LENGTH:
            return Club.objects.none()

        # Search in external FKAPI
        client = FKAPIClient()
        api_results = client.search_clubs(self.q)

        # For each result, get or create the club in local database
        club_ids = []
        for api_club in api_results:
            club_name = api_club.get("name") if isinstance(api_club, dict) else api_club
            if not club_name:
                continue

            # Extract country code if available
            country_code = None
            if isinstance(api_club, dict):
                country = api_club.get("country")
                if isinstance(country, dict):
                    country_code = country.get("code") or country.get("name")
                elif isinstance(country, str):
                    country_code = country

            # Get logo from API or use default
            logo = ""
            if isinstance(api_club, dict):
                logo = api_club.get("logo") or ""
            if not logo:
                logo = DEFAULT_LOGO_URL

            # Get logo_dark from API or use default
            logo_dark = ""
            if isinstance(api_club, dict):
                logo_dark = api_club.get("logo_dark") or ""
            if not logo_dark:
                logo_dark = DEFAULT_LOGO_URL

            club, created = Club.objects.get_or_create(
                name=club_name,
                defaults={
                    "slug": slugify(club_name),
                    "logo": logo,
                    "logo_dark": logo_dark,
                    "id_fka": api_club.get("id") if isinstance(api_club, dict) else None,
                    "country": country_code,
                },
            )

            # Update logo and country if club already existed but didn't have them
            updated = False
            if not created:
                if not club.logo or club.logo == DEFAULT_LOGO_URL:
                    club.logo = logo
                    updated = True
                if not club.logo_dark or club.logo_dark == DEFAULT_LOGO_URL:
                    club.logo_dark = logo_dark
                    updated = True
                if not club.country and country_code:
                    club.country = country_code
                    updated = True
                if updated:
                    club.save(update_fields=["logo", "logo_dark", "country"])

            club_ids.append(club.id)

        # Return queryset with found/created clubs
        if club_ids:
            return Club.objects.filter(id__in=club_ids).order_by("name")
        return Club.objects.none()

    def get_result_label(self, item):
        """Return HTML with logo and name."""
        logo_html = ""
        if item.logo:
            logo_html = format_html(
                '<img src="{}" alt="{}" '
                'style="width: 20px; height: 20px; margin-right: 8px; '
                'object-fit: contain; vertical-align: middle;" />',
                escape(item.logo),
                escape(item.name),
            )
        return format_html(
            "{}{}",
            logo_html,
            escape(item.name),
        )

    def get_result_value(self, item):
        """Return the value for the result."""
        return item.id

    def get_results(self, context):
        """Override to return HTML formatted results for Select2."""
        results = []
        for item in context["object_list"]:
            html_label = self.get_result_label(item)
            results.append(
                {
                    "id": self.get_result_value(item),
                    "text": str(item),  # Plain text fallback
                    "html": str(html_label),  # HTML version for dropdown
                    "selected_text": str(html_label),  # HTML version for selected item
                },
            )
        return results


class SeasonAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete for seasons using FKAPI external database."""

    MIN_QUERY_LENGTH = 2

    def get_queryset(self):  # noqa: C901, PLR0912
        from footycollect.api.client import FKAPIClient

        if not self.q or len(self.q) < self.MIN_QUERY_LENGTH:
            return Season.objects.none()

        # Search kits in external FKAPI to extract seasons
        client = FKAPIClient()
        api_kits = client.search_kits(self.q)

        # Extract unique seasons from kits
        seasons_dict = {}
        for kit in api_kits:
            season_data = kit.get("season") if isinstance(kit, dict) else None
            if not season_data:
                continue

            if isinstance(season_data, dict):
                season_year = season_data.get("year")
                season_id_fka = season_data.get("id")
            else:
                season_year = str(season_data)
                season_id_fka = None

            if season_year and season_year not in seasons_dict:
                # Parse year format (e.g., "2023-24" or "2023")
                first_year = season_year.split("-")[0] if "-" in season_year else season_year
                second_year = ""
                if "-" in season_year:
                    parts = season_year.split("-")
                    if len(parts) == SEASON_PARTS_LENGTH:
                        second_year = parts[1]

                seasons_dict[season_year] = {
                    "year": season_year,
                    "first_year": first_year,
                    "second_year": second_year,
                    "id_fka": season_id_fka,
                }

        # Also try searching clubs and getting their seasons
        api_clubs = client.search_clubs(self.q)
        for club in api_clubs[:5]:  # Limit to first 5 clubs to avoid too many requests
            if isinstance(club, dict) and club.get("id"):
                club_seasons = client.get_club_seasons(club.get("id"))
                for season_data in club_seasons:
                    if isinstance(season_data, dict):
                        season_year = season_data.get("year")
                        season_id_fka = season_data.get("id")
                        if season_year and season_year not in seasons_dict:
                            first_year = season_year.split("-")[0] if "-" in season_year else season_year
                            second_year = ""
                            if "-" in season_year:
                                parts = season_year.split("-")
                                if len(parts) == SEASON_PARTS_LENGTH:
                                    second_year = parts[1]

                            seasons_dict[season_year] = {
                                "year": season_year,
                                "first_year": first_year,
                                "second_year": second_year,
                                "id_fka": season_id_fka,
                            }

        # For each season, get or create in local database
        season_ids = []
        for season_info in seasons_dict.values():
            season, created = Season.objects.get_or_create(
                year=season_info["year"],
                defaults={
                    "first_year": season_info["first_year"],
                    "second_year": season_info["second_year"],
                    "id_fka": season_info["id_fka"],
                },
            )
            season_ids.append(season.id)

        # Return queryset with found/created seasons
        if season_ids:
            return Season.objects.filter(id__in=season_ids).order_by("-first_year", "-second_year")
        return Season.objects.none()

    def get_result_value(self, item):
        """Return the value for the result."""
        return item.id


class CompetitionAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete for competitions using FKAPI external database."""

    MIN_QUERY_LENGTH = 2

    def get_queryset(self):  # noqa: C901
        from django.utils.text import slugify

        from footycollect.api.client import FKAPIClient

        if not self.q or len(self.q) < self.MIN_QUERY_LENGTH:
            return Competition.objects.none()

        # Search in external FKAPI
        client = FKAPIClient()
        api_results = client.search_competitions(self.q)

        # For each result, get or create the competition in local database
        competition_ids = []
        for api_comp in api_results:
            comp_name = api_comp.get("name") if isinstance(api_comp, dict) else api_comp
            if not comp_name:
                continue

            # Get logo from API or use default
            logo = ""
            if isinstance(api_comp, dict):
                logo = api_comp.get("logo") or ""
            if not logo:
                logo = DEFAULT_LOGO_URL

            # Get logo_dark from API or use default
            logo_dark = ""
            if isinstance(api_comp, dict):
                logo_dark = api_comp.get("logo_dark") or ""
            if not logo_dark:
                logo_dark = DEFAULT_LOGO_URL

            competition, created = Competition.objects.get_or_create(
                name=comp_name,
                defaults={
                    "slug": slugify(comp_name),
                    "logo": logo,
                    "logo_dark": logo_dark,
                    "id_fka": api_comp.get("id") if isinstance(api_comp, dict) else None,
                },
            )

            # Update logo if competition already existed but didn't have one
            updated = False
            if not created:
                if not competition.logo or competition.logo == DEFAULT_LOGO_URL:
                    competition.logo = logo
                    updated = True
                if not competition.logo_dark or competition.logo_dark == DEFAULT_LOGO_URL:
                    competition.logo_dark = logo_dark
                    updated = True
                if updated:
                    competition.save(update_fields=["logo", "logo_dark"])

            competition_ids.append(competition.id)

        # Return queryset with found/created competitions
        if competition_ids:
            return Competition.objects.filter(id__in=competition_ids).order_by("name")
        return Competition.objects.none()

    def get_result_label(self, item):
        """Return HTML with logo and name."""
        logo_html = ""
        if item.logo:
            logo_html = format_html(
                '<img src="{}" alt="{}" '
                'style="width: 20px; height: 20px; margin-right: 8px; '
                'object-fit: contain; vertical-align: middle;" />',
                escape(item.logo),
                escape(item.name),
            )
        return format_html(
            "{}{}",
            logo_html,
            escape(item.name),
        )

    def get_result_value(self, item):
        """Return the value for the result."""
        return item.id

    def get_results(self, context):
        """Override to return HTML formatted results for Select2."""
        results = []
        for item in context["object_list"]:
            html_label = self.get_result_label(item)
            results.append(
                {
                    "id": self.get_result_value(item),
                    "text": str(item),  # Plain text fallback
                    "html": str(html_label),  # HTML version for dropdown
                    "selected_text": str(html_label),  # HTML version for selected item
                },
            )
        return results
