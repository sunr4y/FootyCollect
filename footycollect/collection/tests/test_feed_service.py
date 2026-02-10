"""
Tests for FeedFilterService.
"""

from unittest.mock import MagicMock

from django.test import TestCase

from footycollect.collection.factories import (
    BrandFactory,
    ClubFactory,
    JerseyFactory,
    KitFactory,
    SeasonFactory,
    TypeKFactory,
)
from footycollect.collection.models import Jersey
from footycollect.collection.services.feed_service import FeedFilterService


class TestFeedFilterServiceApplyFilters(TestCase):
    def setUp(self):
        self.service = FeedFilterService()
        self.base_qs = Jersey.objects.public()

    def test_apply_filters_empty_dict_returns_queryset_unchanged(self):
        result = self.service.apply_filters(self.base_qs, {})
        result_sql = result.query.get_compiler(result.db).as_sql()
        base_sql = self.base_qs.query.get_compiler(self.base_qs.db).as_sql()
        assert result_sql == base_sql

    def test_apply_filters_country_filters_by_club_country_or_base_item_country(self):
        qs = self.service.apply_filters(self.base_qs, {"country": "ES"})
        qs_query = str(qs.query)
        assert "club__country" in qs_query or "country" in qs_query

    def test_apply_filters_country_empty_string_ignored(self):
        result = self.service.apply_filters(self.base_qs, {"country": ""})
        assert list(result) == list(self.base_qs)

    def test_apply_filters_club_by_id(self):
        club = ClubFactory()
        j = JerseyFactory(base_item__club=club)
        filtered = self.service.apply_filters(self.base_qs, {"club": str(club.id)})
        assert j in filtered

    def test_apply_filters_club_by_slug(self):
        club = ClubFactory(slug="my-club")
        j = JerseyFactory(base_item__club=club)
        filtered = self.service.apply_filters(self.base_qs, {"club": "my-club"})
        assert j in filtered

    def test_apply_filters_brand_by_id(self):
        brand = BrandFactory()
        j = JerseyFactory(base_item__brand=brand)
        filtered = self.service.apply_filters(self.base_qs, {"brand": str(brand.id)})
        assert j in filtered

    def test_apply_filters_season(self):
        season = SeasonFactory(year="2024-25")
        j = JerseyFactory(base_item__season=season)
        filtered = self.service.apply_filters(self.base_qs, {"season": "2024-25"})
        assert j in filtered

    def test_apply_filters_has_nameset_true(self):
        j = JerseyFactory(has_nameset=True)
        filtered = self.service.apply_filters(self.base_qs, {"has_nameset": True})
        assert j in filtered

    def test_apply_filters_kit_type_by_id(self):
        type_k = TypeKFactory(name="Home", category="match")
        j = JerseyFactory()
        kit = KitFactory(
            team=j.base_item.club,
            season=j.base_item.season,
            brand=j.base_item.brand,
            type=type_k,
        )
        j.kit = kit
        j.save()
        filtered = self.service.apply_filters(self.base_qs, {"kit_type": str(type_k.id)})
        assert j in filtered

    def test_apply_filters_category(self):
        type_k = TypeKFactory(name="Away", category="match")
        j = JerseyFactory()
        kit = KitFactory(
            team=j.base_item.club,
            season=j.base_item.season,
            brand=j.base_item.brand,
            type=type_k,
        )
        j.kit = kit
        j.save()
        filtered = self.service.apply_filters(self.base_qs, {"category": "match"})
        assert j in filtered

    def test_apply_filters_search_q(self):
        brand = BrandFactory(name="UniqueBrandName")
        j = JerseyFactory(base_item__brand=brand, base_item__name="UniqueBrandName Jersey")
        filtered = self.service.apply_filters(self.base_qs, {"q": "UniqueBrandName"})
        assert j in filtered


