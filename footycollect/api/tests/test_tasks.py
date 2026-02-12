"""Tests for api Celery tasks."""
from unittest.mock import patch

import pytest

from footycollect.api.tasks import scrape_user_collection_task


@pytest.mark.django_db
class TestScrapeUserCollectionTask:
    def test_success_returns_api_result(self):
        with patch("footycollect.api.tasks.FKAPIClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.post_scrape_user_collection.return_value = {"scraped": True}
            result = scrape_user_collection_task(42)
        assert result == {"scraped": True}
        mock_client.post_scrape_user_collection.assert_called_once_with(42)

    def test_success_returns_empty_dict_when_api_returns_none(self):
        with patch("footycollect.api.tasks.FKAPIClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.post_scrape_user_collection.return_value = None
            result = scrape_user_collection_task(100)
        assert result == {}
        mock_client.post_scrape_user_collection.assert_called_once_with(100)

    def test_failure_reraises_exception(self):
        with patch("footycollect.api.tasks.FKAPIClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.post_scrape_user_collection.side_effect = RuntimeError("API down")
            with pytest.raises(RuntimeError, match="API down"):
                scrape_user_collection_task(1)
        mock_client.post_scrape_user_collection.assert_called_once_with(1)
