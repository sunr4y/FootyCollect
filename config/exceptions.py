from django.conf import settings
from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler

HTTP_TOO_MANY_REQUESTS = 429


def drf_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None and response.status_code == HTTP_TOO_MANY_REQUESTS and isinstance(exc, Throttled):
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        limit = rates.get("user", "100/hour") or rates.get("anon", "20/hour")
        response["X-RateLimit-Limit"] = limit
        response["X-RateLimit-Remaining"] = "0"
        if getattr(exc, "wait", None) is not None:
            response["Retry-After"] = str(int(exc.wait))
    return response
