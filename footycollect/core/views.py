"""
Health check views for monitoring and deployment orchestration.
"""

import logging

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@require_GET
def health_check(request):
    """
    Basic health check endpoint.

    Returns 200 if the application is running.
    This endpoint is lightweight and does not check external services.
    """
    return JsonResponse({"status": "healthy"}, status=200)


@require_GET
def readiness_check(request):
    """
    Readiness check endpoint.

    Checks database and Redis connectivity.
    Returns 200 if all services are ready, 503 if any service is unavailable.
    """
    checks = {
        "database": False,
        "redis": False,
    }

    # Check database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = True
    except Exception:
        logger.exception("Database connectivity check failed")
        checks["database"] = False

    # Check Redis connectivity
    try:
        from django.core.cache import cache

        cache.set("health_check", "ok", 1)
        cache.get("health_check")
        checks["redis"] = True
    except ImportError:
        logger.warning("Redis cache backend not configured")
        checks["redis"] = False
    except Exception:
        logger.exception("Redis connectivity check failed")
        checks["redis"] = False

    # Determine overall status
    all_ready = all(checks.values())
    status_code = 200 if all_ready else 503

    response_data = {
        "status": "ready" if all_ready else "not ready",
        "checks": checks,
    }

    return JsonResponse(response_data, status=status_code)
