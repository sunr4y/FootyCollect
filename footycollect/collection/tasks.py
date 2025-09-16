"""
Celery tasks for the collection app.
"""

import logging

from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task
def cleanup_orphaned_photos():
    """
    Clean up orphaned photos from incomplete form submissions.

    This task runs periodically to remove photos that were uploaded
    but never associated with a completed item.
    """
    try:
        logger.info("Starting orphaned photos cleanup task")

        # Clean up photos older than 24 hours from incomplete submissions
        call_command(
            "cleanup_orphaned_photos",
            "--incomplete-only",
            "--older-than-hours=24",
            verbosity=1,
        )

    except Exception:
        logger.exception("Error in orphaned photos cleanup task")
        raise
    else:
        logger.info("Orphaned photos cleanup task completed successfully")
        return "Orphaned photos cleanup completed"


@shared_task
def cleanup_all_orphaned_photos():
    """
    Clean up all orphaned photos (both from incomplete submissions and general orphaned files).

    This is a more comprehensive cleanup that should be run less frequently.
    """
    try:
        logger.info("Starting comprehensive orphaned photos cleanup task")

        # Clean up all orphaned photos
        call_command(
            "cleanup_orphaned_photos",
            verbosity=1,
        )

    except Exception:
        logger.exception("Error in comprehensive orphaned photos cleanup task")
        raise
    else:
        logger.info("Comprehensive orphaned photos cleanup task completed successfully")
        return "Comprehensive orphaned photos cleanup completed"


@shared_task
def cleanup_old_incomplete_photos():
    """
    Clean up photos from incomplete submissions older than 7 days.

    This is for more aggressive cleanup of very old incomplete submissions.
    """
    try:
        logger.info("Starting old incomplete photos cleanup task")

        # Clean up photos older than 7 days from incomplete submissions
        call_command(
            "cleanup_orphaned_photos",
            "--incomplete-only",
            "--older-than-hours=168",  # 7 days = 168 hours
            verbosity=1,
        )

    except Exception:
        logger.exception("Error in old incomplete photos cleanup task")
        raise
    else:
        logger.info("Old incomplete photos cleanup task completed successfully")
        return "Old incomplete photos cleanup completed"