class TestFeedFilterServiceApplySorting(TestCase):
    def setUp(self):
        self.service = FeedFilterService()
        self.jersey = JerseyFactory()
        self.qs = Jersey.objects.public()

    def test_apply_sorting_newest_orders_by_created_at_desc(self):
        result = self.service.apply_sorting(self.qs, sort_type="newest")
        assert "base_item__created_at" in str(result.query.order_by)

    def test_apply_sorting_random_with_seed_uses_annotate(self):
        result = self.service.apply_sorting(self.qs, sort_type="random", seed=42)
        assert "random_order" in str(result.query)

    def test_apply_sorting_random_without_seed_orders_by_random(self):
        result = self.service.apply_sorting(self.qs, sort_type="random")
        assert "?" in str(result.query.order_by) or "random" in str(result.query).lower()

    def test_apply_sorting_invalid_seed_coerced_to_none(self):
        result = self.service.apply_sorting(self.qs, sort_type="random", seed="not-a-number")
        # Should behave like random without seed
        assert "?" in str(result.query.order_by) or "random" in str(result.query).lower()


class TestFeedFilterServiceParseFiltersFromRequest(TestCase):
    def setUp(self):
        self.service = FeedFilterService()

    def test_parse_filters_empty_request_returns_empty_dict(self):
        request = MagicMock()
        request.GET.get.side_effect = lambda k, d=None: d
        request.GET.getlist.side_effect = lambda k: []
        result = self.service.parse_filters_from_request(request)
        assert result == {}

    def test_parse_filters_country_uppercased(self):
        request = MagicMock()
        request.GET.get.side_effect = lambda k, d=None: " es " if k == "country" else d
        request.GET.getlist.side_effect = lambda k: []
        result = self.service.parse_filters_from_request(request)
        assert "ES" in result.get("country", "")

    def test_parse_filters_club_brand_season_included(self):
        request = MagicMock()
        data = {"club": "  barca  ", "brand": " nike ", "season": " 2024-25 "}

        def get(k, d=None):
            return data.get(k, d)

        request.GET.get.side_effect = get
        request.GET.getlist.side_effect = lambda k: []
        result = self.service.parse_filters_from_request(request)
        assert "barca" in result.get("club", "")
        assert "nike" in result.get("brand", "")
        assert "2024-25" in result.get("season", "")

    def test_parse_filters_has_nameset_true_values(self):
        for val in ("1", "true", "on", "yes"):
            request = MagicMock()
            request.GET.get.side_effect = lambda k, d=None, v=val: v if k == "has_nameset" else d
            request.GET.getlist.side_effect = lambda k: []
            result = self.service.parse_filters_from_request(request)
            assert result.get("has_nameset")

    def test_parse_filters_competition_list(self):
        request = MagicMock()
        request.GET.get.side_effect = lambda k, d=None: d
        request.GET.getlist.side_effect = lambda k: [1, 2] if k == "competition" else []
        result = self.service.parse_filters_from_request(request)
        assert result.get("competition") == [1, 2]

    def test_parse_filters_q_stripped(self):
        request = MagicMock()
        request.GET.get.side_effect = lambda k, d=None: "  search term  " if k == "q" else d
        request.GET.getlist.side_effect = lambda k: []
        result = self.service.parse_filters_from_request(request)
        assert result.get("q") == "search term"


class TestFeedFilterServiceBuildFilterUrl(TestCase):
    def setUp(self):
        self.service = FeedFilterService()

    def test_build_filter_url_empty_dict_returns_base_url(self):
        result = self.service.build_filter_url("https://example.com/feed/", {})
        assert result == "https://example.com/feed/"

    def test_build_filter_url_single_param(self):
        result = self.service.build_filter_url("https://example.com/feed/", {"country": "ES"})
        assert "country=ES" in result
        assert result.startswith("https://example.com/feed/?")

    def test_build_filter_url_multiple_params(self):
        result = self.service.build_filter_url(
            "https://example.com/feed/",
            {"country": "ES", "season": "2024-25"},
        )
        assert "country=ES" in result
        assert "season=2024-25" in result
