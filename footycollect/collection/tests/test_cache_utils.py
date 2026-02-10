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

    def test_get_item_list_cache_index_key(self):
        key = cache_utils.get_item_list_cache_index_key(99)
        assert key == "item_list_keys:99"

    def test_track_item_list_cache_key_stores_in_set(self):
        cache_utils.track_item_list_cache_key(5, "item_list:v2:5:page:1")
        keys = cache.get("item_list_keys:5")
        assert keys is not None
        assert "item_list:v2:5:page:1" in keys

    def test_track_item_list_cache_key_does_not_duplicate(self):
        cache_utils.track_item_list_cache_key(7, "key-dup")
        cache_utils.track_item_list_cache_key(7, "key-dup")
        keys = cache.get("item_list_keys:7")
        assert keys.count("key-dup") == 1

    def test_invalidate_item_list_cache_for_user_with_no_keys(self):
        cache_utils.invalidate_item_list_cache_for_user(999)
        assert cache.get("item_list_keys:999") is None

    def test_invalidate_item_list_cache_for_user_bumps_version(self):
        cache_utils.track_item_list_cache_key(8, "k8")
        cache_utils.invalidate_item_list_cache_for_user(8)
        version = cache.get("item_list_fragment_version:8")
        assert version is not None

    def test_invalidate_item_list_cache_for_user_none_skips(self):
        cache_utils.invalidate_item_list_cache_for_user(None)
        cache_utils.invalidate_item_list_cache_for_user(0)

    def test_reset_item_list_cache_metrics(self):
        cache_utils.increment_item_list_cache_metric(is_hit=True)
        cache_utils.reset_item_list_cache_metrics()
        m = cache_utils.get_item_list_cache_metrics()
        assert m["hits"] == 0
        assert m["misses"] == 0

    def test_increment_item_list_cache_metric_value_error_sets_one(self):
        cache.delete(cache_utils.ITEM_LIST_CACHE_METRICS_HITS_KEY)
        cache_utils.increment_item_list_cache_metric(is_hit=True)
        assert cache.get(cache_utils.ITEM_LIST_CACHE_METRICS_HITS_KEY) == 1
