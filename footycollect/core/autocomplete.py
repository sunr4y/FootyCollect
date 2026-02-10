import logging

from dal import autocomplete
from django.utils.html import escape, format_html
from django_countries import countries

from .models import Brand, Club, Competition, Season

logger = logging.getLogger(__name__)

DEFAULT_LOGO_URL = "https://www.footballkitarchive.com/static/logos/not_found.png"
SEASON_PARTS_LENGTH = 2
AUTOCOMPLETE_LOGO_IMG = (
    '<img src="{}" alt="{}" '
    'style="width: 20px; height: 20px; margin-right: 8px; '
    'object-fit: contain; vertical-align: middle;" />'
)


def _logos_from_api(api_entity):
    if isinstance(api_entity, dict):
        logo = api_entity.get("logo") or ""
        logo_dark = api_entity.get("logo_dark") or ""
    else:
        logo = logo_dark = ""
    return logo or DEFAULT_LOGO_URL, logo_dark or DEFAULT_LOGO_URL


def _get_or_create_brand_from_api(api_brand):
    from django.utils.text import slugify

    brand_name = api_brand.get("name") if isinstance(api_brand, dict) else api_brand
    if not brand_name:
        return None
    logo, logo_dark = _logos_from_api(api_brand)
    id_fka = api_brand.get("id") if isinstance(api_brand, dict) else None
    slug = slugify(brand_name)

    if id_fka is not None:
        brand, created = Brand.objects.get_or_create(
            id_fka=id_fka,
            defaults={
                "name": brand_name,
                "slug": slug,
                "logo": logo,
                "logo_dark": logo_dark,
            },
        )
        if not created:
            update_fields = []
            if not brand.name:
                brand.name = brand_name
                update_fields.append("name")
            if not brand.slug:
                brand.slug = slug
                update_fields.append("slug")
            if not brand.logo or brand.logo == DEFAULT_LOGO_URL:
                brand.logo = logo
                update_fields.append("logo")
            if not brand.logo_dark or brand.logo_dark == DEFAULT_LOGO_URL:
                brand.logo_dark = logo_dark
                update_fields.append("logo_dark")
            if update_fields:
                brand.save(update_fields=update_fields)
        return brand

    brand, created = Brand.objects.get_or_create(
        name=brand_name,
        defaults={
            "slug": slug,
            "logo": logo,
            "logo_dark": logo_dark,
            "id_fka": id_fka,
        },
    )
    if not created:
        updated = False
        if not brand.logo or brand.logo == DEFAULT_LOGO_URL:
            brand.logo = logo
            updated = True
        if not brand.logo_dark or brand.logo_dark == DEFAULT_LOGO_URL:
            brand.logo_dark = logo_dark
            updated = True
        if updated:
            brand.save(update_fields=["logo", "logo_dark"])
    return brand


class Select2HtmlResultsMixin:
    def get_results(self, context):
        results = []
        for item in context["object_list"]:
            html_label = self.get_result_label(item)
            results.append(
                {
                    "id": self.get_result_value(item),
                    "text": str(item),
                    "html": str(html_label),
                    "selected_text": str(html_label),
                },
            )
        return results


class BrandAutocomplete(Select2HtmlResultsMixin, autocomplete.Select2QuerySetView):
    """Autocomplete for brands using FKAPI external database."""

    MIN_QUERY_LENGTH = 2

    def get_queryset(self):
        from footycollect.api.client import FKAPIClient

        if not self.q or len(self.q) < self.MIN_QUERY_LENGTH:
            return Brand.objects.none()
        client = FKAPIClient()
        api_results = client.search_brands(self.q)
        brand_ids = []
        for api_brand in api_results:
            brand = _get_or_create_brand_from_api(api_brand)
            if brand:
                brand_ids.append(brand.id)
        if not brand_ids:
            return Brand.objects.none()
        return Brand.objects.filter(id__in=brand_ids).order_by("name")

    def get_result_label(self, item):
        """Return HTML with logo and name."""
        logo_url = getattr(item, "logo_display_url", None) or getattr(item, "logo", "")
        logo_html = format_html(AUTOCOMPLETE_LOGO_IMG, escape(logo_url), escape(item.name)) if logo_url else ""
        return format_html("{}{}", logo_html, escape(item.name))

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

    def get_result_value(self, item):
        """Extract the primary value (country code) from Select2ListView items, which may be
        (code, html) tuples. Returns the first element for list/tuple, or the item itself."""
        if isinstance(item, (list, tuple)) and len(item) >= 1:
            return item[0]
        return item

    def get_results(self, context):
        return super().get_results(context)

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


def _country_code_from_api_club(api_club):
    if not isinstance(api_club, dict):
        return None
    country = api_club.get("country")
    if isinstance(country, dict):
        return country.get("code") or country.get("name")
    if isinstance(country, str):
        return country
    return None


def _get_or_create_club_from_api(api_club):
    from django.utils.text import slugify

    club_name = api_club.get("name") if isinstance(api_club, dict) else api_club
    if not club_name:
        return None
    logo, logo_dark = _logos_from_api(api_club)
    country_code = _country_code_from_api_club(api_club)
    id_fka = api_club.get("id") if isinstance(api_club, dict) else None
    club, created = Club.objects.get_or_create(
        name=club_name,
        defaults={
            "slug": slugify(club_name),
            "logo": logo,
            "logo_dark": logo_dark,
            "id_fka": id_fka,
            "country": country_code,
        },
    )
    if not created:
        updated = False
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
    return club


