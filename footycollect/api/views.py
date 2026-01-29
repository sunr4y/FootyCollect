# Create your views here.

import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django_ratelimit.decorators import ratelimit

from .client import FKAPIClient

logger = logging.getLogger(__name__)

HTTP_TOO_MANY_REQUESTS = 429


FKAPI_RATE_LIMIT = "100/h"


def _rate_limited_response(request):
    accept = request.headers.get("Accept", "")
    headers = {
        "X-RateLimit-Limit": FKAPI_RATE_LIMIT,
        "X-RateLimit-Remaining": "0",
        "Retry-After": "3600",
    }
    if "application/json" in accept:
        resp = JsonResponse({"error": "Rate limit exceeded"}, status=HTTP_TOO_MANY_REQUESTS)
        for k, v in headers.items():
            resp[k] = v
        return resp
    resp = render(request, "429.html", status=HTTP_TOO_MANY_REQUESTS)
    for k, v in headers.items():
        resp[k] = v
    return resp


@ratelimit(key="ip", rate="100/h", method="GET")
@require_GET
def search_clubs(request):
    if getattr(request, "limited", False):
        return _rate_limited_response(request)
    query = request.GET.get("keyword", "")
    client = FKAPIClient()
    results = client.search_clubs(query)
    return JsonResponse({"results": results})


@ratelimit(key="ip", rate="100/h", method="GET")
@require_GET
def get_kit_details(request, kit_id):
    if getattr(request, "limited", False):
        return _rate_limited_response(request)
    client = FKAPIClient()
    kit_data = client.get_kit_details(kit_id)
    if kit_data is None:
        return JsonResponse(
            {"error": "Kit data temporarily unavailable"},
            status=503,
        )
    return JsonResponse(kit_data)


@ratelimit(key="ip", rate="100/h", method="GET")
@require_GET
def search_kits(request):
    """
    Endpoint to search for kits as the user types.
    """
    if getattr(request, "limited", False):
        return _rate_limited_response(request)
    query = request.GET.get("keyword", "")
    min_query_length = 3
    if len(query) < min_query_length:
        return JsonResponse({"results": []})

    client = FKAPIClient()
    results = client.search_kits(query)
    return JsonResponse({"results": results})


@ratelimit(key="ip", rate="100/h", method="GET")
@require_GET
def get_club_seasons(request, club_id):
    """
    Endpoint to retrieve seasons for a given club.
    """
    if getattr(request, "limited", False):
        return _rate_limited_response(request)
    client = FKAPIClient()
    results = client.get_club_seasons(club_id)
    return JsonResponse({"results": results})


@ratelimit(key="ip", rate="100/h", method="GET")
@require_GET
def get_club_kits(request, club_id, season_id):
    """
    Endpoint to retrieve kits for a given club in a specific season.
    """
    if getattr(request, "limited", False):
        return _rate_limited_response(request)
    client = FKAPIClient()
    results = client.get_club_kits(club_id, season_id)
    return JsonResponse({"results": results})


@ratelimit(key="ip", rate="100/h", method="GET")
@require_GET
def search_brands(request):
    """Search brands from external FKAPI database."""
    if getattr(request, "limited", False):
        return _rate_limited_response(request)
    query = request.GET.get("keyword", "")
    min_query_length = 2
    if len(query) < min_query_length:
        return JsonResponse({"results": []})

    client = FKAPIClient()
    results = client.search_brands(query)
    return JsonResponse({"results": results})


@ratelimit(key="ip", rate="100/h", method="GET")
@require_GET
def search_competitions(request):
    """Search competitions from external FKAPI database."""
    if getattr(request, "limited", False):
        return _rate_limited_response(request)
    query = request.GET.get("keyword", "")
    min_query_length = 2
    if len(query) < min_query_length:
        return JsonResponse({"results": []})

    client = FKAPIClient()
    results = client.search_competitions(query)
    return JsonResponse({"results": results})


@ratelimit(key="ip", rate="100/h", method="GET")
@require_GET
def search_seasons(request):
    """Search seasons from external FKAPI database by searching kits."""
    if getattr(request, "limited", False):
        return _rate_limited_response(request)
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


@ratelimit(key="ip", rate="100/h", method="GET")
@require_GET
def get_filter_options(request):
    """
    Get available filter options with item counts.

    Returns filter options (brands, clubs, competitions, etc.) with counts
    of how many items match each option, optionally filtered by other active filters.
    """
    if getattr(request, "limited", False):
        return _rate_limited_response(request)

    filter_type = request.GET.get("filter_type")
    if not filter_type:
        return JsonResponse({"error": "filter_type parameter is required"}, status=400)

    from django.db.models import Count, Q

    from footycollect.collection.models import Jersey
    from footycollect.core.models import Brand, Club, Competition, TypeK

    base_queryset = Jersey.objects.filter(base_item__is_private=False, base_item__is_draft=False)

    country = request.GET.get("country")
    if country:
        base_queryset = base_queryset.filter(Q(base_item__club__country=country) | Q(base_item__country=country))

    if filter_type == "brand":
        brands = (
            Brand.objects.filter(baseitem__jersey__in=base_queryset)
            .annotate(item_count=Count("baseitem__jersey", distinct=True))
            .filter(item_count__gt=0)
            .order_by("-item_count", "name")[:50]
        )
        results = [
            {"id": brand.id, "name": brand.name, "logo": brand.logo or "", "count": brand.item_count}
            for brand in brands
        ]
    elif filter_type == "club":
        clubs = (
            Club.objects.filter(baseitem__jersey__in=base_queryset)
            .annotate(item_count=Count("baseitem__jersey", distinct=True))
            .filter(item_count__gt=0)
            .order_by("-item_count", "name")[:50]
        )
        results = [
            {
                "id": club.id,
                "name": club.name,
                "logo": club.logo or "",
                "country": str(club.country) if club.country else None,
                "count": club.item_count,
            }
            for club in clubs
        ]
    elif filter_type == "competition":
        competitions = (
            Competition.objects.filter(collection_baseitem_competitions__jersey__in=base_queryset)
            .annotate(item_count=Count("collection_baseitem_competitions__jersey", distinct=True))
            .filter(item_count__gt=0)
            .order_by("-item_count", "name")[:50]
        )
        results = [
            {
                "id": comp.id,
                "name": comp.name,
                "logo": comp.logo or "",
                "count": comp.item_count,
            }
            for comp in competitions
        ]
    elif filter_type == "kit_type":
        kit_types = (
            TypeK.objects.filter(kit__jersey__in=base_queryset)
            .annotate(item_count=Count("kit__jersey", distinct=True))
            .filter(item_count__gt=0)
            .order_by("-item_count", "name")[:50]
        )
        results = [
            {
                "id": kt.id,
                "name": kt.name,
                "category": kt.category,
                "count": kt.item_count,
            }
            for kt in kit_types
        ]
    else:
        return JsonResponse({"error": f"Unknown filter_type: {filter_type}"}, status=400)

    return JsonResponse({"results": results})
