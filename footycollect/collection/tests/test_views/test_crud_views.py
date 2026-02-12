"""
Tests for crud_views: ItemCreateView, ItemUpdateView, ItemDeleteView.
"""

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from footycollect.collection.factories import (
    BaseItemFactory,
    BrandFactory,
    ClubFactory,
    JerseyFactory,
    PhotoFactory,
    SeasonFactory,
    SizeFactory,
    UserFactory,
)
from footycollect.collection.forms import JerseyForm
from footycollect.collection.models import Photo
from footycollect.collection.views.crud_views import (
    ItemCreateView,
    ItemDeleteView,
    ItemUpdateView,
)

User = get_user_model()

TEST_PASSWORD = "testpass123"
HTTP_OK = 200


class TestItemCreateViewCrud(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.user.set_password(TEST_PASSWORD)
        self.user.save()

    def test_get_form_class_returns_jersey_form(self):
        request = RequestFactory().get(reverse("collection:item_create"))
        request.user = self.user
        view = ItemCreateView()
        view.request = request
        view.setup(request)
        assert view.get_form_class() is JerseyForm

    def test_get_context_data_includes_color_and_design_choices(self):
        self.client.login(username=self.user.username, password=TEST_PASSWORD)
        response = self.client.get(reverse("collection:item_create"))
        assert response.status_code == HTTP_OK
        assert "color_choices" in response.context
        assert "design_choices" in response.context


class TestItemUpdateViewCrud(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.user.set_password(TEST_PASSWORD)
        self.user.save()
        self.brand = BrandFactory()
        self.club = ClubFactory()
        self.season = SeasonFactory()
        self.size = SizeFactory()
        self.base_item = BaseItemFactory(
            user=self.user,
            brand=self.brand,
            club=self.club,
            season=self.season,
        )
        self.jersey = JerseyFactory(base_item=self.base_item, size=self.size)
        self.base_item.refresh_from_db()

    def test_parse_photo_ids_invalid_json_returns_none(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        assert view._parse_photo_ids("not-json") is None
        assert view._parse_photo_ids("{invalid") is None

    def test_parse_photo_ids_non_list_returns_none(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        assert view._parse_photo_ids("{}") is None
        assert view._parse_photo_ids("123") is None

    def test_parse_photo_ids_valid_list_returns_parsed(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        result = view._parse_photo_ids('[{"id": 1, "order": 0}]')
        assert result == [{"id": 1, "order": 0}]

    def test_extract_photo_data_skips_non_dict_items(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        keep_ids, order_map, external = view._extract_photo_data([1, "x", None])
        assert keep_ids == set()
        assert order_map == {}
        assert external == []

    def test_extract_photo_data_external_with_url(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        keep_ids, order_map, external = view._extract_photo_data([
            {"external": True, "url": "https://example.com/img.jpg", "order": 2},
        ])
        assert keep_ids == set()
        assert order_map == {}
        assert external == [{"url": "https://example.com/img.jpg", "order": 2}]

    def test_extract_photo_data_photo_id_invalid_skipped(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        keep_ids, order_map, _ = view._extract_photo_data([
            {"id": "not-an-int", "order": 0},
        ])
        assert keep_ids == set()
        assert order_map == {}

    def test_extract_photo_data_photo_id_valid(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        keep_ids, order_map, _ = view._extract_photo_data([
            {"id": 42, "order": 1},
            {"id": "99", "order": 2},
        ])
        assert keep_ids == {42, 99}
        assert order_map == {42: 1, 99: 2}

    def test_update_existing_photos_empty_keep_ids_returns_early(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        view._update_existing_photos(set(), {})

    def test_update_existing_photos_attaches_photos_and_updates_order(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        photo = PhotoFactory(content_object=self.base_item, user=self.user, order=0)
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        expected_order = 2
        view._update_existing_photos({photo.id}, {photo.id: expected_order})
        photo.refresh_from_db()
        assert photo.object_id == self.base_item.pk
        assert photo.order == expected_order

    def test_remove_deleted_photos_exception_logged(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        qs = Mock()
        qs.exclude.return_value = qs
        qs.exists.return_value = True
        qs.delete.side_effect = OSError
        mock_obj = Mock()
        mock_obj.photos.filter.return_value = qs
        view.object = mock_obj
        view.setup(request)
        with patch("footycollect.collection.views.crud_views.logger") as mock_logger:
            view._remove_deleted_photos({1})
        mock_logger.exception.assert_called_once()

    def test_get_context_data_has_is_edit_and_initial_photos(self):
        self.client.login(username=self.user.username, password=TEST_PASSWORD)
        url = reverse("collection:item_update", kwargs={"pk": self.base_item.pk})
        response = self.client.get(url)
        assert response.status_code == HTTP_OK
        assert response.context.get("is_edit") is True
        assert "initial_photos" in response.context
        assert "autocomplete_initial_data" in response.context

    def test_build_photo_dict_fallback_when_get_image_url_raises(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        photo = Mock(spec=Photo)
        photo.id = 1
        photo.order = 0
        photo.image = Mock(name="x.jpg")
        photo.image.name = "item_photos/x.jpg"
        photo.get_image_url = Mock(side_effect=ValueError)
        photo.thumbnail = None
        d = view._build_photo_dict(photo)
        assert d["id"] == 1
        assert d["order"] == 0
        assert "/media/item_photos/x.jpg" in d["url"] or "item_photos" in d["url"]

    def test_add_initial_photos_exception_sets_empty_json(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        mock_obj = Mock()
        mock_obj.photos.order_by.side_effect = OSError
        view.object = mock_obj
        view.setup(request)
        context = {}
        view._add_initial_photos(context)
        assert context.get("initial_photos") == "[]"

    def test_add_autocomplete_initial_data_exception_sets_empty_dict(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        context = {}
        with patch.object(ItemUpdateView, "get_object", side_effect=KeyError):
            view._add_autocomplete_initial_data(context)
        assert context.get("autocomplete_initial_data") == "{}"

    def test_get_kit_from_base_item_no_jersey_returns_none(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        base_item = Mock()
        del base_item.jersey
        assert view._get_kit_from_base_item(base_item) is None

    def test_get_kit_from_base_item_jersey_no_kit_returns_none(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        base_item = Mock()
        base_item.jersey = Mock()
        base_item.jersey.kit = None
        assert view._get_kit_from_base_item(base_item) is None

    def test_get_entity_data_from_kit_when_base_item_has_none(self):
        from types import SimpleNamespace

        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        base_item = Mock()
        base_item.club = None
        kit = Mock()
        kit.team = SimpleNamespace(id=1, name="Team", logo="http://logo.png")
        result = view._get_entity_data(base_item, kit, "club", "team")
        assert result == {"id": 1, "name": "Team", "logo": "http://logo.png"}

    def test_get_season_data_from_kit(self):
        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        base_item = Mock()
        base_item.season = None
        kit = Mock()
        kit.season = Mock(id=1, year="2024")
        result = view._get_season_data(base_item, kit)
        assert result == {"id": 1, "name": "2024", "logo": ""}

    def test_get_competitions_data_from_kit(self):
        from types import SimpleNamespace

        request = RequestFactory().post("/", data={})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        base_item = Mock()
        base_item.competitions = Mock(all=Mock(return_value=[]))
        kit = Mock()
        comp = SimpleNamespace(id=1, name="League", logo="")
        kit.competition = Mock(all=Mock(return_value=[comp]))
        result = view._get_competitions_data(base_item, kit)
        assert result == [{"id": 1, "name": "League", "logo": ""}]

    def test_form_valid_with_photo_ids_calls_update_and_remove_photos(self):
        request = RequestFactory().post("/", data={"photo_ids": '[{"id": 999, "order": 1}]'})
        request.user = self.user
        view = ItemUpdateView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        form = Mock()
        with (
            patch("footycollect.collection.views.crud_views.BaseItemUpdateView.form_valid") as super_valid,
            patch.object(view, "_update_existing_photos") as mock_update,
            patch.object(view, "_remove_deleted_photos") as mock_remove,
        ):
            super_valid.return_value = Mock()
            view.form_valid(form)
            super_valid.assert_called_once_with(form)
            mock_update.assert_called_once_with({999}, {999: 1})
            mock_remove.assert_called_once_with({999})


class TestItemDeleteViewCrud(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.user.set_password(TEST_PASSWORD)
        self.user.save()
        self.base_item = BaseItemFactory(user=self.user)
        self.jersey = JerseyFactory(base_item=self.base_item)

    def test_get_success_url_with_page_appends_query(self):
        request = RequestFactory().post("/", data={"page": "3"})
        request.user = self.user
        view = ItemDeleteView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        url = view.get_success_url()
        assert "page=3" in url

    def test_get_success_url_page_one_returns_base_url(self):
        request = RequestFactory().post("/", data={"page": "1"})
        request.user = self.user
        view = ItemDeleteView()
        view.request = request
        view.object = self.base_item
        view.setup(request)
        url = view.get_success_url()
        assert reverse("collection:item_list") in url
        assert "page=" not in url
