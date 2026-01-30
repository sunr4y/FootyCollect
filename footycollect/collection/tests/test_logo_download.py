"""
Tests for logo_download service (not the backfill_logos command).
"""

from unittest.mock import MagicMock, patch

from django.core.files.base import ContentFile
from django.test import TestCase

from footycollect.collection.services.logo_download import (
    NOT_FOUND_LOGO_URL,
    _is_fka_logo_url,
    _is_not_found_url,
    clean_entity_not_found_logos,
    ensure_entity_logos_downloaded,
    ensure_item_entity_logos_downloaded,
    entity_has_not_found_logos,
)
from footycollect.core.models import Brand, Club


class TestIsNotFoundUrl(TestCase):
    def test_accepts_exact_not_found_url(self):
        assert _is_not_found_url(NOT_FOUND_LOGO_URL) is True

    def test_accepts_not_found_url_with_trailing_slash(self):
        assert _is_not_found_url(NOT_FOUND_LOGO_URL + "/") is True

    def test_rejects_empty_string(self):
        assert _is_not_found_url("") is False

    def test_rejects_none(self):
        assert _is_not_found_url(None) is False

    def test_rejects_other_url(self):
        assert _is_not_found_url("https://www.footballkitarchive.com/static/logos/teams/6.png") is False
        assert _is_not_found_url("https://example.com/not_found.png") is False


class TestEntityHasNotFoundLogos(TestCase):
    def test_none_returns_false(self):
        assert entity_has_not_found_logos(None) is False

    def test_club_without_not_found_returns_false(self):
        club = Club.objects.create(name="Test", slug="test-club-notfound-1")
        try:
            assert entity_has_not_found_logos(club) is False
        finally:
            club.delete()

    def test_club_with_logo_dark_not_found_returns_true(self):
        club = Club.objects.create(
            name="Test",
            slug="test-club-notfound-2",
            logo_dark=NOT_FOUND_LOGO_URL,
        )
        try:
            assert entity_has_not_found_logos(club) is True
        finally:
            club.delete()

    def test_club_with_logo_not_found_returns_true(self):
        club = Club.objects.create(
            name="Test",
            slug="test-club-notfound-3",
            logo=NOT_FOUND_LOGO_URL,
        )
        try:
            assert entity_has_not_found_logos(club) is True
        finally:
            club.delete()


class TestCleanEntityNotFoundLogos(TestCase):
    def test_none_returns_false(self):
        assert clean_entity_not_found_logos(None) is False

    def test_club_with_logo_dark_not_found_clears_and_returns_true(self):
        club = Club.objects.create(
            name="Test",
            slug="test-club-clean-1",
            logo_dark=NOT_FOUND_LOGO_URL,
        )
        try:
            result = clean_entity_not_found_logos(club)
            assert result is True
            club.refresh_from_db()
            assert club.logo_dark == ""
        finally:
            club.delete()

    def test_club_with_logo_not_found_clears_and_returns_true(self):
        club = Club.objects.create(
            name="Test",
            slug="test-club-clean-2",
            logo=NOT_FOUND_LOGO_URL,
        )
        try:
            result = clean_entity_not_found_logos(club)
            assert result is True
            club.refresh_from_db()
            assert club.logo == ""
        finally:
            club.delete()

    def test_club_with_logo_dark_file_not_found_deletes_file(self):
        club = Club.objects.create(
            name="Test",
            slug="test-club-clean-3",
            logo_dark=NOT_FOUND_LOGO_URL,
        )
        try:
            mock_file = MagicMock()
            club.logo_dark_file = mock_file
            with patch.object(club, "save") as mock_save:
                result = clean_entity_not_found_logos(club)
            assert result is True
            mock_file.delete.assert_called_once_with(save=False)
            assert club.logo_dark == ""
            mock_save.assert_called_once()
        finally:
            club.delete()

    def test_club_without_not_found_returns_false(self):
        club = Club.objects.create(
            name="Test",
            slug="test-club-clean-4",
            logo="https://www.footballkitarchive.com/static/logos/teams/1.png",
        )
        try:
            result = clean_entity_not_found_logos(club)
            assert result is False
        finally:
            club.delete()


