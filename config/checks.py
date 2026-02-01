"""
Django system checks for production environment validation.

These checks run automatically on Django startup and will fail fast
with clear error messages if production settings are misconfigured.
"""

import logging
import os

from django.conf import settings
from django.core.checks import Error, Warning, register
from django.db import DatabaseError, connection

logger = logging.getLogger(__name__)

MIN_SECRET_KEY_LENGTH = 50


@register(deploy=True)
def check_debug_disabled(app_configs, **kwargs):
    """
    Check that DEBUG is False in production.

    This is critical for security - DEBUG=True exposes sensitive information.
    """
    errors = []
    if settings.DEBUG:
        errors.append(
            Error(
                "DEBUG is enabled in production",
                hint="Set DEBUG=False in production settings. "
                "DEBUG=True exposes sensitive information and should never be used in production.",
                id="production.E001",
            ),
        )
    return errors


@register(deploy=True)
def check_secret_key_set(app_configs, **kwargs):
    """
    Check that SECRET_KEY is set and not using default value.

    SECRET_KEY is critical for security - it must be unique and secret.
    """
    errors = []
    secret_key = getattr(settings, "SECRET_KEY", None)

    if not secret_key:
        errors.append(
            Error(
                "SECRET_KEY is not set",
                hint=(
                    "Set DJANGO_SECRET_KEY environment variable. "
                    "Generate a new secret key using: "
                    "python -c 'from django.core.management.utils import get_random_secret_key; "
                    "print(get_random_secret_key())'"
                ),
                id="production.E002",
            ),
        )
    elif secret_key == "django-insecure-change-me":  # noqa: S105
        errors.append(
            Error(
                "SECRET_KEY is using default insecure value",
                hint="Generate a new secret key and set DJANGO_SECRET_KEY environment variable.",
                id="production.E003",
            ),
        )
    elif len(secret_key) < MIN_SECRET_KEY_LENGTH:
        errors.append(
            Warning(
                "SECRET_KEY appears to be too short",
                hint="SECRET_KEY should be at least 50 characters long for security.",
                id="production.W001",
            ),
        )

    return errors


@register(deploy=True)
def check_required_env_vars(app_configs, **kwargs):
    """
    Check that all required environment variables are set.

    Validates critical environment variables needed for production.
    """
    errors = []
    warnings = []

    required_vars = {
        "DJANGO_SECRET_KEY": "Required for Django security",
        "DATABASE_URL": "Required for database connection",
        "REDIS_URL": "Required for caching and Celery",
    }

    for var_name, description in required_vars.items():
        if not os.environ.get(var_name):
            errors.append(
                Error(
                    f"Required environment variable {var_name} is not set",
                    hint=f"{description}. Set {var_name} environment variable.",
                    id=f"production.E{len(errors) + 3:03d}",
                ),
            )

    optional_but_recommended = {
        "SENTRY_DSN": "Recommended for error tracking in production",
        "DJANGO_ALLOWED_HOSTS": "Required if not using default",
    }

    for var_name, description in optional_but_recommended.items():
        if not os.environ.get(var_name):
            warnings.append(
                Warning(
                    f"Environment variable {var_name} is not set",
                    hint=f"{description}. Consider setting {var_name}.",
                    id=f"production.W{len(warnings) + 2:03d}",
                ),
            )

    return errors + warnings


@register(deploy=True)
def check_database_connectivity(app_configs, **kwargs):
    """
    Check that database connection is working.

    Validates that Django can connect to the database on startup.
    """
    errors = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except (DatabaseError, Exception) as e:
        errors.append(
            Error(
                "Database connection failed",
                hint=f"Cannot connect to database: {e!s}. "
                "Check DATABASE_URL environment variable and database server status.",
                id="production.E010",
            ),
        )
    return errors


@register(deploy=True)
def check_redis_connectivity(app_configs, **kwargs):
    """
    Check that Redis connection is working.

    Validates that Django can connect to Redis for caching.
    """
    errors = []
    warnings = []

    if "django_redis" not in settings.INSTALLED_APPS:
        warnings.append(
            Warning(
                "django_redis is not in INSTALLED_APPS",
                hint="Redis caching may not work. Add 'django_redis' to INSTALLED_APPS if using Redis.",
                id="production.W010",
            ),
        )
        return warnings

    try:
        from django_redis import get_redis_connection

        redis_conn = get_redis_connection("default")
        redis_conn.ping()
    except ImportError:
        warnings.append(
            Warning(
                "django_redis is not installed",
                hint="Install django-redis package: pip install django-redis",
                id="production.W011",
            ),
        )
    except Exception as e:
        errors.append(
            Error(
                "Redis connection failed",
                hint=f"Cannot connect to Redis: {e!s}. "
                "Check REDIS_URL environment variable and Redis server status.",
                id="production.E011",
            ),
        )

    return errors + warnings


