# ruff: noqa: E501
from .base import *
from .base import INSTALLED_APPS, MIDDLEWARE, env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="furTE7DCnBfpabAj5ZVplhsjBmnVTcAydTu9d5Hr38AEmFAbC44vzhgV84LUwYMp",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
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
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_ACCESS_KEY_ID = env.str("CLOUDFLARE_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env.str("CLOUDFLARE_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env.str("CLOUDFLARE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = "https://storage.developers.cloudflare.com"
else:
    # Local storage settings
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