class TestEnsureEntityLogosDownloaded(TestCase):
    def test_none_does_nothing(self):
        ensure_entity_logos_downloaded(None)

    def test_skips_when_logo_file_already_exists(self):
        club = Club.objects.create(
            name="Test",
            slug="test-club-skip-1",
            logo="https://www.footballkitarchive.com/static/logos/teams/1.png",
        )
        try:
            content = ContentFile(b"x")
            content.name = "1_logo.avif"
            club.logo_file.save("1_logo.avif", content, save=False)
            club.save(update_fields=["logo_file"])
            with patch("footycollect.collection.services.logo_download._download_logo_as_avif_file") as mock_download:
                ensure_entity_logos_downloaded(club)
                mock_download.assert_not_called()
        finally:
            club.delete()

    def test_clears_logo_dark_when_not_found(self):
        club = Club.objects.create(
            name="Test",
            slug="test-club-ensure-1",
            logo_dark=NOT_FOUND_LOGO_URL,
        )
        try:
            ensure_entity_logos_downloaded(club)
            club.refresh_from_db()
            assert club.logo_dark == ""
        finally:
            club.delete()

    def test_skips_download_when_url_not_fka(self):
        club = Club.objects.create(
            name="Test",
            slug="test-club-ensure-2",
            logo="https://example.com/logo.png",
        )
        try:
            with (
                patch("footycollect.collection.services.logo_download._download_logo_as_avif_file") as mock_download,
                patch(
                    "footycollect.collection.services.logo_download._is_fka_logo_url",
                    return_value=False,
                ),
            ):
                ensure_entity_logos_downloaded(club)
                mock_download.assert_not_called()
        finally:
            club.delete()

    def test_downloads_when_fka_url_and_no_file_yet(self):
        club = Club.objects.create(
            name="Test",
            slug="test-club-ensure-3",
            logo="https://www.footballkitarchive.com/static/logos/teams/1.png",
        )
        try:
            mock_avif = MagicMock()
            mock_logo_file = MagicMock()
            mock_logo_file.__bool__ = lambda self: False
            mock_logo_file.__len__ = lambda self: 0
            with (
                patch(
                    "footycollect.collection.services.logo_download._download_logo_as_avif_file",
                    return_value=mock_avif,
                ),
                patch.object(club, "logo_file", mock_logo_file),
                patch.object(club, "save"),
            ):
                ensure_entity_logos_downloaded(club)
            mock_logo_file.save.assert_called_once()
            assert mock_logo_file.save.call_args[0][0] == "1_logo.avif"
            assert mock_logo_file.save.call_args[0][1] is mock_avif
        finally:
            club.delete()


class TestIsFkaLogoUrl(TestCase):
    def test_accepts_fka_hosts(self):
        assert _is_fka_logo_url("https://www.footballkitarchive.com/static/x.png") is True
        assert _is_fka_logo_url("https://cdn.footballkitarchive.com/static/x.png") is True

    def test_rejects_empty_and_non_http(self):
        assert _is_fka_logo_url("") is False
        assert _is_fka_logo_url(None) is False
        assert _is_fka_logo_url("ftp://example.com/x.png") is False

    def test_rejects_other_hosts(self):
        with patch("footycollect.collection.services.logo_download.settings") as mock_settings:
            mock_settings.ALLOWED_EXTERNAL_IMAGE_HOSTS = [
                "cdn.footballkitarchive.com",
                "www.footballkitarchive.com",
            ]
            assert _is_fka_logo_url("https://example.com/logo.png") is False


class TestEnsureItemEntityLogosDownloaded(TestCase):
    # Number of expected calls when item has both club and brand
    EXPECTED_ENSURE_CALLS_FOR_CLUB_AND_BRAND = 2

    def test_none_does_nothing(self):
        ensure_item_entity_logos_downloaded(None)

    def test_calls_ensure_for_club_and_brand(self):
        brand = Brand.objects.create(name="Nike", slug="nike-test-item")
        club = Club.objects.create(name="Barça", slug="barca-test-item")
        item = MagicMock()
        item.club_id = club.pk
        item.brand_id = brand.pk
        item.club = club
        item.brand = brand
        with patch("footycollect.collection.services.logo_download.ensure_entity_logos_downloaded") as mock_ensure:
            ensure_item_entity_logos_downloaded(item)
            assert mock_ensure.call_count == self.EXPECTED_ENSURE_CALLS_FOR_CLUB_AND_BRAND
            mock_ensure.assert_any_call(club)
            mock_ensure.assert_any_call(brand)
        brand.delete()
        club.delete()
