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

        storage_backend = getattr(settings, "STORAGE_BACKEND", "local")
        if not self._ensure_remote_storage(storage_backend):
            return

        current_storage = default_storage
        self.stdout.write(f"Storage backend: {storage_backend}")
        self.stdout.write(f"Remote storage: {current_storage.__class__.__name__}")

        local_media_root = Path(settings.MEDIA_ROOT)
        if not self._ensure_local_media_root(local_media_root):
            return

        local_storage = get_storage_class("django.core.files.storage.FileSystemStorage")()
        photos = Photo.objects.all()
        total_photos = photos.count()
        self.stdout.write(f"Found {total_photos} photos to migrate")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No files will be uploaded"))

        migrated_count, skipped_count, error_count, total_size = self._run_migration_loop(
            photos, local_storage, current_storage, local_media_root, dry_run, verbose, skip_existing
        )

        self._write_summary(migrated_count, skipped_count, error_count, total_size)

    def _ensure_remote_storage(self, storage_backend):
        """Return False if backend is local (caller should return)."""
        if storage_backend == "local":
            self.stdout.write(
                self.style.ERROR(
                    "Error: STORAGE_BACKEND is set to 'local'. "
                    "Please set STORAGE_BACKEND to 'r2' or 'aws' before running migration.",
                ),
            )
            return False
        return True

    def _ensure_local_media_root(self, local_media_root):
        """Return False if media root does not exist (caller should return)."""
        if not local_media_root.exists():
            self.stdout.write(
                self.style.WARNING(f"Local media root does not exist: {local_media_root}"),
            )
            return False
        return True

    def _run_migration_loop(
        self, photos, local_storage, current_storage, local_media_root, dry_run, verbose, skip_existing
    ):
        migrated_count = skipped_count = error_count = total_size = 0
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
                else:
                    error_count += 1
            except OSError as e:
                error_count += 1
                if verbose:
                    self.stdout.write(self.style.ERROR(f"Error migrating photo {photo.id}: {e}"))
        return migrated_count, skipped_count, error_count, total_size

    def _write_summary(self, migrated_count, skipped_count, error_count, total_size):
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

        if skip_existing and remote_storage.exists(image_name):
            if verbose:
                self.stdout.write(f"Skipping {image_name} (already exists in remote)")
            return result

        local_image_path = local_media_root / image_name
        if not local_image_path.exists():
            if verbose:
                self.stdout.write(self.style.WARNING(f"Local file not found: {local_image_path}"))
            return {"status": "error"}

        if dry_run:
            return self._migrate_photo_dry_run(image_name, avif_name, local_image_path, local_media_root)

        return self._migrate_photo_upload(
            image_name, avif_name, local_image_path, local_media_root, remote_storage, verbose
        )

    def _migrate_photo_dry_run(self, image_name, avif_name, local_image_path, local_media_root):
        """Handle dry-run output for one photo."""
        file_size = local_image_path.stat().st_size
        self.stdout.write(f"Would migrate: {image_name} ({self._format_size(file_size)})")
        if avif_name:
            local_avif_path = local_media_root / avif_name
            if local_avif_path.exists():
                avif_size = local_avif_path.stat().st_size
                self.stdout.write(f"Would migrate: {avif_name} ({self._format_size(avif_size)})")
        return {"status": "migrated", "size": file_size}

    def _migrate_photo_upload(
        self, image_name, avif_name, local_image_path, local_media_root, remote_storage, verbose
    ):
        """Upload one photo (and avif if present) to remote storage."""
        try:
            with local_image_path.open("rb") as f:
                remote_storage.save(image_name, File(f))
            file_size = local_image_path.stat().st_size
            if verbose:
                self.stdout.write(f"Migrated: {image_name} ({self._format_size(file_size)})")

            if avif_name:
                self._upload_avif_if_exists(avif_name, local_media_root, remote_storage, verbose)
        except OSError as e:
            if verbose:
                self.stdout.write(self.style.ERROR(f"Error migrating {image_name}: {e}"))
            return {"status": "error"}
        else:
            return {"status": "migrated", "size": file_size}

    def _upload_avif_if_exists(self, avif_name, local_media_root, remote_storage, verbose):
        """Upload avif file to remote if it exists locally."""
        local_avif_path = local_media_root / avif_name
        if not local_avif_path.exists():
            return
        with local_avif_path.open("rb") as f:
            remote_storage.save(avif_name, File(f))
        if verbose:
            avif_size = local_avif_path.stat().st_size
            self.stdout.write(f"Migrated: {avif_name} ({self._format_size(avif_size)})")

    def _format_size(self, size_bytes):
        """Format file size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
