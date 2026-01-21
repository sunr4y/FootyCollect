# Create your views here.

import logging

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .client import FKAPIClient

logger = logging.getLogger(__name__)


@require_GET
def search_clubs(request):
    query = request.GET.get("keyword", "")
    client = FKAPIClient()
    results = client.search_clubs(query)
    return JsonResponse({"results": results})


@require_GET
def get_kit_details(request, kit_id):
    client = FKAPIClient()
    kit_data = client.get_kit_details(kit_id)
    if kit_data is None:
        return JsonResponse(
            {"error": "Kit data temporarily unavailable"},
            status=503,
        )
    return JsonResponse(kit_data)


@require_GET
def search_kits(request):
    """
    Endpoint to search for kits as the user types.
    """
    query = request.GET.get("keyword", "")
    min_query_length = 3
    if len(query) < min_query_length:
        return JsonResponse({"results": []})

    client = FKAPIClient()
    results = client.search_kits(query)
    return JsonResponse({"results": results})


@require_GET
def get_club_seasons(request, club_id):
    """
    Endpoint to retrieve seasons for a given club.
    """
    client = FKAPIClient()
    results = client.get_club_seasons(club_id)
    return JsonResponse({"results": results})


@require_GET
def get_club_kits(request, club_id, season_id):
    """
    Endpoint to retrieve kits for a given club in a specific season.
    """
    client = FKAPIClient()
    results = client.get_club_kits(club_id, season_id)
    return JsonResponse({"results": results})


@require_GET
def search_brands(request):
    """Search brands from external FKAPI database."""
    query = request.GET.get("keyword", "")
    min_query_length = 2
    if len(query) < min_query_length:
        return JsonResponse({"results": []})

    client = FKAPIClient()
    results = client.search_brands(query)
    return JsonResponse({"results": results})


@require_GET
def search_competitions(request):
    """Search competitions from external FKAPI database."""
    query = request.GET.get("keyword", "")
    min_query_length = 2
    if len(query) < min_query_length:
        return JsonResponse({"results": []})

    client = FKAPIClient()
    results = client.search_competitions(query)
    return JsonResponse({"results": results})


@require_GET
def search_seasons(request):
    """Search seasons from external FKAPI database by searching kits."""
    query = request.GET.get("keyword", "")
    min_query_length = 2
    if len(query) < min_query_length:
        return JsonResponse({"results": []})

    client = FKAPIClient()
    seasons_dict = _build_seasons_from_kits(client, query)
    seasons_dict = _enrich_seasons_with_club_data(client, query, seasons_dict)
    results = list(seasons_dict.values())
    return JsonResponse({"results": results})


def _build_seasons_from_kits(client: FKAPIClient, query: str) -> dict:
    """Build initial seasons dict from kit search results."""
    api_kits = client.search_kits(query)

    seasons_dict: dict[str, dict] = {}
    for kit in api_kits:
        season_data = kit.get("season") if isinstance(kit, dict) else None
        if not season_data:
            continue

        if isinstance(season_data, dict):
            season_year = season_data.get("year")
            season_id = season_data.get("id")
        else:
            season_year = str(season_data)
            season_id = None

        if season_year and season_year not in seasons_dict:
            seasons_dict[season_year] = _build_season_entry(season_year, season_id)

    return seasons_dict


def _enrich_seasons_with_club_data(
    client: FKAPIClient,
    query: str,
    seasons_dict: dict,
) -> dict:
    """Enrich seasons dict with data from club seasons."""
    api_clubs = client.search_clubs(query)
    for club in api_clubs[:3]:
        if not isinstance(club, dict) or not club.get("id"):
            continue

        club_seasons = client.get_club_seasons(club.get("id"))
        for season_data in club_seasons:
            if not isinstance(season_data, dict):
                continue

            season_year = season_data.get("year")
            season_id = season_data.get("id")
            if season_year and season_year not in seasons_dict:
                seasons_dict[season_year] = _build_season_entry(season_year, season_id)

    return seasons_dict


def _build_season_entry(season_year: str, season_id: int | None) -> dict:
    """Create a normalized season entry dict."""
    return {
        "id": season_id,
        "name": season_year,
        "logo": None,
    }
