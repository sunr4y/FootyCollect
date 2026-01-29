"""
With these settings, tests run faster.
"""

import logging

from .base import *
from .base import TEMPLATES, env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="joeulw13SVVTuChFQWvVzerXS6iYkZuoBcYDyZgl13RWvHUOySDAWT7Mr3QaqocX",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#test-runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# DEBUGGING FOR TEMPLATES
# ------------------------------------------------------------------------------
TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore[index]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
#
# Using SQLite for tests instead of PostgreSQL for the following reasons:
#
# 1. PERFORMANCE: SQLite in-memory database is significantly faster for tests
#    - No disk I/O operations
#    - No network overhead
#    - Faster test execution (crucial for CI/CD pipelines)
#
# 2. SIMPLICITY: No PostgreSQL-specific features used in this project
#    - No PostgreSQL extensions (pg_trgm, unaccent, etc.)
#    - No PostgreSQL-specific field types (ArrayField, JSONField, HStoreField, etc.)
#    - No PostgreSQL-specific functions (TrigramSimilarity, SearchVector, etc.)
#    - Only standard Django ORM queries with basic lookups (icontains, iexact)
#
# 3. COMPATIBILITY: All Django ORM features work identically
#    - ForeignKey, ManyToManyField relationships
#    - Model validation and constraints
#    - QuerySet operations and filtering
#    - Database transactions and atomic operations
#
# 4. ISOLATION: Each test gets a fresh database
#    - No test data pollution between tests
#    - No need for complex cleanup procedures
#    - Parallel test execution support
#
# 5. DEPLOYMENT: No external dependencies for testing
#    - No need to set up PostgreSQL for test environments
#    - Works in any environment (local, CI/CD, Docker)
#    - Reduces infrastructure complexity
#
# Note: Production and development environments still use PostgreSQL for:
# - Better performance with large datasets
# - Advanced features like full-text search (if needed in future)
# - Better concurrent access handling
# - Production-grade reliability and backup capabilities
#
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "http://media.testserver/"

# Football Kit Archive API Settings for Testing
# ------------------------------------------------------------------------------
try:
    FKA_API_IP = env("FKA_API_IP")
    API_KEY = env("API_KEY")
except (ValueError, TypeError, AttributeError) as e:
    logging.getLogger(__name__).debug("FKA API settings not available for tests: %s", e)

ALLOWED_EXTERNAL_IMAGE_HOSTS = [
    "cdn.footballkitarchive.com",
    "www.footballkitarchive.com",
    "example.com",
]

# CELERY
# ------------------------------------------------------------------------------
# Execute tasks synchronously during tests (no Redis/Celery worker needed)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# Your stuff...
# ------------------------------------------------------------------------------
