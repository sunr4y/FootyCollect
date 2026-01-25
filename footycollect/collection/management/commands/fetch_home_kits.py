"""
Django management command to fetch and cache kits for the home page.

This command reads kit slugs from a JSON file, fetches kit data from the FKAPI
bulk endpoint, downloads and compresses images to AVIF format, and saves
the kit data to a JSON file for use by the home page view.

Supports both local storage and cloud storage (S3/R2) via Django's default_storage.
"""

import json
import logging
from datetime import UTC, datetime
from io import BytesIO
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from footycollect.api.client import FKAPIClient
from footycollect.core.utils.images import optimize_image

logger = logging.getLogger(__name__)

# Storage path prefixes
HOME_KITS_STORAGE_PATH = "home_kits"
LOGOS_STORAGE_PATH = "home_kits/logos"


class Command(BaseCommand):
    help = "Fetch and cache kits for the home page from FKAPI bulk endpoint"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_dir = settings.APPS_DIR / "static" / "data"
        self.slugs_file = self.data_dir / "home_kits_slugs.json"
        self.output_file = self.data_dir / "home_kits_data.json"
        self.proxies = self._get_proxy_config()
        self.storage_backend = getattr(settings, "STORAGE_BACKEND", "local")

    def _get_proxy_config(self) -> dict | None:
        """Get proxy configuration from settings."""
        proxy_url = getattr(settings, "ROTATING_PROXY_URL", "")
        if not proxy_url:
            return None

        username = getattr(settings, "ROTATING_PROXY_USERNAME", "")
        password = getattr(settings, "ROTATING_PROXY_PASSWORD", "")

        if username and password:
            parsed = urlparse(proxy_url)
            proxy_url = f"{parsed.scheme}://{username}:{password}@{parsed.netloc}"

        return {
            "http": proxy_url,
            "https": proxy_url,
        }

    def _get_storage_path(self, filename: str) -> str:
        """Get the storage path for a home kit image."""
        return f"{HOME_KITS_STORAGE_PATH}/{filename}"

    def _get_logo_storage_path(self, logo_type: str, filename: str) -> str:
        """Get the storage path for a logo (team or brand)."""
        return f"{LOGOS_STORAGE_PATH}/{logo_type}/{filename}"

    def _get_image_url(self, storage_path: str) -> str:
        """Get the full URL for an image in storage."""
        try:
            return default_storage.url(storage_path)
        except (ValueError, AttributeError):
            return f"{settings.MEDIA_URL}{storage_path}"

    def _image_exists(self, storage_path: str) -> bool:
        """Check if an image exists in storage."""
        try:
            return default_storage.exists(storage_path)
        except (OSError, AttributeError):
            return False

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be fetched without actually downloading files",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip images that already exist in storage",
        )
        parser.add_argument(
            "--quality",
            type=int,
            default=80,
            help="AVIF compression quality (1-100, default: 80)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        verbose = options["verbose"]
        skip_existing = options["skip_existing"]
        quality = options["quality"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No files will be modified"))

        self.stdout.write(f"Storage backend: {self.storage_backend}")
        self.stdout.write(f"Storage class: {default_storage.__class__.__name__}")

        if self.proxies:
            self.stdout.write(self.style.SUCCESS("Rotating proxy configured"))
        else:
            self.stdout.write("No proxy configured (using direct connection)")

        self.ensure_directories()

        slugs = self.load_slugs()
        if not slugs:
            self.stdout.write(self.style.ERROR("No slugs found in input file"))
            return

        self.stdout.write(f"Found {len(slugs)} kit slugs to fetch")

        kits_data = self.fetch_kits_data(slugs, verbose=verbose)
        if not kits_data:
            self.stdout.write(self.style.ERROR("Failed to fetch kits data from API"))
            return

        self.stdout.write(f"Fetched {len(kits_data)} kits from API")

        processed_kits = self.process_kits(
            kits_data,
            dry_run=dry_run,
            verbose=verbose,
            skip_existing=skip_existing,
            quality=quality,
        )

        if not dry_run:
            self.save_output(processed_kits)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully processed {len(processed_kits)} kits"),
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Would process {len(processed_kits)} kits"),
            )

    def ensure_directories(self):
        """Ensure required directories exist (for local JSON file only)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_slugs(self) -> list[str]:
        """Load kit slugs from the input JSON file."""
        try:
            with self.slugs_file.open() as f:
                data = json.load(f)
            return data.get("slugs", [])
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f"Slugs file not found: {self.slugs_file}"),
            )
            return []
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f"Invalid JSON in slugs file: {e}"),
            )
            return []

    def fetch_kits_data(self, slugs: list[str], *, verbose: bool) -> list[dict]:
        """Fetch kits data from FKAPI bulk endpoint in batches."""
        client = FKAPIClient()
        all_kits = []

        batch_size = 30
        for i in range(0, len(slugs), batch_size):
            batch = slugs[i : i + batch_size]
            if verbose:
                self.stdout.write(f"Fetching batch {i // batch_size + 1}: {len(batch)} kits")
                self.stdout.write(f"  Slugs: {batch[:3]}...")

            kits = client.get_kits_bulk(batch)

            if verbose:
                self.stdout.write(f"  Received {len(kits)} kits from API")
                if kits:
                    self.stdout.write(f"  First kit: {kits[0].get('name', 'N/A')}")

            all_kits.extend(kits)

        if verbose:
            self.stdout.write(f"Total kits fetched: {len(all_kits)}")

        return all_kits

    def _process_logo(
        self,
        url: str,
        logo_type: str,
        logo_cache: dict,
        *,
        dry_run: bool,
        verbose: bool,
        skip_existing: bool,
    ) -> str | None:
        """Process a single logo: download if needed, return storage path."""
        if dry_run or not url:
            return None
        if url in logo_cache:
            return logo_cache[url]
        downloaded_path = self.download_logo(url, logo_type, verbose=verbose, skip_existing=skip_existing)
        if downloaded_path:
            logo_cache[url] = downloaded_path
        return downloaded_path

    def _process_kit_image(
        self,
        kit: dict,
        storage_path: str,
        quality: int,
        *,
        dry_run: bool,
        verbose: bool,
        skip_existing: bool,
    ) -> str | None:
        """Process kit main image: download and compress if needed."""
        if skip_existing and self._image_exists(storage_path):
            if verbose:
                self.stdout.write(f"  Skipping existing image: {storage_path}")
            return storage_path

        if dry_run:
            return None

        source_url = kit.get("main_img_url")
        if source_url and self.download_and_save_image(source_url, storage_path, quality, verbose=verbose):
            return storage_path

        self.stdout.write(self.style.WARNING(f"  Failed to download image for: {kit.get('name', 'Unknown')}"))
        return None

    def process_kits(
        self,
        kits_data: list[dict],
        *,
        dry_run: bool,
        verbose: bool,
        skip_existing: bool,
        quality: int,
    ) -> list[dict]:
        """Process kits: download and compress images, prepare output data."""
        processed = []
        logo_cache: dict[str, str] = {}

        for i, kit in enumerate(kits_data):
            name = kit.get("name", "Unknown")
            if verbose:
                self.stdout.write(f"Processing {i + 1}/{len(kits_data)}: {name}")

            slug = self.generate_slug(kit)
            storage_path = self._get_storage_path(f"{slug}.avif")

            team = kit.get("team", {})
            season = kit.get("season", {})
            brand = kit.get("brand", {})

            logo_kwargs = {"dry_run": dry_run, "verbose": verbose, "skip_existing": skip_existing}

            processed.append(
                {
                    "name": name,
                    "slug": slug,
                    "team_name": team.get("name", ""),
                    "team_country": team.get("country", ""),
                    "season_year": season.get("year", ""),
                    "brand_name": brand.get("name", ""),
                    "image_path": self._process_kit_image(
                        kit, storage_path, quality, dry_run=dry_run, verbose=verbose, skip_existing=skip_existing
                    ),
                    "team_logo_path": self._process_logo(team.get("logo", ""), "teams", logo_cache, **logo_kwargs),
                    "brand_logo_path": self._process_logo(brand.get("logo", ""), "brands", logo_cache, **logo_kwargs),
                    "brand_logo_dark_path": self._process_logo(
                        brand.get("logo_dark", ""), "brands", logo_cache, **logo_kwargs
                    ),
                    "original_image_url": kit.get("main_img_url", ""),
                    "original_team_logo": team.get("logo", ""),
                    "original_brand_logo": brand.get("logo", ""),
                    "original_brand_logo_dark": brand.get("logo_dark", ""),
                }
            )

        if verbose and logo_cache:
            self.stdout.write(f"Downloaded {len(logo_cache)} unique logos")

        return processed

    def generate_slug(self, kit: dict) -> str:
        """Generate a slug from kit data."""
        name = kit.get("name", "unknown")
        slug = name.lower()
        slug = slug.replace(" ", "-")
        for char in ["'", '"', ",", ".", "(", ")", "/"]:
            slug = slug.replace(char, "")
        return "-".join(part for part in slug.split("-") if part)

    def download_and_save_image(
        self,
        url: str,
        storage_path: str,
        quality: int,
        *,
        verbose: bool,
    ) -> str | None:
        """Download an image, compress it to AVIF, and save to storage.

        Returns the storage path (relative) of the saved image, or None if failed.
        """
        try:
            if verbose:
                self.stdout.write(f"  Downloading: {url}")
                if self.proxies:
                    self.stdout.write("  Using rotating proxy")

            response = requests.get(url, timeout=30, proxies=self.proxies)
            response.raise_for_status()

            image_data = BytesIO(response.content)
            image_data.name = urlparse(url).path.split("/")[-1] or "image.jpg"

            from django.core.files import File

            image_file = File(image_data, name=image_data.name)

            optimized = optimize_image(
                image_file,
                max_size=(800, 1200),
                quality=quality,
                img_format="AVIF",
            )

            if optimized:
                content = ContentFile(optimized.read())
                saved_path = default_storage.save(storage_path, content)

                if verbose:
                    self.stdout.write(f"  Saved to storage: {saved_path}")

                return saved_path  # Return relative path, not URL
            self.stdout.write(
                self.style.WARNING(f"  Failed to optimize image from: {url}"),
            )
            return None  # noqa: TRY300

        except requests.RequestException as e:
            logger.warning("Failed to download image %s: %s", url, e)
            return None
        except Exception:
            logger.exception("Error processing image %s", url)
            return None

    def _sanitize_url(self, url: str) -> str:
        """Fix malformed URLs like https:/ to https://"""
        if url and url.startswith("https:/") and not url.startswith("https://"):
            return url.replace("https:/", "https://", 1)
        if url and url.startswith("http:/") and not url.startswith("http://"):
            return url.replace("http:/", "http://", 1)
        return url

    def download_logo(
        self,
        url: str,
        logo_type: str,
        *,
        verbose: bool,
        skip_existing: bool,
    ) -> str | None:
        """Download a logo (team or brand) and save to storage as PNG.

        Returns the storage path (relative) of the saved logo, or None if failed.
        """
        if not url or not url.startswith("http"):
            return None

        # Fix malformed URLs
        url = self._sanitize_url(url)

        # Extract filename from URL
        parsed = urlparse(url)
        path_parts = parsed.path.split("/")
        original_filename = path_parts[-1].split("?")[0] if path_parts else "logo.png"

        # Create a unique filename based on URL path
        safe_filename = original_filename.replace(" ", "_").replace("%20", "_")
        storage_path = self._get_logo_storage_path(logo_type, safe_filename)

        # Check if exists
        if skip_existing and self._image_exists(storage_path):
            if verbose:
                self.stdout.write(f"    Logo exists: {safe_filename}")
            return storage_path  # Return relative path, not URL

        try:
            if verbose:
                self.stdout.write(f"    Downloading logo: {safe_filename}")

            response = requests.get(url, timeout=15, proxies=self.proxies)
            response.raise_for_status()

            content = ContentFile(response.content)
        except requests.RequestException as e:
            logger.warning("Failed to download logo %s: %s", url, e)
            return None
        except Exception:
            logger.exception("Error downloading logo %s", url)
            return None
        else:
            return default_storage.save(storage_path, content)

    def save_output(self, kits: list[dict]):
        """Save processed kit data to output JSON file."""
        output_data = {
            "kits": kits,
            "generated_at": datetime.now(UTC).isoformat(),
            "total_count": len(kits),
            "storage_backend": self.storage_backend,
        }

        with self.output_file.open("w") as f:
            json.dump(output_data, f, indent=2)

        self.stdout.write(f"Saved kit data to: {self.output_file}")
