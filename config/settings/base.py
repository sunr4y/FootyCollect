# ruff: noqa: ERA001, E501
"""Base settings to build other settings files upon."""

import logging
import sys
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
# footycollect/
APPS_DIR = BASE_DIR / "footycollect"
env = environ.Env()
env.read_env(env.str("ENV_PATH", default=str(BASE_DIR / ".envs/.local/.postgres")))
env.read_env(str(BASE_DIR / ".envs/.local/.django"))

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=True)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(BASE_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "Europe/Madrid"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#languages
# from django.utils.translation import gettext_lazy as _
# LANGUAGES = [
#     ('en', _('English')),
#     ('es', _('Spanish')),
# ]
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(BASE_DIR / "locale")]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # "django.contrib.humanize", # Handy template tags
    "dal",
    "dal_select2",
    "unfold",
    "django.contrib.admin",
    "django.forms",
]
THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    # "django_celery_beat",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "drf_spectacular",
    "imagekit",
    "taggit",
    "django_cotton",
    "formtools",
]

LOCAL_APPS = [
    "footycollect.users",
    "footycollect.core",
    "footycollect.api",
    "footycollect.collection",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "footycollect.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "users:redirect"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "account_login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(BASE_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(APPS_DIR / "static")]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#dirs
        "DIRS": [str(APPS_DIR / "templates")],
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "footycollect.users.context_processors.allauth_settings",
            ],
            "loaders": [
                (
                    "django.template.loaders.cached.Loader",
                    [
                        "django_cotton.cotton_loader.Loader",
                        "django.template.loaders.filesystem.Loader",
                        "django.template.loaders.app_directories.Loader",
                    ],
                ),
            ],
            "builtins": [
                "django_cotton.templatetags.cotton",
            ],
        },
    },
]

COTTON_BASE_DIR = str(BASE_DIR / "templates/cotton")

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# Additional security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True


# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = "admin/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [("""sunr4y""", "sunr4ydev@gmail.com")]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
# https://cookiecutter-django.readthedocs.io/en/latest/settings.html#other-environment-settings
# Force the `admin` sign in process to go through the `django-allauth` workflow
DJANGO_ADMIN_FORCE_ALLAUTH = env.bool("DJANGO_ADMIN_FORCE_ALLAUTH", default=False)


# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
class UTF8StreamHandler(logging.StreamHandler):
    """StreamHandler that ensures UTF-8 encoding for Unicode characters."""

    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        super().__init__(stream)

    def emit(self, record):
        try:
            msg = self.format(record)
            if not isinstance(msg, str):
                msg = str(msg)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            try:
                msg = self.format(record)
                stream.write(msg.encode("utf-8", errors="replace").decode("utf-8", errors="replace") + self.terminator)
                self.flush()
            except (UnicodeError, OSError, ValueError):
                self.handleError(record)
        except (UnicodeError, OSError, ValueError):
            self.handleError(record)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "()": UTF8StreamHandler,
            "formatter": "verbose",
        },
    },
    "root": {"level": "DEBUG", "handlers": ["console"]},
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
        "django.request": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
        "footycollect.collection": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
        "footycollect.collection.views": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
        "footycollect.collection.forms": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
        "footycollect.collection.services": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

