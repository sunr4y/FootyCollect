import logging

from celery import shared_task

from .client import FKAPIClient

logger = logging.getLogger(__name__)


@shared_task
def scrape_user_collection_task(userid: int):
    client = FKAPIClient()
    try:
        result = client.post_scrape_user_collection(userid)
    except Exception:
        logger.exception("Error scraping user collection for user %s", userid)
        raise
    else:
        return result or {}
