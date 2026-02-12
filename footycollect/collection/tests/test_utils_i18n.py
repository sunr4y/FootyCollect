"""Tests for collection.utils_i18n."""

from django.test import SimpleTestCase

from footycollect.collection.utils_i18n import get_color_display_name


class TestGetColorDisplayName(SimpleTestCase):
    def test_returns_empty_string_for_none(self):
        assert get_color_display_name(None) == ""

    def test_returns_empty_string_for_empty_string(self):
        assert get_color_display_name("") == ""

    def test_returns_display_name_for_red(self):
        assert get_color_display_name("red") == "Red"

    def test_returns_display_name_for_blue(self):
        assert get_color_display_name("blue") == "Blue"
