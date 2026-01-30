"""
Download club/brand logos to our storage when creating items so we do not depend
on third-party servers to load them. Logos are stored as AVIF.
"""

import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from footycollect.core.utils.images import optimize_image

logger = logging.getLogger(__name__)

PROXY_REFERER = "https://www.footballkitarchive.com/"
NOT_FOUND_LOGO_URL = "https://www.footballkitarchive.com/static/logos/not_found.png"
LOGO_PATH_PREFIX = "logos"
MAX_LOGO_SIZE = 2 * 1024 * 1024
LOGO_MAX_DIMENSION = (512, 512)
BACKFILL_USE_PROXY_ENV = "BACKFILL_LOGS_USE_ROTATING_PROXY"


def _is_not_found_url(url: str) -> bool:
    return bool(url and url.rstrip("/") == NOT_FOUND_LOGO_URL.rstrip("/"))


def _get_rotating_proxy_config() -> dict | None:
    proxy_url = getattr(settings, "ROTATING_PROXY_URL", "")
    if not proxy_url:
        return None
    username = getattr(settings, "ROTATING_PROXY_USERNAME", "")
    password = getattr(settings, "ROTATING_PROXY_PASSWORD", "")
    if username and password:
        parsed = urlparse(proxy_url)
        proxy_url = f"{parsed.scheme}://{username}:{password}@{parsed.netloc}"
    return {"http": proxy_url, "https": proxy_url}


def _is_fka_logo_url(url: str) -> bool:
    if not url or not url.startswith("http"):
        return False
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        allowed = getattr(
            settings,
            "ALLOWED_EXTERNAL_IMAGE_HOSTS",
            ["cdn.footballkitarchive.com", "www.footballkitarchive.com"],
        )
        return hostname in [h.lower() for h in allowed]
    except (ValueError, AttributeError):
        return False


def _ext_from_url_or_content_type(url: str, content_type: str | None) -> str:
    ext = Path(urlparse(url).path).suffix.lower()
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"):
        return ext.lstrip(".")
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if "png" in ct:
            return "png"
        if "jpeg" in ct or "jpg" in ct:
            return "jpg"
        if "webp" in ct:
            return "webp"
        if "gif" in ct:
            return "gif"
    return "png"


def _download_logo_bytes(url: str) -> tuple[bytes, str]:
    kwargs: dict = {
        "stream": True,
        "headers": {"Referer": PROXY_REFERER},
    }
    if os.environ.get(BACKFILL_USE_PROXY_ENV):
        proxies = _get_rotating_proxy_config()
        if proxies:
            kwargs["proxies"] = proxies
    resp = requests.get(url, timeout=15, **kwargs)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "")
    size = 0
    chunks = []
    for chunk in resp.iter_content(chunk_size=65536):
        if chunk:
            size += len(chunk)
            if size > MAX_LOGO_SIZE:
                msg = "Logo too large"
                raise ValueError(msg)
            chunks.append(chunk)
    return b"".join(chunks), content_type


def _storage_path(model_label: str, pk: int, field_suffix: str, ext: str) -> str:
    return f"{LOGO_PATH_PREFIX}/{model_label}/{pk}_{field_suffix}.{ext}"


def download_logo_to_storage(url: str, model_label: str, pk: int, field_suffix: str) -> str:
    data, content_type = _download_logo_bytes(url)
    ext = _ext_from_url_or_content_type(url, content_type)
    if ext == "svg":
        path = _storage_path(model_label, pk, field_suffix, "svg")
        default_storage.save(path, ContentFile(data))
        return default_storage.url(path)
    file_in = ContentFile(data)
    file_in.name = f"logo.{ext}"
    optimized = optimize_image(file_in, max_size=LOGO_MAX_DIMENSION)
    if optimized:
        path = _storage_path(model_label, pk, field_suffix, "avif")
        default_storage.save(path, optimized)
        return default_storage.url(path)
    path = _storage_path(model_label, pk, field_suffix, ext)
    default_storage.save(path, ContentFile(data))
    return default_storage.url(path)


def _download_logo_as_avif_file(url: str):
    data, content_type = _download_logo_bytes(url)
    ext = _ext_from_url_or_content_type(url, content_type)
    if ext == "svg":
        return None
    file_in = ContentFile(data)
    file_in.name = f"logo.{ext}"
    return optimize_image(file_in, max_size=LOGO_MAX_DIMENSION)


def entity_has_not_found_logos(instance) -> bool:
    if instance is None:
        return False
    return _is_not_found_url(getattr(instance, "logo", None)) or _is_not_found_url(
        getattr(instance, "logo_dark", None)
    )


def clean_entity_not_found_logos(instance) -> bool:
    """
    Clear logo/logo_dark when they are the not_found placeholder URL and delete
    the corresponding file from storage (bucket). Returns True if any change was made.
    """
    if instance is None or not instance.pk:
        return False
    updated = []
    for field_name, file_attr in (("logo", "logo_file"), ("logo_dark", "logo_dark_file")):
        url = getattr(instance, field_name, None)
        if not _is_not_found_url(url):
            continue
        setattr(instance, field_name, "")
        updated.append(field_name)
        if hasattr(instance, file_attr):
            f = getattr(instance, file_attr, None)
            if f:
                f.delete(save=False)
                updated.append(file_attr)
    if updated:
        instance.save(update_fields=updated)
        logger.info("Cleaned not_found logos for %s %s: %s", instance._meta.model_name, instance.pk, updated)
        return True
    return False


def ensure_entity_logos_downloaded(instance) -> None:  # noqa: C901, PLR0912
    """Download entity logos from external URLs to local storage."""
    if instance is None:
        return
    model_label = instance._meta.model_name + "s"
    pk = instance.pk
    if not pk:
        return
    updated = []
    for field_name, suffix, file_attr in (
        ("logo", "logo", "logo_file"),
        ("logo_dark", "logo_dark", "logo_dark_file"),
    ):
        url = getattr(instance, field_name, None)
        # Handle not_found placeholder URL for logo_dark
        if _is_not_found_url(url):
            if field_name == "logo_dark":
                setattr(instance, field_name, "")
                updated.append(field_name)
                if hasattr(instance, file_attr):
                    f = getattr(instance, file_attr, None)
                    if f:
                        f.delete(save=False)
                        updated.append(file_attr)
            continue
        if not url or not _is_fka_logo_url(url):
            continue
        if hasattr(instance, file_attr) and getattr(instance, file_attr, None):
            continue
        # Download and save logo
        try:
            if hasattr(instance, file_attr):
                avif_file = _download_logo_as_avif_file(url)
                if avif_file:
                    getattr(instance, file_attr).save(f"{pk}_{suffix}.avif", avif_file, save=False)
                    updated.append(file_attr)
            else:
                new_url = download_logo_to_storage(url, model_label, pk, suffix)
                setattr(instance, field_name, new_url)
                updated.append(field_name)
        except (OSError, ValueError, requests.RequestException):
            logger.warning(
                "Failed to download %s for %s %s: %s",
                field_name,
                model_label,
                pk,
                url[:80],
                exc_info=True,
            )
    if updated:
        instance.save(update_fields=updated)
        logger.info("Downloaded %s for %s %s", updated, model_label, pk)


def ensure_item_entity_logos_downloaded(item) -> None:
    if item is None:
        return
    if getattr(item, "club_id", None):
        ensure_entity_logos_downloaded(item.club)
    if getattr(item, "brand_id", None):
        ensure_entity_logos_downloaded(item.brand)
