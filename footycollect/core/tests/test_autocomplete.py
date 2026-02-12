"""Tests for core autocomplete views."""

from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from footycollect.core.autocomplete import (
    DEFAULT_LOGO_URL,
    BrandAutocomplete,
    ClubAutocomplete,
    CountryAutocomplete,
    _logos_from_api,
)
from footycollect.core.models import Brand, Club


class TestBrandAutocomplete(TestCase):
    @patch("footycollect.api.client.FKAPIClient")
    def test_get_queryset_short_query_returns_empty(self, mock_client_class):
        view_obj = BrandAutocomplete()
        view_obj.request = RequestFactory().get("/", {"q": "n"})
        view_obj.q = "n"
        qs = view_obj.get_queryset()
        assert qs.count() == 0

    @patch("footycollect.api.client.FKAPIClient")
    def test_get_queryset_creates_brands_from_api(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.search_brands.return_value = [
            {"name": "Nike", "id": 1, "logo": "https://nike.png", "logo_dark": ""},
        ]
        mock_client_class.return_value = mock_client
        view_obj = BrandAutocomplete()
        view_obj.request = RequestFactory().get("/", {"q": "ni"})
        view_obj.q = "ni"
        qs = view_obj.get_queryset()
        mock_client.search_brands.assert_called_once_with(view_obj.q)
        assert qs.count() == 1
        assert qs.first().name == "Nike"

    def test_get_result_value_returns_id(self):
        view_obj = BrandAutocomplete()
        brand = Brand.objects.create(name="X", slug="x", logo="")
        assert view_obj.get_result_value(brand) == brand.id

    def test_get_result_label_and_results_generate_html(self):
        view_obj = BrandAutocomplete()
        brand = Brand.objects.create(name="Nike", slug="nike", logo="https://img.example/logo.png")
        label = view_obj.get_result_label(brand)
        assert "Nike" in str(label)
        assert "img" in str(label)

        context = {"object_list": [brand]}
        results = view_obj.get_results(context)
        assert len(results) == 1
        entry = results[0]
        assert entry["id"] == brand.id
        assert "html" in entry
        assert "Nike" in entry["html"]


class TestClubAutocomplete(TestCase):
    @patch("footycollect.api.client.FKAPIClient")
    def test_get_queryset_short_query_returns_empty(self, mock_client_class):
        view_obj = ClubAutocomplete()
        view_obj.request = RequestFactory().get("/", {"q": "a"})
        view_obj.q = "a"
        qs = view_obj.get_queryset()
        assert qs.count() == 0

    @patch("footycollect.api.client.FKAPIClient")
    def test_get_queryset_creates_club_from_api(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.search_clubs.return_value = [
            {"name": "FC Test", "id": 1, "logo": "https://club.png", "country": "ES"},
        ]
        mock_client_class.return_value = mock_client
        view_obj = ClubAutocomplete()
        view_obj.request = RequestFactory().get("/", {"q": "fc"})
        view_obj.q = "fc"
        qs = view_obj.get_queryset()
        mock_client.search_clubs.assert_called_once_with(view_obj.q)
        assert qs.count() == 1
        assert qs.first().name == "FC Test"

    def test_get_result_value_returns_id(self):
        view_obj = ClubAutocomplete()
        club = Club.objects.create(name="C", slug="c", country="ES", logo="")
        assert view_obj.get_result_value(club) == club.id


class TestCountryAutocomplete(TestCase):
    def test_get_list_filters_by_query(self):
        view_obj = CountryAutocomplete()
        view_obj.request = RequestFactory().get("/", {"q": "spain"})
        view_obj.q = "spain"
        result = view_obj.get_list()
        assert len(result) > 0
        for item in result:
            code, display = item
            display_text = str(display).lower()
            assert (
                view_obj.q.lower() in display_text
            ), f"Result ({code!r}, ...) display text should contain {view_obj.q.lower()!r}"

    def test_get_list_empty_query(self):
        view_obj = CountryAutocomplete()
        view_obj.request = RequestFactory().get("/", {"q": ""})
        view_obj.q = ""
        result = view_obj.get_list()
        assert len(result) > 0

    def test_get_list_short_query(self):
        view_obj = CountryAutocomplete()
        view_obj.request = RequestFactory().get("/", {"q": "z"})
        view_obj.q = "z"
        result = view_obj.get_list()
        for item in result:
            code, display = item
            assert "z" in str(display).lower(), f"Result for q='z' should have display containing 'z': ({code!r}, ...)"

    def test_get_result_value_returns_code(self):
        view_obj = CountryAutocomplete()
        result_item = ("ES", "Spain")
        assert view_obj.get_result_value(result_item) == "ES"


class TestLogosFromApi(TestCase):
    def test_logos_from_api_dict_and_non_dict(self):
        api_entity = {"logo": "https://logo.png", "logo_dark": ""}
        logo, logo_dark = _logos_from_api(api_entity)
        assert logo == "https://logo.png"
        assert logo_dark == DEFAULT_LOGO_URL

        logo2, logo_dark2 = _logos_from_api("not-a-dict")
        assert logo2 == DEFAULT_LOGO_URL
        assert logo_dark2 == DEFAULT_LOGO_URL
