import json
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.urls import reverse

from footycollect.collection.factories import BrandFactory, ClubFactory, JerseyFactory
from footycollect.collection.models import Jersey
from footycollect.collection.views.feed_views import (
    FeedView,
    _build_autocomplete_initial_data,
    _build_filter_display_names,
)

FEED_URL_NAME = "collection:feed"
SORT_NEWEST = "newest"
SORT_RANDOM = "random"
EXPECTED_FILTER_COUNT_FOR_TEST = 2


class TestFeedViewGetQueryset(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.url = reverse(FEED_URL_NAME)
        self.view = FeedView()

    def _set_request(self, sort_value: str) -> None:
        request = self.factory.get(self.url, {"sort": sort_value})
        request.session = {}
        self.view.request = request

    @patch("footycollect.collection.views.feed_views.FeedFilterService")
    def test_get_queryset_excludes_private_and_draft_items(self, mock_service_cls):
        public_jersey = JerseyFactory(base_item__is_private=False, base_item__is_draft=False)
        private_jersey = JerseyFactory(base_item__is_private=True, base_item__is_draft=False)
        draft_jersey = JerseyFactory(base_item__is_private=False, base_item__is_draft=True)

        mock_service = mock_service_cls.return_value
        mock_service.parse_filters_from_request.return_value = {}
        mock_service.apply_filters.side_effect = lambda qs, filters: qs
        mock_service.apply_sorting.side_effect = lambda qs, sort_type, seed=None: qs

        self._set_request(SORT_NEWEST)

        queryset = self.view.get_queryset()

        assert public_jersey in queryset
        assert private_jersey not in queryset
        assert draft_jersey not in queryset

        mock_service.parse_filters_from_request.assert_called_once_with(self.view.request)

    @patch("footycollect.collection.views.feed_views.FeedFilterService")
    def test_get_queryset_random_uses_stable_session_seed(self, mock_service_cls):
        JerseyFactory()

        mock_service = mock_service_cls.return_value
        mock_service.parse_filters_from_request.return_value = {}
        mock_service.apply_filters.side_effect = lambda qs, filters: qs

        captured = {}

        def fake_apply_sorting(qs, sort_type, seed=None):
            captured["seed"] = seed
            return qs

        mock_service.apply_sorting.side_effect = fake_apply_sorting

        request = self.factory.get(self.url, {"sort": SORT_RANDOM})
        request.session = {}
        self.view.request = request

        self.view.get_queryset()

        assert "seed" in captured
        seed_value = captured["seed"]
        assert isinstance(seed_value, int)

        seed_keys = [key for key in request.session if key.startswith("feed_random_seed_")]
        assert len(seed_keys) == 1
        assert request.session[seed_keys[0]] == seed_value

        captured.clear()
        self.view.get_queryset()

        assert captured["seed"] == seed_value
        assert request.session[seed_keys[0]] == seed_value


class TestFeedViewContext(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.url = reverse(FEED_URL_NAME)

    @patch("footycollect.collection.views.feed_views._build_autocomplete_initial_data")
    @patch("footycollect.collection.views.feed_views._build_filter_display_names")
    @patch("footycollect.collection.views.feed_views._get_feed_filter_choices")
    @patch("footycollect.collection.views.feed_views.FeedFilterService")
    def test_get_context_data_populates_expected_keys_for_ajax(
        self,
        mock_service_cls,
        mock_get_choices,
        mock_build_display_names,
        mock_build_autocomplete_data,
    ):
        mock_service = mock_service_cls.return_value
        filters = {"brand": "BrandX", "has_nameset": True}
        mock_service.parse_filters_from_request.return_value = filters

        mock_get_choices.return_value = {
            "kit_type_choices": ["Home"],
            "category_choices": ["match"],
            "color_choices_json": "[]",
        }
        mock_build_display_names.return_value = {"brand": "BrandX"}
        autocomplete_initial = {"brand": {"id": 1, "name": "BrandX", "logo": ""}}
        mock_build_autocomplete_data.return_value = autocomplete_initial

        request = self.factory.get(
            self.url,
            {"sort": SORT_NEWEST},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        request.session = {}

        view = FeedView()
        view.request = request
        view.object_list = Jersey.objects.none()
        view.kwargs = {}

        context = view.get_context_data()

        assert context["is_ajax"] is True
        assert context["active_filters"] == filters
        assert context["sort_type"] == SORT_NEWEST
        assert context["filter_count"] == EXPECTED_FILTER_COUNT_FOR_TEST
        assert context["kit_type_choices"] == ["Home"]
        assert context["category_choices"] == ["match"]
        assert context["color_choices_json"] == "[]"
        assert context["filter_display_names"] == {"brand": "BrandX"}
        assert json.loads(context["autocomplete_initial_data"]) == autocomplete_initial


class TestFeedViewHelpers(TestCase):
    def test_build_filter_display_names_includes_colors_and_nameset(self):
        with (
            patch(
                "footycollect.collection.views.feed_views._main_color_display",
                return_value="Red",
            ) as mock_main,
            patch(
                "footycollect.collection.views.feed_views._secondary_color_display",
                return_value=["Blue", "White"],
            ) as mock_secondary,
        ):
            filters = {
                "club": "My Club",
                "brand": "BrandY",
                "competition": "Some League",
                "main_color": "1",
                "secondary_color": "2,3",
                "has_nameset": True,
            }
            result = _build_filter_display_names(filters)

        mock_main.assert_called_once_with("1")
        mock_secondary.assert_called_once_with("2,3")
        assert result["club"] == "My Club"
        assert result["brand"] == "BrandY"
        assert result["competition"] == "Some League"
        assert result["main_color"] == "Red"
        assert result["secondary_color"] == ["Blue", "White"]
        assert result["has_nameset"] == "Has nameset"

    def test_build_autocomplete_initial_data_uses_valid_ids(self):
        brand = BrandFactory()
        club = ClubFactory()

        filters = {
            "club": str(club.id),
            "brand": str(brand.id),
        }

        data = _build_autocomplete_initial_data(filters)

        assert data["club"]["id"] == club.id
        assert data["club"]["name"] == club.name
        assert "logo" in data["club"]

        assert data["brand"]["id"] == brand.id
        assert data["brand"]["name"] == brand.name
        assert "logo" in data["brand"]
