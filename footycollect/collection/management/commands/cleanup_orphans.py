"""Management command to clean up orphaned data."""

import logging
from collections.abc import Callable

from django.core.management.base import BaseCommand
from django.db.models import Count, QuerySet

from footycollect.collection.models import BaseItem, Photo
from footycollect.core.models import Brand, Club, Competition, Kit, Season

logger = logging.getLogger(__name__)


def _run_cleanup(
    stdout,
    style,
    queryset: QuerySet,
    label: str,
    *,
    dry_run: bool,
    item_label_fn: Callable,
) -> int:
    count = queryset.count()
    if count == 0:
        return 0
    stdout.write(f"\n{label}: {count}")
    if dry_run:
        for obj in queryset[:10]:
            stdout.write(f"  - {item_label_fn(obj)}")
        if count > 10:
            stdout.write(f"  ... and {count - 10} more")
        return 0
    queryset.delete()
    stdout.write(style.SUCCESS(f"  Deleted {count} {label.lower()}"))
    return count


def _cleanup_orphan_brands(command, *, dry_run: bool) -> int:
    qs = Brand.objects.annotate(item_count=Count("baseitem")).filter(item_count=0)
    return _run_cleanup(
        command.stdout,
        command.style,
        qs,
        "Orphaned Brands",
        dry_run=dry_run,
        item_label_fn=lambda b: f"{b.name} (pk={b.pk})",
    )


def _cleanup_orphan_clubs(command, *, dry_run: bool) -> int:
    qs = Club.objects.annotate(baseitem_count=Count("baseitem"), kit_count=Count("kit")).filter(
        baseitem_count=0, kit_count=0
    )
    return _run_cleanup(
        command.stdout, command.style, qs, "Orphaned Clubs", dry_run, lambda c: f"{c.name} (pk={c.pk})"
    )


def _cleanup_orphan_kits(command, *, dry_run: bool) -> int:
    qs = Kit.objects.annotate(jersey_count=Count("jersey")).filter(jersey_count=0)
    return _run_cleanup(
        command.stdout,
        command.style,
        qs,
        "Orphaned Kits",
        dry_run=dry_run,
        item_label_fn=lambda k: f"{k.name} (pk={k.pk})",
    )


def _cleanup_orphan_seasons(command, *, dry_run: bool) -> int:
    qs = Season.objects.annotate(baseitem_count=Count("baseitem"), kit_count=Count("kit")).filter(
        baseitem_count=0, kit_count=0
    )
    return _run_cleanup(
        command.stdout,
        command.style,
        qs,
        "Orphaned Seasons",
        dry_run=dry_run,
        item_label_fn=lambda s: f"{s.year} (pk={s.pk})",
    )


def _cleanup_orphan_competitions(command, *, dry_run: bool) -> int:
    qs = Competition.objects.annotate(
        baseitem_count=Count("collection_baseitem_items"), kit_count=Count("kit")
    ).filter(baseitem_count=0, kit_count=0)
    return _run_cleanup(
        command.stdout,
        command.style,
        qs,
        "Orphaned Competitions",
        dry_run=dry_run,
        item_label_fn=lambda c: f"{c.name} (pk={c.pk})",
    )


def _cleanup_orphan_baseitems(command, *, dry_run: bool) -> int:
    orphan_pks = [bi.pk for bi in BaseItem.objects.all() if bi.get_specific_item() is None]
    if not orphan_pks:
        return 0
    count = len(orphan_pks)
    command.stdout.write(f"\nOrphaned BaseItems (no specific item): {count}")
    if dry_run:
        for pk in orphan_pks[:10]:
            bi = BaseItem.objects.get(pk=pk)
            command.stdout.write(f"  - {bi.name} type={bi.item_type} (pk={pk})")
        if count > 10:
            command.stdout.write(f"  ... and {count - 10} more")
        return 0
    BaseItem.objects.filter(pk__in=orphan_pks).delete()
    command.stdout.write(command.style.SUCCESS(f"  Deleted {count} orphaned base items"))
    return count


def _cleanup_orphan_photos(command, *, dry_run: bool) -> int:
    qs = Photo.objects.filter(object_id__isnull=True) | Photo.objects.filter(content_type__isnull=True)
    count = qs.count()
    if count == 0:
        return 0
    command.stdout.write(f"\nOrphaned Photos: {count}")
    if dry_run:
        return 0
    qs.delete()
    command.stdout.write(command.style.SUCCESS(f"  Deleted {count} orphaned photos"))
    return count


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
        runners = [
            (options["brands"] or cleanup_all, _cleanup_orphan_brands),
            (options["clubs"] or cleanup_all, _cleanup_orphan_clubs),
            (options["kits"] or cleanup_all, _cleanup_orphan_kits),
            (options["seasons"] or cleanup_all, _cleanup_orphan_seasons),
            (options["competitions"] or cleanup_all, _cleanup_orphan_competitions),
            (options["baseitems"] or cleanup_all, _cleanup_orphan_baseitems),
            (options["photos"] or cleanup_all, _cleanup_orphan_photos),
        ]
        if not any(active for active, _ in runners):
            self.stdout.write(
                "No cleanup option specified. Use --all or specify what to clean:\n"
                "  --brands, --clubs, --kits, --seasons, --competitions, --baseitems, --photos\n"
            )
            return
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No data will be deleted\n"))
        total_deleted = sum(fn(self, dry_run=dry_run) for active, fn in runners if active)
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN complete - no data was deleted"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Total deleted: {total_deleted} records"))
