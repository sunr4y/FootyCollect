# Create your views here.

import logging

import requests
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .client import FKAPIClient

logger = logging.getLogger(__name__)


@require_GET
def search_clubs(request):
    query = request.GET.get("keyword", "")
    client = FKAPIClient()
    try:
        results = client.search_clubs(query)
        return JsonResponse({"results": results})
    except (requests.RequestException, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=500)
    except Exception:
        logger.exception("Unexpected error in search_clubs")
        return JsonResponse({"error": "Internal server error"}, status=500)


@require_GET
def get_kit_details(request, kit_id):
    client = FKAPIClient()
    try:
        kit_data = client.get_kit_details(kit_id)
        return JsonResponse(kit_data)
    except (requests.RequestException, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=500)
    except Exception:
        logger.exception("Unexpected error in get_kit_details")
        return JsonResponse({"error": "Internal server error"}, status=500)


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
    try:
        results = client.search_kits(query)
        return JsonResponse({"results": results})
    except (requests.RequestException, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=500)
    except Exception:
        logger.exception("Unexpected error in search_kits")
        return JsonResponse({"error": "Internal server error"}, status=500)


@require_GET
def get_club_seasons(request, club_id):
    """
    Endpoint to retrieve seasons for a given club.
    """
    client = FKAPIClient()
    try:
        results = client.get_club_seasons(club_id)
        return JsonResponse({"results": results})
    except (requests.RequestException, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=500)
    except Exception:
        logger.exception("Unexpected error in get_club_seasons")
        return JsonResponse({"error": "Internal server error"}, status=500)


@require_GET
def get_club_kits(request, club_id, season_id):
    """
    Endpoint to retrieve kits for a given club in a specific season.
    """
    client = FKAPIClient()
    try:
        results = client.get_club_kits(club_id, season_id)
        return JsonResponse({"results": results})
    except (requests.RequestException, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=500)
    except Exception:
        logger.exception("Unexpected error in get_club_kits")
        return JsonResponse({"error": "Internal server error"}, status=500)
