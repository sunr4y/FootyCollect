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
