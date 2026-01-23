# ruff: noqa: E501
from .base import *
from .base import INSTALLED_APPS, LOGGING, MIDDLEWARE, env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY")
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
# Disable caching in development (DEBUG=True) to see changes immediately
# and avoid cache-related debugging issues. Production uses Redis.
if DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        },
    }
else:
    # If DEBUG=False in local (shouldn't happen, but fallback to Redis)
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/1"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        },
    }


# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = "localhost"
# https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = 1025
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = "webmaster@localhost"

# django-debug-toolbar
# ------------------------------------------------------------------------------
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#prerequisites
INSTALLED_APPS += ["debug_toolbar"]
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
# https://django-debug-toolbar.readthedocs.io/en/latest/configuration.html#debug-toolbar-config
DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": [
        "debug_toolbar.panels.redirects.RedirectsPanel",
        # Disable profiling panel due to an issue with Python 3.12:
        # https://github.com/jazzband/django-debug-toolbar/issues/1875
        "debug_toolbar.panels.profiling.ProfilingPanel",
    ],
    "SHOW_TEMPLATE_CONTEXT": True,
}
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#internal-ips
INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]
if env("USE_DOCKER", default="no") == "yes":
    import socket

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]

# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ["django_extensions"]
# Celery
# ------------------------------------------------------------------------------

# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-eager-propagates
CELERY_TASK_EAGER_PROPAGATES = True
# Your stuff...
# ------------------------------------------------------------------------------

ACCOUNT_EMAIL_VERIFICATION = "none"

# MEDIA
# ------------------------------------------------------------------------------
STORAGE_BACKEND = env.str("STORAGE_BACKEND", default="local")

if STORAGE_BACKEND == "r2":
    # Cloudflare R2 settings
    INSTALLED_APPS += ["storages"]
    AWS_ACCESS_KEY_ID = env.str("CLOUDFLARE_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env.str("CLOUDFLARE_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env.str("CLOUDFLARE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = env.str("CLOUDFLARE_R2_ENDPOINT_URL", default="https://storage.developers.cloudflare.com")
    AWS_S3_REGION_NAME = env.str("CLOUDFLARE_R2_REGION", default="auto")
    AWS_QUERYSTRING_AUTH = False

    storage_domain = env.str(
        "CLOUDFLARE_R2_CUSTOM_DOMAIN",
        default=None,
    )
    if storage_domain:
        if storage_domain.startswith(("http://", "https://")):
            custom_domain = storage_domain.replace("https://", "").replace("http://", "")
        else:
            custom_domain = storage_domain
        AWS_S3_CUSTOM_DOMAIN = custom_domain
        MEDIA_URL = f"https://{custom_domain}/media/"
    else:
        endpoint_host = AWS_S3_ENDPOINT_URL.replace("https://", "").split("/")[0]
        AWS_S3_CUSTOM_DOMAIN = None
        MEDIA_URL = f"https://{endpoint_host}/{AWS_STORAGE_BUCKET_NAME}/media/"

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "location": "media",
                "file_overwrite": False,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    STATIC_URL = "/static/"
elif STORAGE_BACKEND == "aws":
    # AWS S3 settings
    INSTALLED_APPS += ["storages"]
    AWS_ACCESS_KEY_ID = env.str("DJANGO_AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env.str("DJANGO_AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env.str("DJANGO_AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env.str("DJANGO_AWS_S3_REGION_NAME", default=None)
    AWS_S3_CUSTOM_DOMAIN = env.str("DJANGO_AWS_S3_CUSTOM_DOMAIN", default=None)
    AWS_QUERYSTRING_AUTH = False
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "location": "media",
                "file_overwrite": False,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
    else:
        MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/media/"
    STATIC_URL = "/static/"
else:
    # Local storage settings (default)
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

# LOGGING
# ------------------------------------------------------------------------------
# Reduce boto3/botocore logging noise in development
LOGGING["loggers"].update(
    {
        "boto3": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "botocore": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "s3transfer": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "urllib3": {"level": "WARNING", "handlers": ["console"], "propagate": False},
    },
)
