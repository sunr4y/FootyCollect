"""
Verify static files collection configuration and dry-run collectstatic.

Useful for CI and production deployment to ensure:
- STORAGES staticfiles backend is configured
- collectstatic runs without errors (dry-run, no upload)
- Collectfasta strategy is set when using S3 (production)
"""

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Verify static files configuration and run collectstatic --dry-run"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-dry-run",
            action="store_true",
            help="Only check STORAGES config; do not run collectstatic --dry-run",
        )

    def handle(self, *args, **options):
        errors = []
        skip_dry_run = options["skip_dry_run"]

        storages = getattr(settings, "STORAGES", {})
        staticfiles_backend = storages.get("staticfiles", {}).get("BACKEND", "")

        if not staticfiles_backend:
            errors.append("STORAGES['staticfiles'] is not configured")
        else:
            self.stdout.write(f"Staticfiles backend: {staticfiles_backend}")

        if "s3" in staticfiles_backend.lower() or "S3Storage" in staticfiles_backend:
            strategy = getattr(settings, "COLLECTFASTA_STRATEGY", None)
            if strategy:
                self.stdout.write(f"Collectfasta strategy: {strategy}")
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "S3 staticfiles backend without COLLECTFASTA_STRATEGY; "
                        "collectstatic may be slow. Consider enabling collectfasta."
                    )
                )

        static_url = getattr(settings, "STATIC_URL", None)
        if static_url:
            self.stdout.write(f"STATIC_URL: {static_url}")
        else:
            errors.append("STATIC_URL is not set")

        if errors:
            for msg in errors:
                self.stderr.write(self.style.ERROR(msg))
            raise SystemExit(1)

        if not skip_dry_run:
            self.stdout.write("Running collectstatic --dry-run --noinput...")
            try:
                call_command(
                    "collectstatic",
                    "--dry-run",
                    "--noinput",
                    verbosity=options["verbosity"],
                )
                self.stdout.write(self.style.SUCCESS("Static files verification passed."))
            except CommandError as e:
                self.stderr.write(self.style.ERROR(f"collectstatic --dry-run failed: {e}"))
                raise SystemExit(1) from e
