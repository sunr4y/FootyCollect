"""
Django management command to clean up orphaned photo files.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Clean up orphaned photo files that are no longer referenced in the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting files",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output",
        )
        parser.add_argument(
            "--incomplete-only",
            action="store_true",
            help="Only clean up photos from incomplete form submissions",
        )
        parser.add_argument(
            "--older-than-hours",
            type=int,
            default=24,
            help="Only clean up photos older than specified hours (default: 24)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        verbose = options["verbose"]
        incomplete_only = options["incomplete_only"]
        older_than_hours = options["older_than_hours"]

        self.stdout.write("Starting orphaned photo cleanup...")

        if incomplete_only:
            self.stdout.write(f"Cleaning up photos from incomplete submissions older than {older_than_hours} hours...")
            return self._cleanup_incomplete_photos(dry_run, verbose, older_than_hours)

        return self._cleanup_all_orphaned_photos(dry_run, verbose)

    def _cleanup_all_orphaned_photos(self, dry_run, verbose):
        """Clean up all orphaned photos."""
        # Get all photo files from database
        db_files = self._get_database_files()
        self.stdout.write(f"Found {len(db_files)} files referenced in database")

        # Get all files in media directories
        orphaned_files = self._find_orphaned_files(db_files)
        self.stdout.write(f"Found {len(orphaned_files)} orphaned files")

        if orphaned_files:
            self._display_orphaned_files(orphaned_files)
            if not dry_run:
                self._delete_orphaned_files(orphaned_files, verbose)
                return
            self.stdout.write(
                self.style.WARNING("Dry run - no files were deleted"),
            )
            return
        self.stdout.write(self.style.SUCCESS("No orphaned files found"))
        return

    def _get_database_files(self):
        """Get all photo files referenced in database."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT image, image_avif
                FROM collection_photo
                WHERE image IS NOT NULL OR image_avif IS NOT NULL
            """,
            )
            db_files = set()
            for row in cursor.fetchall():
                if row[0]:  # image
                    db_files.add(row[0])
                if row[1]:  # image_avif
                    db_files.add(row[1])
        return db_files

    def _find_orphaned_files(self, db_files):
        """Find orphaned files in media directories."""
        media_root = Path(settings.MEDIA_ROOT)
        photo_dirs = [
            media_root / "item_photos",
            media_root / "item_photos_avif",
        ]

        orphaned_files = []
        for photo_dir in photo_dirs:
            if photo_dir.exists():
                for file_path in photo_dir.rglob("*"):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(media_root)
                        # Convert to forward slashes for database comparison
                        relative_path = str(relative_path).replace("\\", "/")
                        if relative_path not in db_files:
                            orphaned_files.append(file_path)
        return orphaned_files

    def _display_orphaned_files(self, orphaned_files):
        """Display list of orphaned files."""
        self.stdout.write("\nOrphaned files:")
        for file_path in orphaned_files:
            try:
                file_size = file_path.stat().st_size
            except OSError:
                file_size = 0
            self.stdout.write(f"  {file_path} ({file_size} bytes)")

    def _delete_orphaned_files(self, orphaned_files, verbose):
        """Delete orphaned files from filesystem."""
        deleted_count = 0
        total_size = 0

        for file_path in orphaned_files:
            if file_path.exists():
                file_size = file_path.stat().st_size
                try:
                    file_path.unlink()
                    deleted_count += 1
                    total_size += file_size
                    if verbose:
                        self.stdout.write(f"Deleted: {file_path}")
                except OSError as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error deleting {file_path}: {e}"),
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} files ({total_size} bytes)",
            ),
        )

    def _cleanup_incomplete_photos(self, dry_run, verbose, older_than_hours):
        """Clean up photos from incomplete form submissions."""

        cutoff_time = self._get_cutoff_time(older_than_hours)
        orphaned_photos = self._get_incomplete_photos(cutoff_time)

        if not orphaned_photos:
            self.stdout.write(self.style.SUCCESS("No incomplete photos found"))
            return None

        self.stdout.write(f"Found {len(orphaned_photos)} incomplete photos")
        return self._process_incomplete_photos(orphaned_photos, dry_run, verbose)

    def _get_cutoff_time(self, older_than_hours):
        """Get cutoff time for incomplete photos."""
        from datetime import timedelta

        from django.utils import timezone

        return timezone.now() - timedelta(hours=older_than_hours)

    def _get_incomplete_photos(self, cutoff_time):
        """Get incomplete photos older than cutoff time (not attached to any item)."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, image, image_avif, uploaded_at, user_id
                FROM collection_photo
                WHERE uploaded_at < %s
                AND content_type_id IS NULL
                """,
                [cutoff_time],
            )
            return cursor.fetchall()

    def _process_incomplete_photos(self, orphaned_photos, dry_run, verbose):
        """Process incomplete photos for deletion."""
        deleted_count = 0
        total_size = 0

        for photo_id, image_path, avif_path, uploaded_at, user_id in orphaned_photos:
            if verbose:
                self.stdout.write(f"Processing photo {photo_id} uploaded at {uploaded_at} by user {user_id}")

            files_to_delete = self._get_files_to_delete(image_path, avif_path)

            if not dry_run:
                deleted_count, total_size = self._delete_incomplete_files(
                    files_to_delete,
                    photo_id,
                    deleted_count,
                    total_size,
                    verbose,
                )
            else:
                total_size = self._count_dry_run_files(files_to_delete, total_size, verbose)

        return self._display_incomplete_results(dry_run, deleted_count, total_size, len(orphaned_photos))

    def _get_files_to_delete(self, image_path, avif_path):
        """Get list of files to delete for a photo."""
        files_to_delete = []
        if image_path:
            full_image_path = Path(settings.MEDIA_ROOT) / image_path
            if full_image_path.exists():
                files_to_delete.append(full_image_path)

        if avif_path:
            full_avif_path = Path(settings.MEDIA_ROOT) / avif_path
            if full_avif_path.exists():
                files_to_delete.append(full_avif_path)
        return files_to_delete

    def _delete_incomplete_files(self, files_to_delete, photo_id, deleted_count, total_size, verbose):
        """Delete files from incomplete photos."""
        for file_path in files_to_delete:
            try:
                file_size = file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
                total_size += file_size
                if verbose:
                    self.stdout.write(f"Deleted: {file_path}")
            except OSError as e:
                self.stdout.write(
                    self.style.ERROR(f"Error deleting {file_path}: {e}"),
                )

        # Delete database record
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM collection_photo WHERE id = %s", [photo_id])
        return deleted_count, total_size

    def _count_dry_run_files(self, files_to_delete, total_size, verbose):
        """Count files in dry run mode."""
        for file_path in files_to_delete:
            if file_path.exists():
                file_size = file_path.stat().st_size
                total_size += file_size
                if verbose:
                    self.stdout.write(f"Would delete: {file_path} ({file_size} bytes)")
        return total_size

    def _display_incomplete_results(self, dry_run, deleted_count, total_size, photo_count):
        """Display results for incomplete photo cleanup."""
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {deleted_count} orphaned photos ({total_size} bytes)",
                ),
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run - would delete {photo_count} orphaned photos ({total_size} bytes)",
                ),
            )
