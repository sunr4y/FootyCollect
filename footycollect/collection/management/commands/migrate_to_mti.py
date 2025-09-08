"""
Management command to migrate from abstract BaseItem to Multi-Table Inheritance (MTI).

This command migrates existing data from the current abstract inheritance
structure to the new MTI structure.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from footycollect.collection.models import (
    Jersey as OldJersey,
)
from footycollect.collection.models import (
    OtherItem as OldOtherItem,
)
from footycollect.collection.models import (
    Outerwear as OldOuterwear,
)
from footycollect.collection.models import (
    Pants as OldPants,
)
from footycollect.collection.models import (
    Shorts as OldShorts,
)
from footycollect.collection.models import (
    Tracksuit as OldTracksuit,
)
from footycollect.collection.models_mti import (
    BaseItem as NewBaseItem,
)
from footycollect.collection.models_mti import (
    Jersey as NewJersey,
)
from footycollect.collection.models_mti import (
    OtherItem as NewOtherItem,
)
from footycollect.collection.models_mti import (
    Outerwear as NewOuterwear,
)
from footycollect.collection.models_mti import (
    Pants as NewPants,
)
from footycollect.collection.models_mti import (
    Shorts as NewShorts,
)
from footycollect.collection.models_mti import (
    Tracksuit as NewTracksuit,
)


class Command(BaseCommand):
    help = "Migrate from abstract BaseItem to Multi-Table Inheritance (MTI)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be migrated without actually doing it",
        )
        parser.add_argument(
            "--item-type",
            type=str,
            choices=["jersey", "shorts", "outerwear", "tracksuit", "pants", "other"],
            help="Migrate only specific item type",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        item_type = options.get("item_type")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No data will be migrated"),
            )

        try:
            with transaction.atomic():
                if item_type:
                    self.migrate_item_type(item_type, dry_run)
                else:
                    self.migrate_all_items(dry_run)

                if dry_run:
                    # Rollback the transaction in dry run mode
                    dry_run_msg = "Dry run - rolling back transaction"
                    raise RuntimeError(dry_run_msg)  # noqa: TRY301

        except RuntimeError as e:
            if dry_run and "Dry run" in str(e):
                self.stdout.write(
                    self.style.SUCCESS("Dry run completed successfully"),
                )
            else:
                error_msg = f"Migration failed: {e}"
                raise CommandError(error_msg) from e

        self.stdout.write(
            self.style.SUCCESS("Migration completed successfully!"),
        )

    def migrate_all_items(self, *, dry_run=False):
        """Migrate all item types."""
        self.stdout.write("Starting migration of all item types...")

        self.migrate_item_type("jersey", dry_run)
        self.migrate_item_type("shorts", dry_run)
        self.migrate_item_type("outerwear", dry_run)
        self.migrate_item_type("tracksuit", dry_run)
        self.migrate_item_type("pants", dry_run)
        self.migrate_item_type("other", dry_run)

    def migrate_item_type(self, item_type, *, dry_run=False):
        """Migrate a specific item type."""
        self.stdout.write(f"Migrating {item_type} items...")

        if item_type == "jersey":
            self.migrate_jerseys(dry_run)
        elif item_type == "shorts":
            self.migrate_shorts(dry_run)
        elif item_type == "outerwear":
            self.migrate_outerwear(dry_run)
        elif item_type == "tracksuit":
            self.migrate_tracksuits(dry_run)
        elif item_type == "pants":
            self.migrate_pants(dry_run)
        elif item_type == "other":
            self.migrate_other_items(dry_run)

    def migrate_jerseys(self, *, dry_run=False):
        """Migrate Jersey items."""
        old_jerseys = OldJersey.objects.all()
        count = 0

        for old_jersey in old_jerseys:
            if dry_run:
                self.stdout.write(f"Would migrate Jersey: {old_jersey}")
                count += 1
                continue

            # Create BaseItem
            base_item = NewBaseItem.objects.create(
                item_type="jersey",
                name=self.get_item_name(old_jersey),
                user=old_jersey.user,
                brand=old_jersey.brand,
                club=old_jersey.club,
                season=old_jersey.season,
                condition=old_jersey.condition,
                detailed_condition=old_jersey.detailed_condition,
                description=old_jersey.description,
                is_replica=old_jersey.is_replica,
                is_private=old_jersey.is_private,
                is_draft=old_jersey.is_draft,
                design=old_jersey.design,
                main_color=old_jersey.main_color,
                country=old_jersey.country,
                created_at=old_jersey.created_at,
                updated_at=old_jersey.updated_at,
            )

            # Copy competitions
            base_item.competitions.set(old_jersey.competitions.all())

            # Copy secondary colors
            base_item.secondary_colors.set(old_jersey.secondary_colors.all())

            # Copy tags
            base_item.tags.set(old_jersey.tags.all())

            # Create Jersey
            NewJersey.objects.create(
                base_item=base_item,
                kit=old_jersey.kit,
                size=old_jersey.size,
                is_fan_version=old_jersey.is_fan_version,
                is_signed=old_jersey.is_signed,
                has_nameset=old_jersey.has_nameset,
                player_name=old_jersey.player_name,
                number=old_jersey.number,
                is_short_sleeve=old_jersey.is_short_sleeve,
            )

            count += 1

        self.stdout.write(f"Migrated {count} jerseys")

    def migrate_shorts(self, *, dry_run=False):
        """Migrate Shorts items."""
        old_shorts = OldShorts.objects.all()
        count = 0

        for old_short in old_shorts:
            if dry_run:
                self.stdout.write(f"Would migrate Shorts: {old_short}")
                count += 1
                continue

            # Create BaseItem
            base_item = NewBaseItem.objects.create(
                item_type="shorts",
                name=self.get_item_name(old_short),
                user=old_short.user,
                brand=old_short.brand,
                club=old_short.club,
                season=old_short.season,
                condition=old_short.condition,
                detailed_condition=old_short.detailed_condition,
                description=old_short.description,
                is_replica=old_short.is_replica,
                is_private=old_short.is_private,
                is_draft=old_short.is_draft,
                design=old_short.design,
                main_color=old_short.main_color,
                country=old_short.country,
                created_at=old_short.created_at,
                updated_at=old_short.updated_at,
            )

            # Copy relationships
            base_item.competitions.set(old_short.competitions.all())
            base_item.secondary_colors.set(old_short.secondary_colors.all())
            base_item.tags.set(old_short.tags.all())

            # Create Shorts
            NewShorts.objects.create(
                base_item=base_item,
                size=old_short.size,
                number=old_short.number,
                is_fan_version=old_short.is_fan_version,
            )

            count += 1

        self.stdout.write(f"Migrated {count} shorts")

    def migrate_outerwear(self, *, dry_run=False):
        """Migrate Outerwear items."""
        old_outerwear = OldOuterwear.objects.all()
        count = 0

        for old_item in old_outerwear:
            if dry_run:
                self.stdout.write(f"Would migrate Outerwear: {old_item}")
                count += 1
                continue

            # Create BaseItem
            base_item = NewBaseItem.objects.create(
                item_type="outerwear",
                name=self.get_item_name(old_item),
                user=old_item.user,
                brand=old_item.brand,
                club=old_item.club,
                season=old_item.season,
                condition=old_item.condition,
                detailed_condition=old_item.detailed_condition,
                description=old_item.description,
                is_replica=old_item.is_replica,
                is_private=old_item.is_private,
                is_draft=old_item.is_draft,
                design=old_item.design,
                main_color=old_item.main_color,
                country=old_item.country,
                created_at=old_item.created_at,
                updated_at=old_item.updated_at,
            )

            # Copy relationships
            base_item.competitions.set(old_item.competitions.all())
            base_item.secondary_colors.set(old_item.secondary_colors.all())
            base_item.tags.set(old_item.tags.all())

            # Create Outerwear
            NewOuterwear.objects.create(
                base_item=base_item,
                type=old_item.type,
                size=old_item.size,
            )

            count += 1

        self.stdout.write(f"Migrated {count} outerwear items")

    def migrate_tracksuits(self, *, dry_run=False):
        """Migrate Tracksuit items."""
        old_tracksuits = OldTracksuit.objects.all()
        count = 0

        for old_item in old_tracksuits:
            if dry_run:
                self.stdout.write(f"Would migrate Tracksuit: {old_item}")
                count += 1
                continue

            # Create BaseItem
            base_item = NewBaseItem.objects.create(
                item_type="tracksuit",
                name=self.get_item_name(old_item),
                user=old_item.user,
                brand=old_item.brand,
                club=old_item.club,
                season=old_item.season,
                condition=old_item.condition,
                detailed_condition=old_item.detailed_condition,
                description=old_item.description,
                is_replica=old_item.is_replica,
                is_private=old_item.is_private,
                is_draft=old_item.is_draft,
                design=old_item.design,
                main_color=old_item.main_color,
                country=old_item.country,
                created_at=old_item.created_at,
                updated_at=old_item.updated_at,
            )

            # Copy relationships
            base_item.competitions.set(old_item.competitions.all())
            base_item.secondary_colors.set(old_item.secondary_colors.all())
            base_item.tags.set(old_item.tags.all())

            # Create Tracksuit
            NewTracksuit.objects.create(
                base_item=base_item,
                size=old_item.size,
            )

            count += 1

        self.stdout.write(f"Migrated {count} tracksuits")

    def migrate_pants(self, *, dry_run=False):
        """Migrate Pants items."""
        old_pants = OldPants.objects.all()
        count = 0

        for old_item in old_pants:
            if dry_run:
                self.stdout.write(f"Would migrate Pants: {old_item}")
                count += 1
                continue

            # Create BaseItem
            base_item = NewBaseItem.objects.create(
                item_type="pants",
                name=self.get_item_name(old_item),
                user=old_item.user,
                brand=old_item.brand,
                club=old_item.club,
                season=old_item.season,
                condition=old_item.condition,
                detailed_condition=old_item.detailed_condition,
                description=old_item.description,
                is_replica=old_item.is_replica,
                is_private=old_item.is_private,
                is_draft=old_item.is_draft,
                design=old_item.design,
                main_color=old_item.main_color,
                country=old_item.country,
                created_at=old_item.created_at,
                updated_at=old_item.updated_at,
            )

            # Copy relationships
            base_item.competitions.set(old_item.competitions.all())
            base_item.secondary_colors.set(old_item.secondary_colors.all())
            base_item.tags.set(old_item.tags.all())

            # Create Pants
            NewPants.objects.create(
                base_item=base_item,
                size=old_item.size,
            )

            count += 1

        self.stdout.write(f"Migrated {count} pants")

    def migrate_other_items(self, *, dry_run=False):
        """Migrate OtherItem items."""
        old_items = OldOtherItem.objects.all()
        count = 0

        for old_item in old_items:
            if dry_run:
                self.stdout.write(f"Would migrate OtherItem: {old_item}")
                count += 1
                continue

            # Create BaseItem
            base_item = NewBaseItem.objects.create(
                item_type="other",
                name=self.get_item_name(old_item),
                user=old_item.user,
                brand=old_item.brand,
                club=old_item.club,
                season=old_item.season,
                condition=old_item.condition,
                detailed_condition=old_item.detailed_condition,
                description=old_item.description,
                is_replica=old_item.is_replica,
                is_private=old_item.is_private,
                is_draft=old_item.is_draft,
                design=old_item.design,
                main_color=old_item.main_color,
                country=old_item.country,
                created_at=old_item.created_at,
                updated_at=old_item.updated_at,
            )

            # Copy relationships
            base_item.competitions.set(old_item.competitions.all())
            base_item.secondary_colors.set(old_item.secondary_colors.all())
            base_item.tags.set(old_item.tags.all())

            # Create OtherItem
            NewOtherItem.objects.create(
                base_item=base_item,
                type=old_item.type,
            )

            count += 1

        self.stdout.write(f"Migrated {count} other items")

    def get_item_name(self, old_item):
        """Generate a name for the item if it doesn't have one."""
        if hasattr(old_item, "name") and old_item.name:
            return old_item.name

        # Generate name from available fields
        parts = []
        if old_item.brand:
            parts.append(old_item.brand.name)
        if old_item.club:
            parts.append(old_item.club.name)

        item_type = old_item.__class__.__name__.lower()
        parts.append(item_type.title())

        return " ".join(parts) if parts else f"Unnamed {item_type}"
