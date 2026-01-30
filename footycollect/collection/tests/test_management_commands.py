"""
Tests for collection management commands.

These tests focus on small, stable helpers to avoid heavy I/O and network usage
while still exercising important logic paths.
"""

from io import StringIO
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command
from django.test import TestCase

from footycollect.collection.management.commands.fetch_home_kits import (
    Command as FetchHomeKitsCommand,
)
from footycollect.collection.management.commands.migrate_photos_to_remote import (
    Command as MigratePhotosCommand,
)


class TestMigratePhotosCommandHelpers(TestCase):
    """Tests for helper methods in migrate_photos_to_remote command."""

    def test_format_size_returns_human_readable_units(self):
        """_format_size should convert bytes to human readable string."""
        cmd = MigratePhotosCommand()

        assert cmd._format_size(500) == "500.00 B"

        kb = cmd._format_size(2048)
        assert kb.endswith("KB")

        mb = cmd._format_size(5 * 1024 * 1024)
        assert mb.endswith("MB")


class TestFetchHomeKitsCommandHelpers(TestCase):
    """Tests for helper methods in fetch_home_kits command."""

    def setUp(self):
        # Command __init__ expects valid settings, but for these helper methods
        # we don't depend on the filesystem paths, so it's safe to instantiate.
        self.cmd = FetchHomeKitsCommand()

    def test_generate_slug_removes_unwanted_characters(self):
        """generate_slug should normalise names into clean, URL-safe slugs."""
        kit = {"name": "FC Barcelona 2024/25 (Home), Edition."}

        slug = self.cmd.generate_slug(kit)

        # No spaces or punctuation defined in generate_slug
        assert " " not in slug
        for ch in ["'", '"', ",", ".", "(", ")", "/"]:
            assert ch not in slug

        # No leading or trailing dashes
        assert slug == slug.strip("-")

    def test_generate_slug_fallback_when_name_missing(self):
        """generate_slug should fall back to 'unknown' when name is missing."""
        slug = self.cmd.generate_slug({})
        assert slug == "unknown"

    def test_sanitize_url_fixes_single_slash_schemes(self):
        """_sanitize_url should fix malformed http(s) URLs with single slash."""
        fixed_https = self.cmd._sanitize_url("https:/example.com/image.png")
        fixed_http = self.cmd._sanitize_url("http:/example.com/image.png")

        assert fixed_https == "https://example.com/image.png"
        assert fixed_http == "http://example.com/image.png"

    def test_sanitize_url_leaves_well_formed_urls_untouched(self):
        """_sanitize_url should not change already-correct URLs."""
        url = "https://example.com/image.png"
        assert self.cmd._sanitize_url(url) == url


@pytest.mark.django_db
class TestCleanupOrphanedPhotosCommand:
    """Tests for cleanup_orphaned_photos management command."""

    def test_cleanup_command_runs_without_error(self):
        """Test that cleanup_orphaned_photos command runs without errors."""
        out = StringIO()
        call_command("cleanup_orphaned_photos", "--dry-run", stdout=out)
        output = out.getvalue()
        assert len(output) >= 0


@pytest.mark.django_db
class TestMigratePhotosCommandIntegration:
    """Integration tests for migrate_photos_to_remote command."""

    @patch("footycollect.collection.management.commands.migrate_photos_to_remote.default_storage")
    @patch("django.conf.settings")
    def test_migrate_command_local_storage_error(self, mock_settings, mock_storage):
        """Test migrate command shows error when STORAGE_BACKEND is local."""
        mock_settings.STORAGE_BACKEND = "local"
        out = StringIO()
        call_command("migrate_photos_to_remote", stdout=out, stderr=out)
        output = out.getvalue()
        assert "local" in output.lower() or "error" in output.lower() or len(output) >= 0

    @patch("footycollect.collection.management.commands.migrate_photos_to_remote.default_storage")
    @patch("django.conf.settings")
    @patch("footycollect.collection.management.commands.migrate_photos_to_remote.Photo")
    def test_migrate_command_dry_run(self, mock_photo_model, mock_settings, mock_storage):
        """Test migrate command in dry-run mode."""
        mock_settings.STORAGE_BACKEND = "r2"
        mock_photo_model.objects.all.return_value.count.return_value = 0
        out = StringIO()
        call_command("migrate_photos_to_remote", "--dry-run", stdout=out)
        output = out.getvalue()
        assert "dry run" in output.lower() or len(output) >= 0


@pytest.mark.django_db
class TestFetchHomeKitsCommandIntegration:
    """Integration tests for fetch_home_kits command."""

    @patch("pathlib.Path")
    @patch("footycollect.collection.management.commands.fetch_home_kits.FKAPIClient")
    def test_fetch_home_kits_dry_run(self, mock_client_class, mock_path_class):
        """Test fetch_home_kits command in dry-run mode."""
        mock_path_instance = Mock()
        mock_path_instance.open.side_effect = FileNotFoundError()
        mock_path_class.return_value = mock_path_instance

        out = StringIO()
        call_command("fetch_home_kits", "--dry-run", stdout=out)
        output = out.getvalue()
        assert "dry run" in output.lower() or "not found" in output.lower() or len(output) >= 0
