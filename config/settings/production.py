# ruff: noqa: E501
import logging

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# Import production checks to register them
from config import checks  # noqa: F401

from .base import *  # NOSONAR (S2208) "This is a production settings file"
from .base import DATABASES, INSTALLED_APPS, MIDDLEWARE, SPECTACULAR_SETTINGS, _csp_sources, env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY")
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["footycollect.pro"])

# DATABASES
# ------------------------------------------------------------------------------
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Mimicing memcache behavior.
            # https://github.com/jazzband/django-redis#memcached-exceptions-behavior
            "IGNORE_EXCEPTIONS": True,
        },
    },
}

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-name
SESSION_COOKIE_NAME = "__Secure-sessionid"
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-name
CSRF_COOKIE_NAME = "__Secure-csrftoken"
# https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works #NOSONAR (S1135) "This is a TODO comment"
SECURE_HSTS_SECONDS = 60
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=True,
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF",
    default=True,
)

# STORAGES
# ------------------------------------------------------------------------------
# https://django-storages.readthedocs.io/en/latest/#installation
INSTALLED_APPS += ["storages"]

STORAGE_BACKEND = env.str("STORAGE_BACKEND", default="aws")

# Common settings for S3-compatible storage
AWS_QUERYSTRING_AUTH = False
_AWS_EXPIRY = 60 * 60 * 24 * 7
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": f"max-age={_AWS_EXPIRY}, s-maxage={_AWS_EXPIRY}, must-revalidate",
}
AWS_S3_MAX_MEMORY_SIZE = env.int(
    "DJANGO_AWS_S3_MAX_MEMORY_SIZE",
    default=100_000_000,  # 100MB
)

if STORAGE_BACKEND == "r2":
    # Cloudflare R2 settings
    # https://developers.cloudflare.com/r2/api/s3/api/
    AWS_ACCESS_KEY_ID = env("CLOUDFLARE_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("CLOUDFLARE_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("CLOUDFLARE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = env("CLOUDFLARE_R2_ENDPOINT_URL", default="https://<account-id>.r2.cloudflarestorage.com")
    AWS_S3_REGION_NAME = env("CLOUDFLARE_R2_REGION", default="auto")
    AWS_S3_CUSTOM_DOMAIN = env("CLOUDFLARE_R2_CUSTOM_DOMAIN", default=None)
    storage_domain = AWS_S3_CUSTOM_DOMAIN or AWS_S3_ENDPOINT_URL.replace("https://", "").split("/")[0]
elif STORAGE_BACKEND == "aws":
    # AWS S3 settings
    AWS_ACCESS_KEY_ID = env("DJANGO_AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("DJANGO_AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("DJANGO_AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("DJANGO_AWS_S3_REGION_NAME", default=None)
    AWS_S3_CUSTOM_DOMAIN = env("DJANGO_AWS_S3_CUSTOM_DOMAIN", default=None)
    storage_domain = AWS_S3_CUSTOM_DOMAIN or f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
else:
    error_msg = f"Invalid STORAGE_BACKEND: {STORAGE_BACKEND}. Must be 'aws' or 'r2'"
    raise ValueError(error_msg)

# Strip scheme from storage_domain so MEDIA_URL/STATIC_URL and storage .url never get "https://https://..."
if storage_domain and "://" in storage_domain:
    storage_domain = storage_domain.split("://", 1)[-1].split("/")[0]
# Use host-only domain for S3/R2 backend (django-storages builds "https://" + domain + path)
if STORAGE_BACKEND in {"r2", "aws"}:
    AWS_S3_CUSTOM_DOMAIN = storage_domain

storage_origin = f"https://{storage_domain}"
_CSP_SELF = "'self'"
img_src_default = (
    _CSP_SELF + " data: blob: https://www.gravatar.com https://cdn.footballkitarchive.com "
    "https://www.footballkitarchive.com https://cdn.jsdelivr.net " + storage_origin
)


def _csp_sources_with_storage(name: str, default: str) -> list:
    sources = _csp_sources(name, default)
    if storage_origin not in sources:
        sources.append(storage_origin)
    return sources


CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": _csp_sources("DJANGO_CSP_DEFAULT_SRC", _CSP_SELF),
        "script-src": _csp_sources_with_storage(
            "DJANGO_CSP_SCRIPT_SRC",
            _CSP_SELF + " 'unsafe-inline' 'unsafe-eval' "
            "https://cdnjs.cloudflare.com https://cdn.jsdelivr.net "
            "https://code.jquery.com https://unpkg.com " + storage_origin,
        ),
        "style-src": _csp_sources_with_storage(
            "DJANGO_CSP_STYLE_SRC",
            _CSP_SELF + " 'unsafe-inline' "
            "https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://fonts.googleapis.com " + storage_origin,
        ),
        "font-src": _csp_sources_with_storage(
            "DJANGO_CSP_FONT_SRC",
            _CSP_SELF + " data: "
            "https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://fonts.gstatic.com " + storage_origin,
        ),
        "img-src": _csp_sources("DJANGO_CSP_IMG_SRC", img_src_default),
        "connect-src": _csp_sources("DJANGO_CSP_CONNECT_SRC", _CSP_SELF + " " + storage_origin),
        "frame-ancestors": _csp_sources("DJANGO_CSP_FRAME_ANCESTORS", _CSP_SELF),
        "form-action": _csp_sources("DJANGO_CSP_FORM_ACTION", _CSP_SELF),
    },
}
if "csp.middleware.CSPMiddleware" not in MIDDLEWARE:
    MIDDLEWARE.insert(1, "csp.middleware.CSPMiddleware")

# STATIC & MEDIA
# ------------------------
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "location": "media",
            "file_overwrite": False,
        },
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "location": "static",
            "default_acl": "public-read",
        },
    },
}
MEDIA_URL = f"https://{storage_domain}/media/"
COLLECTFASTA_STRATEGY = "collectfasta.strategies.boto3.Boto3Strategy"
STATIC_URL = f"https://{storage_domain}/static/"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="footycollect <noreply@footycollect.pro>",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env(
    "DJANGO_EMAIL_SUBJECT_PREFIX",
    default="[footycollect] ",
)

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL regex.
ADMIN_URL = env("DJANGO_ADMIN_URL")

