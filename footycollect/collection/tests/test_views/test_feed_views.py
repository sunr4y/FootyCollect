import json
from unittest.mock import Mock, patch

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

    def test_build_autocomplete_initial_data_ignores_invalid_ids(self):
        data = _build_autocomplete_initial_data({"club": "x", "brand": "y"})
        assert data == {}


EXPECTED_SECONDARY_COLORS_COUNT = 2


class TestFeedViewHelperFunctions(TestCase):
    def test_get_feed_filter_choices_returns_expected_keys(self):
        from footycollect.collection.views.feed_views import _get_feed_filter_choices

        choices = _get_feed_filter_choices()
        assert "kit_type_choices" in choices
        assert "category_choices" in choices
        assert "color_choices_json" in choices
        assert isinstance(choices["kit_type_choices"], list)
        assert isinstance(choices["category_choices"], list)
        assert isinstance(choices["color_choices_json"], str)

    def test_main_color_display_returns_name_for_valid_id(self):
        from footycollect.collection.models import Color
        from footycollect.collection.views.feed_views import _main_color_display

        color = Color.objects.create(name="RED", hex_value="#FF0000")
        result = _main_color_display(str(color.id))
        assert result is not None

    def test_main_color_display_returns_none_for_invalid_id(self):
        from footycollect.collection.views.feed_views import _main_color_display

        assert _main_color_display("not-a-number") is None
        assert _main_color_display(None) is None

    def test_secondary_color_display_returns_none_for_empty_or_non_string(self):
        from footycollect.collection.views.feed_views import _secondary_color_display

        assert _secondary_color_display("") is None
        assert _secondary_color_display(None) is None
        assert _secondary_color_display(123) is None

    def test_secondary_color_display_returns_list_for_valid_comma_ids(self):
        from footycollect.collection.models import Color
        from footycollect.collection.views.feed_views import _secondary_color_display

        c1 = Color.objects.create(name="RED", hex_value="#FF0000")
        c2 = Color.objects.create(name="BLUE", hex_value="#0000FF")
        result = _secondary_color_display(f"{c1.id}, {c2.id}")
        assert isinstance(result, list)
        assert len(result) == EXPECTED_SECONDARY_COLORS_COUNT

    def test_secondary_color_display_returns_none_when_no_valid_ids(self):
        from footycollect.collection.views.feed_views import _secondary_color_display

        assert _secondary_color_display("a, b, c") is None

    def test_secondary_color_display_returns_none_on_valueerror(self):
        from footycollect.collection.models import Color
        from footycollect.collection.views.feed_views import _secondary_color_display

        c = Color.objects.create(name="RED", hex_value="#FF0000")
        with patch("footycollect.collection.utils_i18n.get_color_display_name", side_effect=ValueError):
            assert _secondary_color_display(f"{c.id}") is None

    def test_secondary_color_display_returns_none_on_typeerror(self):
        from footycollect.collection.models import Color
        from footycollect.collection.views.feed_views import _secondary_color_display

        c = Color.objects.create(name="RED", hex_value="#FF0000")
        with patch("footycollect.collection.utils_i18n.get_color_display_name", side_effect=TypeError):
            assert _secondary_color_display(f"{c.id}") is None

    def test_feed_random_sort_seed_hash_zero_uses_fallback_seed(self):
        import hashlib

        self.factory = RequestFactory()
        self.url = reverse(FEED_URL_NAME)
        request = self.factory.get(self.url, {"sort": SORT_RANDOM})
        request.session = {}
        request.user = None
        view = FeedView()
        view.request = request
        mock_hex = "0" * 8 + "a" * 56
        mock_sha = Mock()
        mock_sha.hexdigest.return_value = mock_hex

        with (
            patch("footycollect.collection.views.feed_views.FeedFilterService") as mock_svc,
            patch.object(hashlib, "sha256", return_value=mock_sha),
        ):
            mock_svc.return_value.parse_filters_from_request.return_value = {}
            mock_svc.return_value.apply_filters.return_value = Jersey.objects.none()
            mock_svc.return_value.apply_sorting.return_value = Jersey.objects.none()
            view.get_queryset()
        assert request.session["feed_random_seed_00000000"] == 123456789  # noqa: PLR2004

    def test_get_context_data_when_not_ajax(self):
        self.factory = RequestFactory()
        self.url = reverse(FEED_URL_NAME)
        request = self.factory.get(self.url, {"sort": SORT_NEWEST})
        request.session = {}
        request.META = {}
        view = FeedView()
        view.request = request
        view.object_list = Jersey.objects.none()
        view.kwargs = {}
        with patch("footycollect.collection.views.feed_views.FeedFilterService") as mock_svc:
            mock_svc.return_value.parse_filters_from_request.return_value = {}
            with patch("footycollect.collection.views.feed_views._get_feed_filter_choices") as mock_choices:
                mock_choices.return_value = {
                    "kit_type_choices": [],
                    "category_choices": [],
                    "color_choices_json": "[]",
                }
                context = view.get_context_data()
        assert context.get("is_ajax") is not True
