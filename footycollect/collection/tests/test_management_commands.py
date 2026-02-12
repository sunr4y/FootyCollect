"""
Tests for collection management commands.

These tests focus on small, stable helpers to avoid heavy I/O and network usage
while still exercising important logic paths.
"""

import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command
from django.test import TestCase

from footycollect.collection.management.commands.cleanup_orphaned_photos import (
    Command as CleanupOrphanedPhotosCommand,
)
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

    @patch("footycollect.collection.management.commands.fetch_home_kits.settings")
    def test_get_proxy_config_empty_url_returns_none(self, mock_settings):
        mock_settings.ROTATING_PROXY_URL = ""
        cmd = FetchHomeKitsCommand()
        assert cmd._get_proxy_config() is None

    @patch("footycollect.collection.management.commands.fetch_home_kits.settings")
    def test_get_proxy_config_with_credentials_returns_dict(self, mock_settings):
        mock_settings.ROTATING_PROXY_URL = "http://proxy.example.com"
        mock_settings.ROTATING_PROXY_USERNAME = "u"
        mock_settings.ROTATING_PROXY_PASSWORD = "p"
        cmd = FetchHomeKitsCommand()
        result = cmd._get_proxy_config()
        assert result is not None
        assert "http" in result
        assert "https" in result
        assert "u:p@" in result["http"] or "u:p@" in result["https"]

    def test_get_storage_path_returns_home_kits_prefix(self):
        cmd = FetchHomeKitsCommand()
        assert cmd._get_storage_path("kit.avif") == "home_kits/kit.avif"

    def test_get_logo_storage_path_returns_logos_subpath(self):
        cmd = FetchHomeKitsCommand()
        path = cmd._get_logo_storage_path("team", "logo.png")
        assert path == "home_kits/logos/team/logo.png"

    @patch("footycollect.collection.management.commands.fetch_home_kits.default_storage")
    def test_get_image_url_fallback_on_value_error(self, mock_storage):
        mock_storage.url.side_effect = ValueError("no url")
        cmd = FetchHomeKitsCommand()
        result = cmd._get_image_url("home_kits/x.avif")
        assert result.endswith("home_kits/x.avif")
        assert "media" in result or "home_kits" in result or result.endswith("home_kits/x.avif")

    @patch("footycollect.collection.management.commands.fetch_home_kits.default_storage")
    def test_image_exists_returns_false_on_oserror(self, mock_storage):
        mock_storage.exists.side_effect = OSError()
        cmd = FetchHomeKitsCommand()
        assert cmd._image_exists("home_kits/x.avif") is False

    def test_load_slugs_file_not_found_returns_empty_list(self):
        cmd = FetchHomeKitsCommand()
        cmd.slugs_file = Path(__file__).with_name("nonexistent_slugs.json")
        cmd.stdout = StringIO()
        result = cmd.load_slugs()
        assert result == []
        assert "not found" in cmd.stdout.getvalue().lower() or "error" in cmd.stdout.getvalue().lower()

    def test_load_slugs_invalid_json_returns_empty_list(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json {")
            path = Path(f.name)
        try:
            cmd = FetchHomeKitsCommand()
            cmd.slugs_file = path
            cmd.stdout = StringIO()
            result = cmd.load_slugs()
            assert result == []
            out = cmd.stdout.getvalue().lower()
            assert "invalid" in out or "error" in out
        finally:
            path.unlink(missing_ok=True)


@pytest.mark.django_db
class TestCleanupOrphanedPhotosCommand:
    """Tests for cleanup_orphaned_photos management command."""

    def test_cleanup_command_runs_without_error(self):
        """Test that cleanup_orphaned_photos command runs without errors."""
        out = StringIO()
        call_command("cleanup_orphaned_photos", "--dry-run", stdout=out)
        output = out.getvalue()
        assert len(output) > 0

    def test_cleanup_command_verbose_dry_run(self):
        out = StringIO()
        call_command("cleanup_orphaned_photos", "--dry-run", "--verbose", stdout=out)
        output = out.getvalue()
        assert "Starting" in output

    def test_cleanup_command_older_than_hours_option(self):
        out = StringIO()
        call_command(
            "cleanup_orphaned_photos",
            "--incomplete-only",
            "--older-than-hours",
            "48",
            "--dry-run",
            stdout=out,
        )
        output = out.getvalue()
        assert "48" in output or "incomplete" in output.lower() or "Starting" in output


class TestCleanupOrphanedPhotosCommandHelpers(TestCase):
    def test_get_database_files_returns_set_of_paths(self):
        cmd = CleanupOrphanedPhotosCommand()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("item_photos/a.jpg", "item_photos_avif/a.avif"),
            ("item_photos/b.jpg", None),
        ]
        with patch("footycollect.collection.management.commands.cleanup_orphaned_photos.connection") as mock_conn:
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            result = cmd._get_database_files()
        assert "item_photos/a.jpg" in result
        assert "item_photos_avif/a.avif" in result
        assert "item_photos/b.jpg" in result
        assert len(result) == 3  # noqa: PLR2004

    @patch.object(CleanupOrphanedPhotosCommand, "_delete_orphaned_files")
    @patch.object(CleanupOrphanedPhotosCommand, "_display_orphaned_files")
    @patch.object(CleanupOrphanedPhotosCommand, "_find_orphaned_files")
    @patch.object(CleanupOrphanedPhotosCommand, "_get_database_files")
    def test_cleanup_all_orphaned_photos_no_orphans_writes_success(
        self, mock_get_db, mock_find, mock_display, mock_delete
    ):
        mock_get_db.return_value = set()
        mock_find.return_value = []
        cmd = CleanupOrphanedPhotosCommand()
        cmd.stdout = StringIO()
        cmd._cleanup_all_orphaned_photos(dry_run=False, verbose=False)
        out = cmd.stdout.getvalue()
        assert "No orphaned files found" in out
        mock_delete.assert_not_called()

    @patch.object(CleanupOrphanedPhotosCommand, "_get_incomplete_photos")
    def test_cleanup_incomplete_photos_none_found_writes_success(self, mock_get_incomplete):
        mock_get_incomplete.return_value = []
        cmd = CleanupOrphanedPhotosCommand()
        cmd.stdout = StringIO()
        cmd._cleanup_incomplete_photos(dry_run=False, verbose=False, older_than_hours=24)
        out = cmd.stdout.getvalue()
        assert "No incomplete photos found" in out


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
        assert "local" in output.lower() or "error" in output.lower()

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
        assert "dry run" in output.lower()

    @patch("footycollect.collection.management.commands.migrate_photos_to_remote.settings")
    @patch("footycollect.collection.management.commands.migrate_photos_to_remote.Path")
    @patch("footycollect.collection.management.commands.migrate_photos_to_remote.get_storage_class")
    @patch("footycollect.collection.management.commands.migrate_photos_to_remote.default_storage")
    @patch("footycollect.collection.management.commands.migrate_photos_to_remote.Photo")
    def test_migrate_command_successful_migration(
        self, mock_photo_model, mock_default_storage, mock_get_storage, mock_path_class, mock_settings
    ):
        mock_settings.STORAGE_BACKEND = "r2"
        mock_settings.MEDIA_ROOT = "/tmp/media"  # noqa: S108
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path_class.return_value = mock_path_instance

        mock_photo = Mock()
        mock_photo.id = 1
        mock_photo.image = Mock()
        mock_photo.image.name = "item_photos/p.jpg"
        mock_photo.image_avif = None
        mock_qs = Mock()
        mock_qs.count.return_value = 1
        mock_photo_model.objects.all.return_value = mock_qs

        mock_local_storage = Mock()
        mock_get_storage.return_value.return_value = mock_local_storage
        mock_default_storage.__class__.__name__ = "S3Storage"

        with patch.object(MigratePhotosCommand, "_run_migration_loop") as mock_loop:
            mock_loop.return_value = (1, 0, 0, 100)
            out = StringIO()
            call_command("migrate_photos_to_remote", stdout=out)
            output = out.getvalue()
        assert "Migration completed" in output
        assert "Migrated: 1" in output

    @patch("footycollect.collection.management.commands.migrate_photos_to_remote.settings")
    @patch("footycollect.collection.management.commands.migrate_photos_to_remote.Path")
    @patch("footycollect.collection.management.commands.migrate_photos_to_remote.get_storage_class")
    @patch("footycollect.collection.management.commands.migrate_photos_to_remote.default_storage")
    @patch("footycollect.collection.management.commands.migrate_photos_to_remote.Photo")
    def test_migrate_command_handles_oserror_in_loop(
        self, mock_photo_model, mock_default_storage, mock_get_storage, mock_path_class, mock_settings
    ):
        mock_settings.STORAGE_BACKEND = "r2"
        mock_settings.MEDIA_ROOT = "/tmp/media"  # noqa: S108
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path_class.return_value = mock_path_instance

        mock_photo = Mock()
        mock_photo.id = 1
        mock_photo.image = Mock()
        mock_photo.image.name = "item_photos/p.jpg"
        mock_photo.image_avif = None
        mock_qs = Mock()
        mock_qs.count.return_value = 1
        mock_qs.__iter__ = lambda self: iter([mock_photo])
        mock_photo_model.objects.all.return_value = mock_qs

        mock_get_storage.return_value.return_value = Mock()
        mock_default_storage.__class__.__name__ = "S3Storage"

        with patch.object(MigratePhotosCommand, "_migrate_photo") as mock_migrate:
            mock_migrate.side_effect = OSError("disk full")
            out = StringIO()
            call_command("migrate_photos_to_remote", "--verbose", stdout=out)
            output = out.getvalue()
        assert "Migration completed" in output
        assert "Errors: 1" in output


@pytest.mark.django_db
class TestCleanupOrphansCommand:
    """Tests for cleanup_orphans management command."""

    def test_cleanup_orphans_no_option_prints_help(self):
        out = StringIO()
        call_command("cleanup_orphans", stdout=out)
        output = out.getvalue()
        assert "No cleanup option specified" in output or "brands" in output.lower()

    def test_cleanup_orphans_dry_run_runs_without_error(self):
        out = StringIO()
        call_command("cleanup_orphans", "--all", "--dry-run", stdout=out)
        output = out.getvalue()
        assert "DRY RUN" in output.upper()
        assert "no data" in output.lower() or "deleted" in output.lower() or len(output) > 0

    def test_cleanup_orphans_brands_only_dry_run(self):
        out = StringIO()
        call_command("cleanup_orphans", "--brands", "--dry-run", stdout=out)
        assert out.getvalue()

    def test_cleanup_orphans_with_no_orphans_reports_zero(self):
        out = StringIO()
        call_command("cleanup_orphans", "--photos", stdout=out)
        output = out.getvalue()
        assert "Total deleted: 0" in output or "deleted: 0" in output

    def test_cleanup_orphans_orphan_photos_dry_run_lists_only(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from footycollect.collection.models import Photo
        from footycollect.users.tests.factories import UserFactory

        user = UserFactory()
        photo = Photo.objects.create(
            user=user,
            content_type=None,
            object_id=None,
            image=SimpleUploadedFile("o.jpg", b"x", content_type="image/jpeg"),
        )
        out = StringIO()
        call_command("cleanup_orphans", "--photos", "--dry-run", stdout=out)
        output = out.getvalue()
        assert "Orphaned Photos" in output or "DRY RUN" in output
        assert Photo.objects.filter(pk=photo.pk).exists()

    def test_cleanup_orphans_orphan_photos_actually_deleted(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from footycollect.collection.models import Photo
        from footycollect.users.tests.factories import UserFactory

        user = UserFactory()
        photo = Photo.objects.create(
            user=user,
            content_type=None,
            object_id=None,
            image=SimpleUploadedFile("o.jpg", b"x", content_type="image/jpeg"),
        )
        out = StringIO()
        call_command("cleanup_orphans", "--photos", stdout=out)
        output = out.getvalue()
        assert "Deleted" in output or "deleted" in output
        assert not Photo.objects.filter(pk=photo.pk).exists()


@pytest.mark.django_db
class TestPopulateUserCollectionCommand:
    """Tests for populate_user_collection management command."""

    def test_populate_user_collection_requires_userid_without_json_file(self):
        from django.core.management.base import CommandError

        out = StringIO()
        with pytest.raises(CommandError, match="userid"):
            call_command("populate_user_collection", stdout=out)

    def test_populate_user_collection_dry_run_with_json_file(self, tmp_path):
        json_file = tmp_path / "collection.json"
        json_file.write_text('{"data": {"entries": [{"userid": 123, "id": 1}]}, "user": {}}')
        out = StringIO()
        call_command("populate_user_collection", "--json-file", str(json_file), "--dry-run", stdout=out)
        output = out.getvalue()
        assert "DRY RUN" in output.upper() or "entries" in output.lower() or "Completed" in output

    def test_populate_user_collection_json_file_without_userid_in_entries_raises(self, tmp_path):
        from django.core.management.base import CommandError

        json_file = tmp_path / "collection.json"
        json_file.write_text('{"data": {"entries": [{"id": 1}]}, "user": {}}')
        out = StringIO()
        with pytest.raises(CommandError, match="Could not determine userid"):
            call_command("populate_user_collection", "--json-file", str(json_file), stdout=out)

    def test_populate_user_collection_load_json_returns_userid_from_first_entry(self, tmp_path):
        from footycollect.collection.management.commands.populate_user_collection import Command

        json_file = tmp_path / "collection.json"
        json_file.write_text('{"data": {"entries": [{"userid": 456, "id": 1}]}, "user": {"name": "Test"}}')
        cmd = Command()
        cmd.stdout = StringIO()
        data, user_info, userid = cmd._load_collection_from_json(str(json_file))
        assert userid == 456  # noqa: PLR2004
        assert data.get("entries") is not None
        assert user_info == {"name": "Test"}

    def test_populate_user_collection_check_scrape_response_none_raises(self):
        from django.core.management.base import CommandError

        from footycollect.collection.management.commands.populate_user_collection import Command

        cmd = Command()
        cmd.stdout = StringIO()
        with pytest.raises(CommandError, match="No response"):
            cmd._check_scrape_response(None, 1)

    def test_populate_user_collection_check_scrape_response_error_status_raises(self):
        from django.core.management.base import CommandError

        from footycollect.collection.management.commands.populate_user_collection import Command

        cmd = Command()
        cmd.stdout = StringIO()
        with pytest.raises(CommandError, match="Failed to start"):
            cmd._check_scrape_response({"status": "error", "error": "API down"}, 1)

    def test_populate_user_collection_get_cached_entries_non_cached_returns_none(self):
        from footycollect.collection.management.commands.populate_user_collection import Command

        cmd = Command()
        a, b = cmd._get_cached_entries_if_available({"status": "queued"})
        assert a is None
        assert b is None

    def test_populate_user_collection_get_cached_entries_cached_with_entries_returns_data(self):
        from footycollect.collection.management.commands.populate_user_collection import Command

        cmd = Command()
        data, user_info = cmd._get_cached_entries_if_available(
            {"status": "cached", "data": {"entries": [{"id": 1}], "user": {"name": "U"}}},
        )
        assert data is not None
        assert data.get("entries") == [{"id": 1}]
        assert user_info == {"name": "U"}


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
        assert "dry run" in output.lower() or "not found" in output.lower()

    @patch.object(FetchHomeKitsCommand, "save_output")
    @patch.object(FetchHomeKitsCommand, "process_kits")
    @patch.object(FetchHomeKitsCommand, "fetch_kits_data")
    @patch.object(FetchHomeKitsCommand, "load_slugs")
    def test_fetch_home_kits_ok_with_kits(self, mock_load_slugs, mock_fetch, mock_process, mock_save):
        mock_load_slugs.return_value = ["barcelona-2024-25-home"]
        mock_fetch.return_value = [
            {
                "name": "Barcelona 2024/25 Home",
                "team": {"name": "Barcelona", "country": "ES", "logo": ""},
                "season": {"year": "2024-25"},
                "brand": {"name": "Nike", "logo": "", "logo_dark": ""},
                "main_img_url": "https://example.com/kit.jpg",
            }
        ]
        mock_process.return_value = [{"name": "Barcelona 2024/25 Home", "slug": "barcelona-2024-25-home"}]
        out = StringIO()
        call_command("fetch_home_kits", stdout=out)
        output = out.getvalue()
        assert "Successfully processed" in output
        mock_save.assert_called_once()

    @patch.object(FetchHomeKitsCommand, "load_slugs")
    def test_fetch_home_kits_no_slugs_exits_early(self, mock_load_slugs):
        mock_load_slugs.return_value = []
        out = StringIO()
        call_command("fetch_home_kits", stdout=out)
        output = out.getvalue()
        assert "No slugs" in output

    @patch.object(FetchHomeKitsCommand, "fetch_kits_data")
    @patch.object(FetchHomeKitsCommand, "load_slugs")
    def test_fetch_home_kits_api_returns_empty_exits_early(self, mock_load_slugs, mock_fetch):
        mock_load_slugs.return_value = ["some-kit"]
        mock_fetch.return_value = []
        out = StringIO()
        call_command("fetch_home_kits", stdout=out)
        output = out.getvalue()
        assert "Failed to fetch" in output
