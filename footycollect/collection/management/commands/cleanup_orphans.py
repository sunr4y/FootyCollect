"""Management command to clean up orphaned data."""

import logging

from django.core.management.base import BaseCommand
from django.db.models import Count

from footycollect.collection.models import BaseItem, Photo
from footycollect.core.models import Brand, Club, Competition, Kit, Season

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Remove orphaned entities that are not referenced by any items."""

    help = "Clean up orphaned brands, clubs, kits, seasons, and competitions not used by any items"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--brands",
            action="store_true",
            help="Clean up orphaned brands only",
        )
        parser.add_argument(
            "--clubs",
            action="store_true",
            help="Clean up orphaned clubs only",
        )
        parser.add_argument(
            "--kits",
            action="store_true",
            help="Clean up orphaned kits only",
        )
        parser.add_argument(
            "--seasons",
            action="store_true",
            help="Clean up orphaned seasons only",
        )
        parser.add_argument(
            "--competitions",
            action="store_true",
            help="Clean up orphaned competitions only",
        )
        parser.add_argument(
            "--baseitems",
            action="store_true",
            help="Clean up orphaned base items (no specific item type attached)",
        )
        parser.add_argument(
            "--photos",
            action="store_true",
            help="Clean up orphaned photos (no associated item)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            dest="cleanup_all",
            help="Clean up all orphaned entities",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        cleanup_all = options["cleanup_all"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No data will be deleted\n"))

        # Determine what to clean up
        cleanup_brands = options["brands"] or cleanup_all
        cleanup_clubs = options["clubs"] or cleanup_all
        cleanup_kits = options["kits"] or cleanup_all
        cleanup_seasons = options["seasons"] or cleanup_all
        cleanup_competitions = options["competitions"] or cleanup_all
        cleanup_baseitems = options["baseitems"] or cleanup_all
        cleanup_photos = options["photos"] or cleanup_all

        # If no specific option selected, show usage
        if not any(
            [
                cleanup_brands,
                cleanup_clubs,
                cleanup_kits,
                cleanup_seasons,
                cleanup_competitions,
                cleanup_baseitems,
                cleanup_photos,
            ]
        ):
            self.stdout.write(
                "No cleanup option specified. Use --all or specify what to clean:\n"
                "  --brands, --clubs, --kits, --seasons, --competitions, --baseitems, --photos\n"
            )
            return

        total_deleted = 0

        # Orphaned Brands (not used by any BaseItem)
        if cleanup_brands:
            orphan_brands = Brand.objects.annotate(item_count=Count("baseitem")).filter(item_count=0)

            count = orphan_brands.count()
            if count > 0:
                self.stdout.write(f"\nOrphaned Brands: {count}")
                if dry_run:
                    for brand in orphan_brands[:10]:
                        self.stdout.write(f"  - {brand.name} (pk={brand.pk})")
                    if count > 10:
                        self.stdout.write(f"  ... and {count - 10} more")
                else:
                    orphan_brands.delete()
                    total_deleted += count
                    self.stdout.write(self.style.SUCCESS(f"  Deleted {count} orphaned brands"))

        # Orphaned Clubs (not used by any BaseItem or Kit)
        if cleanup_clubs:
            orphan_clubs = Club.objects.annotate(
                baseitem_count=Count("baseitem"),
                kit_count=Count("kit"),
            ).filter(baseitem_count=0, kit_count=0)

            count = orphan_clubs.count()
            if count > 0:
                self.stdout.write(f"\nOrphaned Clubs: {count}")
                if dry_run:
                    for club in orphan_clubs[:10]:
                        self.stdout.write(f"  - {club.name} (pk={club.pk})")
                    if count > 10:
                        self.stdout.write(f"  ... and {count - 10} more")
                else:
                    orphan_clubs.delete()
                    total_deleted += count
                    self.stdout.write(self.style.SUCCESS(f"  Deleted {count} orphaned clubs"))

        # Orphaned Kits (not used by any Jersey)
        if cleanup_kits:
            orphan_kits = Kit.objects.annotate(jersey_count=Count("jersey")).filter(jersey_count=0)

            count = orphan_kits.count()
            if count > 0:
                self.stdout.write(f"\nOrphaned Kits: {count}")
                if dry_run:
                    for kit in orphan_kits[:10]:
                        self.stdout.write(f"  - {kit.name} (pk={kit.pk})")
                    if count > 10:
                        self.stdout.write(f"  ... and {count - 10} more")
                else:
                    orphan_kits.delete()
                    total_deleted += count
                    self.stdout.write(self.style.SUCCESS(f"  Deleted {count} orphaned kits"))

        # Orphaned Seasons (not used by any BaseItem or Kit)
        if cleanup_seasons:
            orphan_seasons = Season.objects.annotate(
                baseitem_count=Count("baseitem"),
                kit_count=Count("kit"),
            ).filter(baseitem_count=0, kit_count=0)

            count = orphan_seasons.count()
            if count > 0:
                self.stdout.write(f"\nOrphaned Seasons: {count}")
                if dry_run:
                    for season in orphan_seasons[:10]:
                        self.stdout.write(f"  - {season.year} (pk={season.pk})")
                    if count > 10:
                        self.stdout.write(f"  ... and {count - 10} more")
                else:
                    orphan_seasons.delete()
                    total_deleted += count
                    self.stdout.write(self.style.SUCCESS(f"  Deleted {count} orphaned seasons"))

        # Orphaned Competitions (not used by any BaseItem or Kit)
        if cleanup_competitions:
            orphan_competitions = Competition.objects.annotate(
                # ManyToMany relations need different counting
                baseitem_count=Count("collection_baseitem_items"),
                kit_count=Count("kit"),
            ).filter(baseitem_count=0, kit_count=0)

            count = orphan_competitions.count()
            if count > 0:
                self.stdout.write(f"\nOrphaned Competitions: {count}")
                if dry_run:
                    for comp in orphan_competitions[:10]:
                        self.stdout.write(f"  - {comp.name} (pk={comp.pk})")
                    if count > 10:
                        self.stdout.write(f"  ... and {count - 10} more")
                else:
                    orphan_competitions.delete()
                    total_deleted += count
                    self.stdout.write(self.style.SUCCESS(f"  Deleted {count} orphaned competitions"))

        # Orphaned BaseItems (no specific item type attached - MTI orphans)
        if cleanup_baseitems:
            # Find BaseItems that have no related Jersey, Shorts, etc.
            orphan_baseitems = []
            for base_item in BaseItem.objects.all():
                specific = base_item.get_specific_item()
                if specific is None:
                    orphan_baseitems.append(base_item.pk)

            count = len(orphan_baseitems)
            if count > 0:
                self.stdout.write(f"\nOrphaned BaseItems (no specific item): {count}")
                if dry_run:
                    for pk in orphan_baseitems[:10]:
                        bi = BaseItem.objects.get(pk=pk)
                        self.stdout.write(f"  - {bi.name} type={bi.item_type} (pk={pk})")
                    if count > 10:
                        self.stdout.write(f"  ... and {count - 10} more")
                else:
                    BaseItem.objects.filter(pk__in=orphan_baseitems).delete()
                    total_deleted += count
                    self.stdout.write(self.style.SUCCESS(f"  Deleted {count} orphaned base items"))

        # Orphaned Photos (no associated content object)
        if cleanup_photos:
            orphan_photos = Photo.objects.filter(object_id__isnull=True) | Photo.objects.filter(
                content_type__isnull=True
            )

            count = orphan_photos.count()
            if count > 0:
                self.stdout.write(f"\nOrphaned Photos: {count}")
                if not dry_run:
                    orphan_photos.delete()
                    total_deleted += count
                    self.stdout.write(self.style.SUCCESS(f"  Deleted {count} orphaned photos"))

        # Summary
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN complete - no data was deleted"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Total deleted: {total_deleted} records"))
