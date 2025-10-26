"""
Tests for collection tasks.
"""

from unittest.mock import patch

import pytest
from django.test import TestCase

from footycollect.collection.tasks import (
    cleanup_all_orphaned_photos,
    cleanup_old_incomplete_photos,
    cleanup_orphaned_photos,
)


class TestCleanupOrphanedPhotos(TestCase):
    """Test cases for cleanup_orphaned_photos task."""

    @patch("footycollect.collection.tasks.call_command")
    @patch("footycollect.collection.tasks.logger")
    def test_cleanup_orphaned_photos_success(self, mock_logger, mock_call_command):
        """Test successful orphaned photos cleanup."""
        mock_call_command.return_value = None

        result = cleanup_orphaned_photos()

        mock_logger.info.assert_any_call("Starting orphaned photos cleanup task")
        mock_logger.info.assert_any_call("Orphaned photos cleanup task completed successfully")
        mock_call_command.assert_called_once_with(
            "cleanup_orphaned_photos",
            "--incomplete-only",
            "--older-than-hours=24",
            verbosity=1,
        )
        assert result == "Orphaned photos cleanup completed"

    @patch("footycollect.collection.tasks.call_command")
    @patch("footycollect.collection.tasks.logger")
    def test_cleanup_orphaned_photos_exception(self, mock_logger, mock_call_command):
        """Test orphaned photos cleanup with exception."""
        mock_call_command.side_effect = Exception("Test error")

        with pytest.raises(Exception, match="Test error"):
            cleanup_orphaned_photos()

        mock_logger.info.assert_called_once_with("Starting orphaned photos cleanup task")
        mock_logger.exception.assert_called_once_with("Error in orphaned photos cleanup task")


class TestCleanupAllOrphanedPhotos(TestCase):
    """Test cases for cleanup_all_orphaned_photos task."""

    @patch("footycollect.collection.tasks.call_command")
    @patch("footycollect.collection.tasks.logger")
    def test_cleanup_all_orphaned_photos_success(self, mock_logger, mock_call_command):
        """Test successful comprehensive orphaned photos cleanup."""
        mock_call_command.return_value = None

        result = cleanup_all_orphaned_photos()

        mock_logger.info.assert_any_call("Starting comprehensive orphaned photos cleanup task")
        mock_logger.info.assert_any_call("Comprehensive orphaned photos cleanup task completed successfully")
        mock_call_command.assert_called_once_with(
            "cleanup_orphaned_photos",
            verbosity=1,
        )
        assert result == "Comprehensive orphaned photos cleanup completed"

    @patch("footycollect.collection.tasks.call_command")
    @patch("footycollect.collection.tasks.logger")
    def test_cleanup_all_orphaned_photos_exception(self, mock_logger, mock_call_command):
        """Test comprehensive orphaned photos cleanup with exception."""
        mock_call_command.side_effect = Exception("Test error")

        with pytest.raises(Exception, match="Test error"):
            cleanup_all_orphaned_photos()

        mock_logger.info.assert_called_once_with("Starting comprehensive orphaned photos cleanup task")
        mock_logger.exception.assert_called_once_with("Error in comprehensive orphaned photos cleanup task")


class TestCleanupOldIncompletePhotos(TestCase):
    """Test cases for cleanup_old_incomplete_photos task."""

    @patch("footycollect.collection.tasks.call_command")
    @patch("footycollect.collection.tasks.logger")
    def test_cleanup_old_incomplete_photos_success(self, mock_logger, mock_call_command):
        """Test successful old incomplete photos cleanup."""
        mock_call_command.return_value = None

        result = cleanup_old_incomplete_photos()

        mock_logger.info.assert_any_call("Starting old incomplete photos cleanup task")
        mock_logger.info.assert_any_call("Old incomplete photos cleanup task completed successfully")
        mock_call_command.assert_called_once_with(
            "cleanup_orphaned_photos",
            "--incomplete-only",
            "--older-than-hours=168",
            verbosity=1,
        )
        assert result == "Old incomplete photos cleanup completed"

    @patch("footycollect.collection.tasks.call_command")
    @patch("footycollect.collection.tasks.logger")
    def test_cleanup_old_incomplete_photos_exception(self, mock_logger, mock_call_command):
        """Test old incomplete photos cleanup with exception."""
        mock_call_command.side_effect = Exception("Test error")

        with pytest.raises(Exception, match="Test error"):
            cleanup_old_incomplete_photos()

        mock_logger.info.assert_called_once_with("Starting old incomplete photos cleanup task")
        mock_logger.exception.assert_called_once_with("Error in old incomplete photos cleanup task")