class ClubAutocomplete(Select2HtmlResultsMixin, autocomplete.Select2QuerySetView):
    """Autocomplete for clubs using FKAPI external database."""

    MIN_QUERY_LENGTH = 2

    def get_queryset(self):
        from footycollect.api.client import FKAPIClient

        if not self.q or len(self.q) < self.MIN_QUERY_LENGTH:
            return Club.objects.none()
        client = FKAPIClient()
        api_results = client.search_clubs(self.q)
        club_ids = []
        for api_club in api_results:
            club = _get_or_create_club_from_api(api_club)
            if club:
                club_ids.append(club.id)
        if not club_ids:
            return Club.objects.none()
        return Club.objects.filter(id__in=club_ids).order_by("name")

    def get_result_label(self, item):
        """Return HTML with logo and name."""
        logo_url = getattr(item, "logo_display_url", None) or getattr(item, "logo", "")
        logo_html = format_html(AUTOCOMPLETE_LOGO_IMG, escape(logo_url), escape(item.name)) if logo_url else ""
        return format_html("{}{}", logo_html, escape(item.name))

    def get_result_value(self, item):
        """Return the value for the result."""
        return item.id


def _parse_season_year_parts(season_year):
    parts = season_year.split("-")
    first_year = parts[0]
    second_year = parts[1] if len(parts) == SEASON_PARTS_LENGTH else ""
    return first_year, second_year


def _season_info_from_season_data(season_data):
    if isinstance(season_data, dict):
        season_year = season_data.get("year")
        season_id_fka = season_data.get("id")
    else:
        season_year = str(season_data) if season_data else None
        season_id_fka = None
    if not season_year:
        return None
    first_year, second_year = _parse_season_year_parts(season_year)
    return {"year": season_year, "first_year": first_year, "second_year": second_year, "id_fka": season_id_fka}


def _build_seasons_dict_from_kits(api_kits):
    out = {}
    for kit in api_kits:
        season_data = kit.get("season") if isinstance(kit, dict) else None
        if not season_data:
            continue
        info = _season_info_from_season_data(season_data)
        if info and info["year"] not in out:
            out[info["year"]] = info
    return out


def _add_club_seasons_to_dict(client, api_clubs, seasons_dict, limit=5):
    for club in api_clubs[:limit]:
        if not isinstance(club, dict) or not club.get("id"):
            continue
        for season_data in client.get_club_seasons(club.get("id")):
            info = _season_info_from_season_data(season_data) if isinstance(season_data, dict) else None
            if info and info["year"] not in seasons_dict:
                seasons_dict[info["year"]] = info


class SeasonAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete for seasons using FKAPI external database."""

    MIN_QUERY_LENGTH = 2

    def get_queryset(self):
        from footycollect.api.client import FKAPIClient

        if not self.q or len(self.q) < self.MIN_QUERY_LENGTH:
            return Season.objects.none()
        try:
            client = FKAPIClient()
            seasons_dict = _build_seasons_dict_from_kits(client.search_kits(self.q))
            _add_club_seasons_to_dict(client, client.search_clubs(self.q), seasons_dict)
            season_ids = []
            for season_info in seasons_dict.values():
                season, _ = Season.objects.get_or_create(
                    year=season_info["year"],
                    defaults={
                        "first_year": season_info["first_year"],
                        "second_year": season_info["second_year"],
                        "id_fka": season_info["id_fka"],
                    },
                )
                season_ids.append(season.id)
            if not season_ids:
                return Season.objects.none()
            return Season.objects.filter(id__in=season_ids).order_by("-first_year", "-second_year")
        except Exception as e:
            logger.exception(
                "Season autocomplete: FKAPI request failed (%s): %s",
                type(e).__name__,
                e,
            )
            return Season.objects.none()

    def get_result_value(self, item):
        """Return the value for the result."""
        return item.id


def _get_or_create_competition_from_api(api_comp):
    from django.utils.text import slugify

    comp_name = api_comp.get("name") if isinstance(api_comp, dict) else api_comp
    if not comp_name:
        return None
    logo, logo_dark = _logos_from_api(api_comp)
    id_fka = api_comp.get("id") if isinstance(api_comp, dict) else None
    competition, created = Competition.objects.get_or_create(
        name=comp_name,
        defaults={"slug": slugify(comp_name), "logo": logo, "logo_dark": logo_dark, "id_fka": id_fka},
    )
    if not created:
        updated = False
        if not competition.logo or competition.logo == DEFAULT_LOGO_URL:
            competition.logo = logo
            updated = True
        if not competition.logo_dark or competition.logo_dark == DEFAULT_LOGO_URL:
            competition.logo_dark = logo_dark
            updated = True
        if updated:
            competition.save(update_fields=["logo", "logo_dark"])
    return competition


class CompetitionAutocomplete(Select2HtmlResultsMixin, autocomplete.Select2QuerySetView):
    """Autocomplete for competitions using FKAPI external database."""

    MIN_QUERY_LENGTH = 2

    def get_queryset(self):
        from footycollect.api.client import FKAPIClient

        if not self.q or len(self.q) < self.MIN_QUERY_LENGTH:
            return Competition.objects.none()
        client = FKAPIClient()
        api_results = client.search_competitions(self.q)
        competition_ids = []
        for api_comp in api_results:
            comp = _get_or_create_competition_from_api(api_comp)
            if comp:
                competition_ids.append(comp.id)

        # Return queryset with found/created competitions
        if competition_ids:
            return Competition.objects.filter(id__in=competition_ids).order_by("name")
        return Competition.objects.none()

    def get_result_label(self, item):
        """Return HTML with logo and name."""
        logo_html = format_html(AUTOCOMPLETE_LOGO_IMG, escape(item.logo), escape(item.name)) if item.logo else ""
        return format_html("{}{}", logo_html, escape(item.name))

    def get_result_value(self, item):
        """Return the value for the result."""
        return item.id