def _check_r2_credentials(errors, warnings):
    """Check Cloudflare R2 credentials."""
    required_vars = {
        "CLOUDFLARE_ACCESS_KEY_ID": "Required for R2 access",
        "CLOUDFLARE_SECRET_ACCESS_KEY": "Required for R2 access",
        "CLOUDFLARE_BUCKET_NAME": "Required for R2 bucket name",
    }

    for var_name, description in required_vars.items():
        if not os.environ.get(var_name):
            errors.append(
                Error(
                    f"Required Cloudflare R2 environment variable {var_name} is not set",
                    hint=f"{description}. Set {var_name} environment variable when using R2 storage.",
                    id=f"production.E{len(errors) + 20:03d}",
                ),
            )

    optional_vars = {
        "CLOUDFLARE_R2_ENDPOINT_URL": "Recommended for R2 endpoint specification",
        "CLOUDFLARE_R2_REGION": "Recommended for R2 region specification",
    }

    for var_name, description in optional_vars.items():
        if not os.environ.get(var_name):
            warnings.append(
                Warning(
                    f"Cloudflare R2 environment variable {var_name} is not set",
                    hint=f"{description}. Consider setting {var_name}.",
                    id=f"production.W{len(warnings) + 20:03d}",
                ),
            )

    return errors, warnings


def _check_aws_credentials(errors, warnings):
    """Check AWS S3 credentials."""
    required_vars = {
        "DJANGO_AWS_ACCESS_KEY_ID": "Required for S3 access",
        "DJANGO_AWS_SECRET_ACCESS_KEY": "Required for S3 access",
        "DJANGO_AWS_STORAGE_BUCKET_NAME": "Required for S3 bucket name",
    }

    for var_name, description in required_vars.items():
        if not os.environ.get(var_name):
            errors.append(
                Error(
                    f"Required AWS environment variable {var_name} is not set",
                    hint=f"{description}. Set {var_name} environment variable when using S3 storage.",
                    id=f"production.E{len(errors) + 20:03d}",
                ),
            )

    optional_vars = {
        "DJANGO_AWS_S3_REGION_NAME": "Recommended for S3 region specification",
    }

    for var_name, description in optional_vars.items():
        if not os.environ.get(var_name):
            warnings.append(
                Warning(
                    f"AWS environment variable {var_name} is not set",
                    hint=f"{description}. Consider setting {var_name}.",
                    id=f"production.W{len(warnings) + 20:03d}",
                ),
            )

    return errors, warnings


@register(deploy=True)
def check_aws_s3_credentials(app_configs, **kwargs):
    """
    Check that storage credentials are set if using S3-compatible storage (AWS S3 or Cloudflare R2).

    Only runs if S3 storage is configured in STORAGES setting.
    """
    errors = []
    warnings = []

    storages = getattr(settings, "STORAGES", {})
    using_s3 = False

    for storage_config in storages.values():
        backend = storage_config.get("BACKEND", "")
        if "s3" in backend.lower() or "S3Storage" in backend:
            using_s3 = True
            break

    if not using_s3:
        return []

    storage_backend = os.environ.get("STORAGE_BACKEND", "aws")

    if storage_backend == "r2":
        errors, warnings = _check_r2_credentials(errors, warnings)
    else:
        errors, warnings = _check_aws_credentials(errors, warnings)

    return errors + warnings


@register(deploy=True)
def check_allowed_hosts_configured(app_configs, **kwargs):
    """
    Check that ALLOWED_HOSTS is properly configured.

    ALLOWED_HOSTS must be set in production to prevent host header attacks.
    """
    errors = []
    warnings = []

    allowed_hosts = getattr(settings, "ALLOWED_HOSTS", [])

    if not allowed_hosts:
        errors.append(
            Error(
                "ALLOWED_HOSTS is empty",
                hint="Set ALLOWED_HOSTS in production settings. "
                "This prevents host header attacks. "
                "Set DJANGO_ALLOWED_HOSTS environment variable.",
                id="production.E030",
            ),
        )
    elif "*" in allowed_hosts:
        warnings.append(
            Warning(
                "ALLOWED_HOSTS contains wildcard '*'",
                hint="Using '*' in ALLOWED_HOSTS is insecure. Specify exact hostnames instead.",
                id="production.W030",
            ),
        )

    return errors + warnings


@register(deploy=True)
def check_ssl_settings(app_configs, **kwargs):
    """
    Check that SSL/HTTPS settings are properly configured.

    Validates security settings for production HTTPS.
    """
    warnings = []

    if not getattr(settings, "SECURE_SSL_REDIRECT", False):
        warnings.append(
            Warning(
                "SECURE_SSL_REDIRECT is disabled",
                hint="Enable SECURE_SSL_REDIRECT in production to force HTTPS connections.",
                id="production.W040",
            ),
        )

    if not getattr(settings, "SESSION_COOKIE_SECURE", False):
        warnings.append(
            Warning(
                "SESSION_COOKIE_SECURE is disabled",
                hint="Enable SESSION_COOKIE_SECURE in production to prevent session hijacking over HTTP.",
                id="production.W041",
            ),
        )

    if not getattr(settings, "CSRF_COOKIE_SECURE", False):
        warnings.append(
            Warning(
                "CSRF_COOKIE_SECURE is disabled",
                hint="Enable CSRF_COOKIE_SECURE in production to prevent CSRF attacks over HTTP.",
                id="production.W042",
            ),
        )

    return warnings
