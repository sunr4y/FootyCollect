from django.core.management.base import BaseCommand
from django_celery_beat.models import IntervalSchedule, PeriodicTask

DEFAULTS = [
    {
        "name": "cleanup_orphaned_photos (incomplete, 24h)",
        "task": "collection.tasks.cleanup_orphaned_photos",
        "every": 6,
        "period": IntervalSchedule.HOURS,
    },
    {
        "name": "cleanup_all_orphaned_photos",
        "task": "collection.tasks.cleanup_all_orphaned_photos",
        "every": 7,
        "period": IntervalSchedule.DAYS,
    },
    {
        "name": "cleanup_old_incomplete_photos (168h)",
        "task": "collection.tasks.cleanup_old_incomplete_photos",
        "every": 1,
        "period": IntervalSchedule.DAYS,
    },
]


class Command(BaseCommand):
    help = "Create or update django_celery_beat periodic tasks with sensible default frequencies."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print what would be created/updated.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write("DRY RUN: no changes will be saved")

        for spec in DEFAULTS:
            interval, _ = IntervalSchedule.objects.get_or_create(
                every=spec["every"],
                period=spec["period"],
            )
            pt, created = PeriodicTask.objects.update_or_create(
                task=spec["task"],
                defaults={
                    "name": spec["name"],
                    "interval": interval,
                    "enabled": True,
                },
            )
            if dry_run:
                self.stdout.write(
                    f"Would {'create' if created else 'update'}: {spec['name']} " f"({spec['every']} {spec['period']})"
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{'Created' if created else 'Updated'}: {spec['name']} "
                        f"every {spec['every']} {spec['period']}"
                    )
                )

        if not dry_run:
            from django_celery_beat.models import PeriodicTasks

            PeriodicTasks.update_changed()
            self.stdout.write(self.style.SUCCESS("Beat schedule updated. Celery Beat will pick up changes."))
            self.stdout.write("Adjust intervals in Django Admin: django_celery_beat > Periodic tasks.")