# Anymail
# ------------------------------------------------------------------------------
# https://anymail.readthedocs.io/en/stable/installation/#installing-anymail
INSTALLED_APPS += ["anymail"]
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
# https://anymail.readthedocs.io/en/stable/installation/#anymail-settings-reference
# https://anymail.readthedocs.io/en/stable/esps/sendgrid/
# Allow DJANGO_EMAIL_BACKEND override (e.g. console for demo) to avoid 500 on login when SendGrid is disabled
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="anymail.backends.sendgrid.EmailBackend",
)
ANYMAIL = {
    "SENDGRID_API_KEY": env("SENDGRID_API_KEY", default=""),
    "SENDGRID_API_URL": env("SENDGRID_API_URL", default="https://api.sendgrid.com/v3/"),
}

# django-compressor
# ------------------------------------------------------------------------------
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_ENABLED
COMPRESS_ENABLED = env.bool("COMPRESS_ENABLED", default=True)
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_STORAGE
COMPRESS_STORAGE = STORAGES["staticfiles"]["BACKEND"]
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_URL
COMPRESS_URL = STATIC_URL
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_FILTERS
COMPRESS_FILTERS = {
    "css": [
        "compressor.filters.css_default.CssAbsoluteFilter",
        "compressor.filters.cssmin.rCSSMinFilter",
    ],
    "js": ["compressor.filters.jsmin.JSMinFilter"],
}
# Collectfasta
# ------------------------------------------------------------------------------
# https://github.com/jasongi/collectfasta#installation
INSTALLED_APPS = ["collectfasta", *INSTALLED_APPS]

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        # Errors logged by the SDK itself
        "sentry_sdk": {"level": "ERROR", "handlers": ["console"], "propagate": False},
        "django.security.DisallowedHost": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

# Sentry
# ------------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN")
SENTRY_LOG_LEVEL = env.int("DJANGO_SENTRY_LOG_LEVEL", logging.INFO)

sentry_logging = LoggingIntegration(
    level=SENTRY_LOG_LEVEL,  # Capture info and above as breadcrumbs
    event_level=logging.ERROR,  # Send errors as events
)
integrations = [
    sentry_logging,
    DjangoIntegration(),
    CeleryIntegration(),
    RedisIntegration(),
]
sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=integrations,
    environment=env("SENTRY_ENVIRONMENT", default="production"),
    traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
)

# django-rest-framework
# -------------------------------------------------------------------------------
# Tools that generate code samples can use SERVERS to point to the correct domain
SPECTACULAR_SETTINGS["SERVERS"] = [
    {"url": "https://footycollect.pro", "description": "Production server"},
]
# Your stuff...
# ------------------------------------------------------------------------------
