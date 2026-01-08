"""
Tests for production environment validation checks.
"""

import os
from unittest.mock import Mock, patch

from django.core.checks import Error, Warning
from django.db import DatabaseError

from config.checks import (
    check_allowed_hosts_configured,
    check_aws_s3_credentials,
    check_database_connectivity,
    check_debug_disabled,
    check_redis_connectivity,
    check_required_env_vars,
    check_secret_key_set,
    check_ssl_settings,
)


class TestCheckDebugDisabled:
    """Test DEBUG=False validation check."""

    @patch("config.checks.settings")
    def test_debug_enabled_raises_error(self, mock_settings):
        """Test that DEBUG=True raises an error."""
        mock_settings.DEBUG = True

        errors = check_debug_disabled(None)

        assert len(errors) == 1
        assert isinstance(errors[0], Error)
        assert errors[0].id == "production.E001"
        assert "DEBUG is enabled" in errors[0].msg

    @patch("config.checks.settings")
    def test_debug_disabled_no_error(self, mock_settings):
        """Test that DEBUG=False raises no error."""
        mock_settings.DEBUG = False

        errors = check_debug_disabled(None)

        assert len(errors) == 0


class TestCheckSecretKeySet:
    """Test SECRET_KEY validation check."""

    @patch("config.checks.settings")
    def test_secret_key_not_set_raises_error(self, mock_settings):
        """Test that missing SECRET_KEY raises an error."""
        mock_settings.SECRET_KEY = None

        errors = check_secret_key_set(None)

        assert len(errors) == 1
        assert isinstance(errors[0], Error)
        assert errors[0].id == "production.E002"
        assert "SECRET_KEY is not set" in errors[0].msg

    @patch("config.checks.settings")
    def test_secret_key_default_value_raises_error(self, mock_settings):
        """Test that default SECRET_KEY value raises an error."""
        mock_settings.SECRET_KEY = "django-insecure-change-me"

        errors = check_secret_key_set(None)

        assert len(errors) == 1
        assert isinstance(errors[0], Error)
        assert errors[0].id == "production.E003"
        assert "default insecure value" in errors[0].msg

    @patch("config.checks.settings")
    def test_secret_key_too_short_raises_warning(self, mock_settings):
        """Test that short SECRET_KEY raises a warning."""
        mock_settings.SECRET_KEY = "short"

        errors = check_secret_key_set(None)

        assert len(errors) == 1
        assert isinstance(errors[0], Warning)
        assert errors[0].id == "production.W001"
        assert "too short" in errors[0].msg

    @patch("config.checks.settings")
    def test_secret_key_valid_no_error(self, mock_settings):
        """Test that valid SECRET_KEY raises no error."""
        mock_settings.SECRET_KEY = "a" * 50

        errors = check_secret_key_set(None)

        assert len(errors) == 0


class TestCheckRequiredEnvVars:
    """Test required environment variables validation."""

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_required_vars_raises_errors(self):
        """Test that missing required env vars raise errors."""
        errors = check_required_env_vars(None)

        assert len(errors) >= 3  # noqa: PLR2004
        error_ids = [e.id for e in errors if isinstance(e, Error)]
        assert "production.E004" in error_ids or "production.E005" in error_ids

    @patch.dict(
        os.environ,
        {
            "DJANGO_SECRET_KEY": "test-secret",
            "DATABASE_URL": "postgresql://test",
            "REDIS_URL": "redis://test",
        },
        clear=True,
    )
    def test_all_required_vars_set_no_errors(self):
        """Test that all required env vars set raises no errors."""
        errors = [e for e in check_required_env_vars(None) if isinstance(e, Error)]

        assert len(errors) == 0


