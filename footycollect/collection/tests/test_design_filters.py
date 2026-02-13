"""Tests for collection.templatetags.design_filters."""

from django.test import SimpleTestCase

from footycollect.collection.templatetags.design_filters import to_hyphens


class TestToHyphens(SimpleTestCase):
    def test_replaces_underscores_with_hyphens(self):
        assert to_hyphens("home_kit") == "home-kit"

    def test_returns_value_unchanged_without_underscores(self):
        assert to_hyphens("home") == "home"
