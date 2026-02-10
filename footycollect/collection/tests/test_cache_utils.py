"""Tests for cache_utils."""

from django.core.cache import cache
from django.test import TestCase

from footycollect.collection import cache_utils


class TestCacheUtils(TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        cache_utils.reset_item_list_cache_metrics()

    def tearDown(self):
        cache.clear()

    def test_get_item_list_fragment_version_key(self):
        key = cache_utils.get_item_list_fragment_version_key(1)
        assert key == "item_list_fragment_version:1"

    def test_get_item_list_cache_key(self):
        key = cache_utils.get_item_list_cache_key(2, 3)
        assert key == "item_list:v2:2:page:3"

    def test_track_and_invalidate(self):
        cache_utils.track_item_list_cache_key(10, "k1")
        cache.set("k1", "v")
        cache_utils.invalidate_item_list_cache_for_user(10)
        assert cache.get("k1") is None

    def test_metrics(self):
        cache_utils.increment_item_list_cache_metric(is_hit=True)
        cache_utils.increment_item_list_cache_metric(is_hit=False)
        m = cache_utils.get_item_list_cache_metrics()
        assert m["hits"] == 1
        assert m["misses"] == 1
