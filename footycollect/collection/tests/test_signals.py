"""Tests for collection signals."""

from unittest.mock import patch

from django.test import TestCase

from footycollect.collection.factories import JerseyFactory, PhotoFactory


class TestSignalsCacheInvalidation(TestCase):
    @patch("footycollect.collection.signals.invalidate_item_list_cache_for_user")
    def test_base_item_post_save_triggers_invalidate(self, mock_invalidate):
        j = JerseyFactory()
        mock_invalidate.reset_mock()
        j.base_item.name = "Updated"
        j.base_item.save()
        mock_invalidate.assert_called_once_with(j.base_item.user_id)

    @patch("footycollect.collection.signals.invalidate_item_list_cache_for_user")
    def test_base_item_post_delete_triggers_invalidate(self, mock_invalidate):
        j = JerseyFactory()
        user_id = j.base_item.user_id
        mock_invalidate.reset_mock()
        j.base_item.delete()
        assert mock_invalidate.call_count >= 1
        mock_invalidate.assert_any_call(user_id)

    @patch("footycollect.collection.signals.invalidate_item_list_cache_for_user")
    def test_jersey_post_save_triggers_invalidate(self, mock_invalidate):
        j = JerseyFactory()
        mock_invalidate.reset_mock()
        j.save()
        assert mock_invalidate.call_count >= 1
        mock_invalidate.assert_any_call(j.base_item.user_id)

    @patch("footycollect.collection.signals.invalidate_item_list_cache_for_user")
    def test_jersey_post_delete_triggers_invalidate(self, mock_invalidate):
        j = JerseyFactory()
        user_id = j.base_item.user_id
        mock_invalidate.reset_mock()
        j.delete()
        mock_invalidate.assert_called_once_with(user_id)

    @patch("footycollect.collection.signals.invalidate_item_list_cache_for_user")
    def test_photo_post_save_triggers_invalidate_via_content_object(self, mock_invalidate):
        j = JerseyFactory()
        photo = PhotoFactory(content_object=j, user=j.base_item.user)
        mock_invalidate.reset_mock()
        photo.save()
        mock_invalidate.assert_called_once_with(j.base_item.user_id)

    @patch("footycollect.collection.signals.invalidate_item_list_cache_for_user")
    def test_photo_post_delete_triggers_invalidate(self, mock_invalidate):
        j = JerseyFactory()
        photo = PhotoFactory(content_object=j, user=j.base_item.user)
        user_id = j.base_item.user_id
        mock_invalidate.reset_mock()
        photo.delete()
        mock_invalidate.assert_called_once_with(user_id)

    @patch("footycollect.collection.signals.invalidate_item_list_cache_for_user")
    def test_photo_without_content_object_does_not_crash(self, mock_invalidate):
        photo = PhotoFactory(content_object=None, user=None)
        photo.content_object = None
        photo.save()
        mock_invalidate.assert_not_called()
