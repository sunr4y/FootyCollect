"""Tests for templatetags list_filters and image_tags."""

from unittest.mock import MagicMock

from django.test import TestCase

from footycollect.collection.templatetags import image_tags, list_filters


class TestListFilters(TestCase):
    def test_color_display_returns_display_name(self):
        assert list_filters.color_display("red") == "Red"

    def test_contains_in_list(self):
        assert list_filters.contains("a", ["a", "b"])

    def test_contains_not_in_list(self):
        assert not list_filters.contains("c", ["a", "b"])

    def test_contains_comma_separated_string(self):
        assert list_filters.contains("b", "a, b , c")
        assert not list_filters.contains("x", "a, b")

    def test_contains_empty_value_returns_false(self):
        assert not list_filters.contains("", ["a"])
        assert not list_filters.contains(None, ["a"])

    def test_contains_empty_arg_returns_false(self):
        assert not list_filters.contains("a", "")
        assert not list_filters.contains("a", None)

    def test_parse_json_valid(self):
        assert list_filters.parse_json("[1,2]") == [1, 2]
        assert list_filters.parse_json('{"x":1}') == {"x": 1}

    def test_parse_json_none_returns_empty_list(self):
        assert list_filters.parse_json(None) == []

    def test_parse_json_already_list_returns_same(self):
        assert list_filters.parse_json([1, 2]) == [1, 2]

    def test_parse_json_already_dict_returns_same(self):
        assert list_filters.parse_json({"a": 1}) == {"a": 1}

    def test_parse_json_bool_returns_empty_list(self):
        assert list_filters.parse_json(value=True) == []

    def test_parse_json_invalid_string_returns_empty_list(self):
        assert list_filters.parse_json("not json") == []


class TestImageTags(TestCase):
    def test_responsive_image_no_avif(self):
        photo = MagicMock()
        photo.image.url = "/media/photo.jpg"
        photo.image_avif = None
        photo.caption = "Cap"
        result = image_tags.responsive_image(photo, "my-class")
        assert 'src="/media/photo.jpg"' in result
        assert 'class="my-class"' in result
        assert 'alt="Cap"' in result
        assert "<picture>" not in result

    def test_responsive_image_with_avif(self):
        photo = MagicMock()
        photo.image.url = "/media/photo.jpg"
        photo.caption = ""
        avif = MagicMock()
        avif.storage.exists.return_value = True
        avif.url = "/media/photo.avif"
        photo.image_avif = avif
        result = image_tags.responsive_image(photo)
        assert "<picture>" in result
        assert 'srcset="/media/photo.avif"' in result
        assert 'type="image/avif"' in result

    def test_responsive_image_with_missing_avif(self):
        photo = MagicMock()
        photo.image.url = "/media/photo.jpg"
        photo.caption = ""
        avif = MagicMock()
        avif.storage.exists.return_value = False
        avif.url = "/media/photo.avif"
        photo.image_avif = avif
        result = image_tags.responsive_image(photo)
        assert 'srcset="/media/photo.avif"' not in result
        assert 'type="image/avif"' not in result
        assert 'src="/media/photo.jpg"' in result

    def test_responsive_image_no_image_uses_empty_url(self):
        photo = MagicMock()
        photo.image = None
        photo.image_avif = None
        photo.caption = None
        result = image_tags.responsive_image(photo)
        assert 'src=""' in result
        assert 'alt=""' in result
