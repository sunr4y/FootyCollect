"""
Django management command to migrate photos from local storage to remote storage (R2/AWS S3).

This command reads photos from local filesystem and uploads them to the configured
remote storage backend (Cloudflare R2 or AWS S3).
"""

from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage, get_storage_class
from django.core.management.base import BaseCommand

from footycollect.collection.models import Photo


class Command(BaseCommand):
    help = "Migrate photos from local storage to remote storage (R2/AWS S3)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be migrated without actually uploading files",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip photos that already exist in remote storage",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        verbose = options["verbose"]
        skip_existing = options["skip_existing"]

        if dry_run:
            self.stdout.write("Starting photo migration to remote storage (dry run)...")
        else:
            self.stdout.write("Starting photo migration to remote storage...")

        current_storage = default_storage
        storage_backend = getattr(settings, "STORAGE_BACKEND", "local")

        if storage_backend == "local":
            self.stdout.write(
                self.style.ERROR(
                    "Error: STORAGE_BACKEND is set to 'local'. "
                    "Please set STORAGE_BACKEND to 'r2' or 'aws' before running migration.",
                ),
            )
            return

        self.stdout.write(f"Storage backend: {storage_backend}")
        self.stdout.write(f"Remote storage: {current_storage.__class__.__name__}")

        local_storage = get_storage_class("django.core.files.storage.FileSystemStorage")()
        local_media_root = Path(settings.MEDIA_ROOT)

        if not local_media_root.exists():
            self.stdout.write(
                self.style.WARNING(f"Local media root does not exist: {local_media_root}"),
            )
            return

        photos = Photo.objects.all()
        total_photos = photos.count()
        self.stdout.write(f"Found {total_photos} photos to migrate")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No files will be uploaded"))

        migrated_count = 0
        skipped_count = 0
        error_count = 0
        total_size = 0

        for photo in photos:
            try:
                result = self._migrate_photo(
                    photo,
                    local_storage,
                    current_storage,
                    local_media_root,
                    dry_run,
                    verbose,
                    skip_existing,
                )
                if result["status"] == "migrated":
                    migrated_count += 1
                    total_size += result.get("size", 0)
                elif result["status"] == "skipped":
                    skipped_count += 1
                elif result["status"] == "error":
                    error_count += 1
            except OSError as e:
                error_count += 1
                if verbose:
                    self.stdout.write(
                        self.style.ERROR(f"Error migrating photo {photo.id}: {e}"),
                    )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Migration completed!"))
        self.stdout.write(f"  Migrated: {migrated_count}")
        self.stdout.write(f"  Skipped: {skipped_count}")
        self.stdout.write(f"  Errors: {error_count}")
        if total_size > 0:
            self.stdout.write(f"  Total size: {self._format_size(total_size)}")

    def _migrate_photo(self, photo, local_storage, remote_storage, local_media_root, dry_run, verbose, skip_existing):
        """Migrate a single photo from local to remote storage."""
        result = {"status": "skipped", "size": 0}

        if not photo.image:
            return result

        image_name = photo.image.name
        avif_name = photo.image_avif.name if photo.image_avif else None

        if skip_existing:
            if remote_storage.exists(image_name):
                if verbose:
                    self.stdout.write(f"Skipping {image_name} (already exists in remote)")
                return result

        local_image_path = local_media_root / image_name
        if not local_image_path.exists():
            if verbose:
                self.stdout.write(
                    self.style.WARNING(f"Local file not found: {local_image_path}"),
                )
            return {"status": "error"}

        if dry_run:
            file_size = local_image_path.stat().st_size
            self.stdout.write(f"Would migrate: {image_name} ({self._format_size(file_size)})")
            if avif_name:
                local_avif_path = local_media_root / avif_name
                if local_avif_path.exists():
                    avif_size = local_avif_path.stat().st_size
                    self.stdout.write(f"Would migrate: {avif_name} ({self._format_size(avif_size)})")
            return {"status": "migrated", "size": file_size}

        try:
            with local_image_path.open("rb") as f:
                remote_storage.save(image_name, File(f))
                file_size = local_image_path.stat().st_size

            if verbose:
                self.stdout.write(f"Migrated: {image_name} ({self._format_size(file_size)})")

            if avif_name:
                local_avif_path = local_media_root / avif_name
                if local_avif_path.exists():
                    with local_avif_path.open("rb") as f:
                        remote_storage.save(avif_name, File(f))
                    if verbose:
                        avif_size = local_avif_path.stat().st_size
                        self.stdout.write(f"Migrated: {avif_name} ({self._format_size(avif_size)})")

        except OSError as e:
            if verbose:
                self.stdout.write(
                    self.style.ERROR(f"Error migrating {image_name}: {e}"),
                )
            return {"status": "error"}
        else:
            return {"status": "migrated", "size": file_size}

    def _format_size(self, size_bytes):
        """Format file size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
