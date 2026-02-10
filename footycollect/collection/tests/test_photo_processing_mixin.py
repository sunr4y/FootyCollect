import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from footycollect.collection.factories import BaseItemFactory, PhotoFactory, UserFactory
from footycollect.collection.models import BaseItem
from footycollect.collection.views.jersey.mixins.photo_processing_mixin import PhotoProcessingMixin

User = get_user_model()


NUM_EXTERNAL_IMAGES = 2
MAIN_IMAGE_ORDER = 5
START_ORDER = 10
FIRST_PHOTO_OFFSET = 2
EXPECTED_FIRST_ORDER = START_ORDER + FIRST_PHOTO_OFFSET
MAX_EXPECTED_SECOND_ORDER = START_ORDER + 1


class DummyPhotoView(PhotoProcessingMixin):
    def __init__(self, user, obj):
        self.request = SimpleNamespace(user=user)
        self.object = obj
        self._download_and_attach_image = lambda *args, **kwargs: None


def test_parse_photo_ids_returns_empty_for_non_string_input():
    mixin = PhotoProcessingMixin()

    photo_ids, external_images, order_map = mixin._parse_photo_ids(123)  # type: ignore[arg-type]

    assert photo_ids == []
    assert external_images == []
    assert order_map == {}


def test_parse_photo_ids_parses_json_payload_with_ids_and_urls():
    mixin = PhotoProcessingMixin()

    payload = json.dumps(
        [
            1,
            {"id": 2, "order": 7},
            {"url": "https://example.com/a.jpg", "order": 0},
            {"id": "3"},
        ],
    )

    photo_ids, external_images, order_map = mixin._parse_photo_ids(payload)

    assert set(photo_ids) == {"1", "2", "3"}
    assert len(external_images) == 1
    assert external_images[0]["url"] == "https://example.com/a.jpg"
    assert external_images[0]["order"] == 0
    assert order_map == {"2": 7}


def test_parse_photo_ids_falls_back_to_comma_separated_list():
    mixin = PhotoProcessingMixin()

    photo_ids, external_images, order_map = mixin._parse_photo_ids("1, 2 , 3")

    assert photo_ids == ["1", "2", "3"]
    assert external_images == []
    assert order_map == {}


def test_process_external_images_from_photo_ids_uses_order_and_index():
    user = SimpleNamespace()
    dummy_object = SimpleNamespace()
    view = DummyPhotoView(user=user, obj=dummy_object)
    base_item = SimpleNamespace()

    external_images = [
        {"url": "https://example.com/main.jpg", "order": MAIN_IMAGE_ORDER},
        {"url": "https://example.com/alt.jpg"},
    ]

    with patch.object(view, "_download_and_attach_image") as mock_download:
        view._process_external_images_from_photo_ids(external_images, base_item=base_item)

    assert mock_download.call_count == NUM_EXTERNAL_IMAGES

    first_call_args, first_call_kwargs = mock_download.call_args_list[0]
    assert first_call_args[0] == base_item
    assert first_call_args[1] == "https://example.com/main.jpg"
    assert first_call_kwargs["order"] == MAIN_IMAGE_ORDER

    second_call_args, second_call_kwargs = mock_download.call_args_list[1]
    assert second_call_args[0] == base_item
    assert second_call_args[1] == "https://example.com/alt.jpg"
    assert second_call_kwargs["order"] == 1


@pytest.mark.django_db
def test_associate_existing_photos_filters_by_user_and_sets_content_type_and_order():
    user = UserFactory()
    base_item = BaseItemFactory(user=user)
    view = DummyPhotoView(user=user, obj=base_item)

    first_photo = PhotoFactory(user=user)
    second_photo = PhotoFactory(user=user)
    other_user_photo = PhotoFactory()

    photo_ids = [str(first_photo.id), str(second_photo.id), str(other_user_photo.id)]
    order_map = {str(first_photo.id): FIRST_PHOTO_OFFSET}
    original_object_id = other_user_photo.object_id

    view._associate_existing_photos(photo_ids, order_map, base_item=base_item, start_order=10)

    first_photo.refresh_from_db()
    second_photo.refresh_from_db()
    other_user_photo.refresh_from_db()

    expected_ct = ContentType.objects.get_for_model(BaseItem)

    assert first_photo.content_type == expected_ct
    assert second_photo.content_type == expected_ct
    assert first_photo.object_id == base_item.id
    assert second_photo.object_id == base_item.id
    assert first_photo.order == EXPECTED_FIRST_ORDER
    # second_photo can be processed before or after first_photo in the queryset,
    # so its calculated order may be START_ORDER or START_ORDER + 1.
    assert START_ORDER <= second_photo.order <= MAX_EXPECTED_SECOND_ORDER

    assert other_user_photo.object_id == original_object_id
