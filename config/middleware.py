from django.utils.deprecation import MiddlewareMixin


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        from django.conf import settings

        if getattr(settings, "REFERRER_POLICY", None):
            response["Referrer-Policy"] = settings.REFERRER_POLICY
        if getattr(settings, "PERMISSIONS_POLICY", None):
            response["Permissions-Policy"] = settings.PERMISSIONS_POLICY
        return response