class TestCheckDatabaseConnectivity:
    """Test database connectivity check."""

    @patch("config.checks.connection")
    def test_database_connection_success(self, mock_connection):
        """Test successful database connection."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        errors = check_database_connectivity(None)

        assert len(errors) == 0

    @patch("config.checks.connection")
    def test_database_connection_failure(self, mock_connection):
        """Test database connection failure."""
        mock_connection.cursor.side_effect = DatabaseError("Connection failed")

        errors = check_database_connectivity(None)

        assert len(errors) == 1
        assert isinstance(errors[0], Error)
        assert errors[0].id == "production.E010"
        assert "Database connection failed" in errors[0].msg


class TestCheckRedisConnectivity:
    """Test Redis connectivity check."""

    @patch("config.checks.settings")
    def test_redis_not_installed_raises_warning(self, mock_settings):
        """Test that missing django_redis raises warning."""
        mock_settings.INSTALLED_APPS = []

        errors = check_redis_connectivity(None)

        assert len(errors) == 1
        assert isinstance(errors[0], Warning)
        assert errors[0].id == "production.W010"

    @patch("config.checks.settings")
    @patch("django_redis.get_redis_connection")
    def test_redis_connection_success(self, mock_get_redis, mock_settings):
        """Test successful Redis connection."""
        mock_settings.INSTALLED_APPS = ["django_redis"]
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_get_redis.return_value = mock_redis

        errors = check_redis_connectivity(None)

        assert len(errors) == 0

    @patch("config.checks.settings")
    @patch("django_redis.get_redis_connection")
    def test_redis_connection_failure(self, mock_get_redis, mock_settings):
        """Test Redis connection failure."""
        mock_settings.INSTALLED_APPS = ["django_redis"]
        mock_get_redis.side_effect = Exception("Redis connection failed")

        errors = check_redis_connectivity(None)

        assert len(errors) == 1
        assert isinstance(errors[0], Error)
        assert errors[0].id == "production.E011"
        assert "Redis connection failed" in errors[0].msg


class TestCheckAwsS3Credentials:
    """Test AWS S3 credentials validation."""

    @patch("config.checks.settings")
    def test_not_using_s3_no_checks(self, mock_settings):
        """Test that no checks run if not using S3."""
        mock_settings.STORAGES = {}

        errors = check_aws_s3_credentials(None)

        assert len(errors) == 0

    @patch.dict(os.environ, {}, clear=True)
    @patch("config.checks.settings")
    def test_s3_missing_credentials_raises_errors(self, mock_settings):
        """Test that missing S3 credentials raise errors."""
        mock_settings.STORAGES = {
            "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        }

        errors = [e for e in check_aws_s3_credentials(None) if isinstance(e, Error)]

        assert len(errors) >= 3  # noqa: PLR2004

    @patch.dict(
        os.environ,
        {
            "DJANGO_AWS_ACCESS_KEY_ID": "test-key",
            "DJANGO_AWS_SECRET_ACCESS_KEY": "test-secret",
            "DJANGO_AWS_STORAGE_BUCKET_NAME": "test-bucket",
        },
        clear=True,
    )
    @patch("config.checks.settings")
    def test_s3_credentials_set_no_errors(self, mock_settings):
        """Test that all S3 credentials set raises no errors."""
        mock_settings.STORAGES = {
            "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        }

        errors = [e for e in check_aws_s3_credentials(None) if isinstance(e, Error)]

        assert len(errors) == 0


class TestCheckAllowedHostsConfigured:
    """Test ALLOWED_HOSTS validation."""

    @patch("config.checks.settings")
    def test_allowed_hosts_empty_raises_error(self, mock_settings):
        """Test that empty ALLOWED_HOSTS raises error."""
        mock_settings.ALLOWED_HOSTS = []

        errors = check_allowed_hosts_configured(None)

        assert len(errors) == 1
        assert isinstance(errors[0], Error)
        assert errors[0].id == "production.E030"
        assert "ALLOWED_HOSTS is empty" in errors[0].msg

    @patch("config.checks.settings")
    def test_allowed_hosts_wildcard_raises_warning(self, mock_settings):
        """Test that wildcard in ALLOWED_HOSTS raises warning."""
        mock_settings.ALLOWED_HOSTS = ["*"]

        errors = check_allowed_hosts_configured(None)

        assert len(errors) == 1
        assert isinstance(errors[0], Warning)
        assert errors[0].id == "production.W030"
        assert "wildcard" in errors[0].msg

    @patch("config.checks.settings")
    def test_allowed_hosts_valid_no_error(self, mock_settings):
        """Test that valid ALLOWED_HOSTS raises no error."""
        mock_settings.ALLOWED_HOSTS = ["example.com"]

        errors = check_allowed_hosts_configured(None)

        assert len(errors) == 0


class TestCheckSslSettings:
    """Test SSL settings validation."""

    @patch("config.checks.settings")
    def test_ssl_redirect_disabled_raises_warning(self, mock_settings):
        """Test that disabled SSL redirect raises warning."""
        mock_settings.SECURE_SSL_REDIRECT = False

        errors = check_ssl_settings(None)

        assert len(errors) >= 1
        assert any(e.id == "production.W040" for e in errors)

    @patch("config.checks.settings")
    def test_session_cookie_secure_disabled_raises_warning(self, mock_settings):
        """Test that disabled session cookie secure raises warning."""
        mock_settings.SESSION_COOKIE_SECURE = False

        errors = check_ssl_settings(None)

        assert any(e.id == "production.W041" for e in errors)

    @patch("config.checks.settings")
    def test_csrf_cookie_secure_disabled_raises_warning(self, mock_settings):
        """Test that disabled CSRF cookie secure raises warning."""
        mock_settings.CSRF_COOKIE_SECURE = False

        errors = check_ssl_settings(None)

        assert any(e.id == "production.W042" for e in errors)

    @patch("config.checks.settings")
    def test_all_ssl_settings_enabled_no_warnings(self, mock_settings):
        """Test that all SSL settings enabled raises no warnings."""
        mock_settings.SECURE_SSL_REDIRECT = True
        mock_settings.SESSION_COOKIE_SECURE = True
        mock_settings.CSRF_COOKIE_SECURE = True

        errors = check_ssl_settings(None)

        assert len(errors) == 0


class TestChecksRegistered:
    """Test that checks are properly registered."""

    def test_checks_are_callable(self):
        """Test that all production check functions are callable."""
        from config import checks

        check_functions = [
            checks.check_debug_disabled,
            checks.check_secret_key_set,
            checks.check_required_env_vars,
            checks.check_database_connectivity,
            checks.check_redis_connectivity,
            checks.check_aws_s3_credentials,
            checks.check_allowed_hosts_configured,
            checks.check_ssl_settings,
        ]

        for check_func in check_functions:
            assert callable(check_func)
            result = check_func(None)
            assert isinstance(result, list)
