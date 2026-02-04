import logging

from django.shortcuts import render

logger = logging.getLogger(__name__)


def _load_home_kits():
    """Load and process home kits data from JSON file."""
    import json

    from django.conf import settings

    data_path = settings.APPS_DIR / "static" / "data" / "home_kits_data.json"

    try:
        with data_path.open() as f:
            data = json.load(f)
        kits = data.get("kits", [])
    except FileNotFoundError:
        logger.warning("Home kits data file not found: %s", data_path)
        return []
    except json.JSONDecodeError:
        logger.exception("Invalid JSON in home kits data file")
        return []

    media_url = getattr(settings, "MEDIA_URL", "/media/")
    use_cdn = media_url.startswith("http")

    for kit in kits:
        for path_key, fallback_key, url_key in [
            ("image_path", "original_image_url", "image_url"),
            ("team_logo_path", "original_team_logo", "team_logo"),
            ("brand_logo_path", "original_brand_logo", "brand_logo"),
            ("brand_logo_dark_path", "original_brand_logo_dark", "brand_logo_dark"),
        ]:
            if use_cdn and kit.get(path_key):
                kit[url_key] = f"{media_url.rstrip('/')}/{kit[path_key]}"
            else:
                kit[url_key] = kit.get(fallback_key, "")

    return kits


def _distribute_kits_to_columns(kits, num_columns, kits_per_column):
    """Distribute kits across columns, avoiding same club in same column."""
    import random

    if not kits:
        return [[] for _ in range(num_columns)]

    random.seed(42)
    available = kits.copy()
    random.shuffle(available)  # NOSONAR (S2245) "safe random shuffle"

    columns = [[] for _ in range(num_columns)]
    columns_teams = [set() for _ in range(num_columns)]

    for col_idx in range(num_columns):
        for kit in available[:]:
            if len(columns[col_idx]) >= kits_per_column:
                break
            team = kit.get("team_name", "") or kit.get("name", "").split()[0]
            if team not in columns_teams[col_idx]:
                columns[col_idx].append(kit)
                columns_teams[col_idx].add(team)
                available.remove(kit)

    return [col * 3 for col in columns]


def home(request):
    """Home view with curated jersey cards from external API."""
    kits = _load_home_kits()
    columns_items = _distribute_kits_to_columns(kits, num_columns=8, kits_per_column=5)
    return render(request, "pages/home.html", {"columns_items": columns_items, "use_cached_kits": True})


__all__ = [
    "home",
]
