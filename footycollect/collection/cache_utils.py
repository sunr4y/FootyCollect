from django.core.cache import cache

ITEM_LIST_CACHE_TIMEOUT = 60 * 5  # 5 minutes
ITEM_LIST_CACHE_METRICS_HITS_KEY = "cache_metrics:item_list:hits"
ITEM_LIST_CACHE_METRICS_MISSES_KEY = "cache_metrics:item_list:misses"


def get_item_list_cache_key(user_id, page):
    return f"item_list:{user_id}:page:{page}"


def get_item_list_cache_index_key(user_id):
    return f"item_list_keys:{user_id}"


def track_item_list_cache_key(user_id, cache_key):
    index_key = get_item_list_cache_index_key(user_id)
    keys = cache.get(index_key) or []
    if cache_key not in keys:
        keys.append(cache_key)
        cache.set(index_key, keys, ITEM_LIST_CACHE_TIMEOUT)


def increment_item_list_cache_metric(is_hit):
    key = ITEM_LIST_CACHE_METRICS_HITS_KEY if is_hit else ITEM_LIST_CACHE_METRICS_MISSES_KEY
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, None)


def invalidate_item_list_cache_for_user(user_id):
    if not user_id:
        return

    index_key = get_item_list_cache_index_key(user_id)
    keys = cache.get(index_key) or []

    if keys:
        cache.delete_many(keys)

    cache.delete(index_key)


def get_item_list_cache_metrics():
    hits = cache.get(ITEM_LIST_CACHE_METRICS_HITS_KEY, 0)
    misses = cache.get(ITEM_LIST_CACHE_METRICS_MISSES_KEY, 0)
    return {"hits": hits, "misses": misses}
