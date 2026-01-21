import logging

from django.utils.deprecation import MiddlewareMixin

STATUS_ERROR_MIN = 400
STATUS_ERROR_MAX_EXCLUSIVE = 600

security_logger = logging.getLogger("footycollect.security")


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add additional security-related HTTP headers."""

    def process_response(self, request, response):
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


class SecurityAuditMiddleware(MiddlewareMixin):
    """Log security-sensitive events for basic audit trails."""

    def process_request(self, request):
        if request.path == "/accounts/login/" and request.method == "POST":
            username = request.POST.get("login", "") or request.POST.get("username", "")
            ip_address = self._get_client_ip(request)
            security_logger.info(
                "Login attempt for user '%s' from IP %s",
                username,
                ip_address,
            )

        sensitive_prefixes = ("/admin/", "/api/", "/fkapi/")
        if request.path.startswith(sensitive_prefixes):
            user = getattr(request, "user", None)
            username = getattr(user, "username", "anonymous")
            ip_address = self._get_client_ip(request)
            security_logger.info(
                "Access to sensitive endpoint %s by user '%s' from IP %s",
                request.path,
                username,
                ip_address,
            )

    def process_response(self, request, response):
        if STATUS_ERROR_MIN <= response.status_code < STATUS_ERROR_MAX_EXCLUSIVE:
            user = getattr(request, "user", None)
            username = getattr(user, "username", "anonymous")
            ip_address = self._get_client_ip(request)
            security_logger.warning(
                "HTTP %s for path %s by user '%s' from IP %s",
                response.status_code,
                getattr(request, "path", "<unknown>"),
                username,
                ip_address,
            )
        return response

    def _get_client_ip(self, request):
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