# Celery
# ------------------------------------------------------------------------------
# if USE_TZ:
#     # https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-timezone
#     CELERY_TIMEZONE = TIME_ZONE
# # https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-broker_url
# CELERY_BROKER_URL = env("CELERY_BROKER_URL")
# # https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-result_backend
# CELERY_RESULT_BACKEND = CELERY_BROKER_URL
# # https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-extended
# CELERY_RESULT_EXTENDED = True
# # https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-backend-always-retry
# # https://github.com/celery/celery/pull/6122
# CELERY_RESULT_BACKEND_ALWAYS_RETRY = True
# # https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-backend-max-retries
# CELERY_RESULT_BACKEND_MAX_RETRIES = 10
# # https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-accept_content
# CELERY_ACCEPT_CONTENT = ["json"]
# # https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-task_serializer
# CELERY_TASK_SERIALIZER = "json"
# # https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-result_serializer
# CELERY_RESULT_SERIALIZER = "json"
# # https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-time-limit
# # TODO: set to whatever value is adequate in your circumstances
# CELERY_TASK_TIME_LIMIT = 5 * 60
# # https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-soft-time-limit
# # TODO: set to whatever value is adequate in your circumstances
# CELERY_TASK_SOFT_TIME_LIMIT = 60
# # https://docs.celeryq.dev/en/stable/userguide/configuration.html#beat-scheduler
# CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# # https://docs.celeryq.dev/en/stable/userguide/configuration.html#worker-send-task-events
# CELERY_WORKER_SEND_TASK_EVENTS = True
# # https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-task_send_sent_event
# CELERY_TASK_SEND_SENT_EVENT = True
# django-allauth
# ------------------------------------------------------------------------------
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_AUTHENTICATION_METHOD = "username"
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_EMAIL_REQUIRED = True
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# Account lockout after failed login attempts
# New format: ACCOUNT_RATE_LIMITS replaces deprecated ACCOUNT_LOGIN_ATTEMPTS_LIMIT/TIMEOUT
# Format: "attempts/period" where period can be 's' (seconds), 'm' (minutes), 'h' (hours)
# 5 attempts per 5 minutes (300 seconds)
ACCOUNT_RATE_LIMITS = {
    "login_failed": "5/5m",
}
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_ADAPTER = "footycollect.users.adapters.CustomAccountAdapter"
# https://docs.allauth.org/en/latest/account/forms.html
ACCOUNT_FORMS = {"signup": "footycollect.users.forms.UserSignupForm"}
# https://docs.allauth.org/en/latest/socialaccount/configuration.html
SOCIALACCOUNT_ADAPTER = "footycollect.users.adapters.CustomSocialAccountAdapter"
# https://docs.allauth.org/en/latest/socialaccount/configuration.html
SOCIALACCOUNT_FORMS = {"signup": "footycollect.users.forms.UserSocialSignupForm"}

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
    },
}

# django-compressor
# ------------------------------------------------------------------------------
# https://django-compressor.readthedocs.io/en/latest/quickstart/#installation
INSTALLED_APPS += ["compressor"]
STATICFILES_FINDERS += ["compressor.finders.CompressorFinder"]
# django-rest-framework
# -------------------------------------------------------------------------------
# django-rest-framework - https://www.django-rest-framework.org/api-guide/settings/
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "100/hour",
        "anon": "20/hour",
    },
}

# django-cors-headers - https://github.com/adamchainz/django-cors-headers#setup
CORS_URLS_REGEX = r"^/api/.*$"

# By Default swagger ui is available only to admin user(s). You can change permission classes to change that
# See more configuration options at https://drf-spectacular.readthedocs.io/en/latest/settings.html#settings
SPECTACULAR_SETTINGS = {
    "TITLE": "FootyCollect API",
    "DESCRIPTION": """
    FootyCollect REST API Documentation

    This API provides programmatic access to the FootyCollect platform for managing
    football memorabilia collections.

    ## Authentication

    Most endpoints require authentication. Use token authentication by including
    the token in the Authorization header:

    ```
    Authorization: Token <your-token>
    ```

    ## Endpoints

    - `/api/` - Internal server APIs (DRF)
    - `/fkapi/` - External API proxy endpoints

    ## Rate Limiting

    API requests are rate-limited to prevent abuse. Contact support for higher limits.

    ## Support

    For API issues or questions, please open an issue on GitHub.
    """,
    "VERSION": "1.0.0",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
    "SCHEMA_PATH_PREFIX": "/api/",
    "COMPONENT_SPLIT_REQUEST": True,
    "COMPONENT_NO_READ_ONLY_REQUIRED": True,
    "SORT_OPERATIONS": False,
    "TAGS": [
        {"name": "items", "description": "Collection item operations"},
        {"name": "photos", "description": "Photo management"},
        {"name": "users", "description": "User management"},
        {"name": "fkapi", "description": "External API proxy endpoints"},
    ],
}
# ------------------------------------------------------------------------------

# Football Kit Archive API Settings
FKA_API_IP = env("FKA_API_IP")
API_KEY = env("API_KEY")

# Rotating Proxy Settings (for image downloads)
ROTATING_PROXY_URL = env("ROTATING_PROXY_URL", default="")
ROTATING_PROXY_USERNAME = env("ROTATING_PROXY_USERNAME", default="")
ROTATING_PROXY_PASSWORD = env("ROTATING_PROXY_PASSWORD", default="")

# Testing flag for conditional URL loading
TESTING = False
