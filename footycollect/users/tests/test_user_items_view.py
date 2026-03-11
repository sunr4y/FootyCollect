"""
Tests for UserItemListView collection statistics and filtering.
"""

from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from footycollect.collection.models import BaseItem, Color, Jersey, Size
from footycollect.core.models import Brand, Club, Competition, Season

User = get_user_model()


class TestUserItemListView(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="collector",
            email="collector@example.com",
            password="testpass123",  # NOSONAR - test fixture
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="testpass123",  # NOSONAR - test fixture
        )
        self.brand = Brand.objects.create(name="BrandA", slug="branda")
        self.club = Club.objects.create(name="Club A", slug="club-a")
        self.league = Competition.objects.create(name="League A", slug="league-a")
        self.season = Season.objects.create(year="2024-25", first_year="2024", second_year="2025")
        self.color = Color.objects.create(name="RED", hex_value="#FF0000")

        base_item = BaseItem.objects.create(
            item_type="jersey",
            name="Home Shirt",
            user=self.user,
            brand=self.brand,
            club=self.club,
            season=self.season,
            condition=10,
            detailed_condition="BNWT",
            is_replica=False,
            is_private=False,
            is_draft=False,
            design="PLAIN",
            main_color=self.color,
            country="ES",
        )
        base_item.competitions.add(self.league)

        size = Size.objects.create(name="L", category="tops")
        Jersey.objects.create(
            base_item=base_item,
            size=size,
        )

    def _get_url(self, **params):
        url = reverse("users:user_items", kwargs={"username": self.user.username})
        if not params:
            return url
        query = "&".join(f"{key}={value}" for key, value in params.items())
        return f"{url}?{query}"

    def test_user_items_view_includes_geo_stats_in_context(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self._get_url())

        assert response.status_code == HTTPStatus.OK
        assert response.context["is_user_collection"] is True
        assert response.context["geo_summary"]["clubs"] == 1
        assert response.context["geo_summary"]["countries"] == 1
        assert response.context["geo_summary"]["competitions"] == 1
        assert response.context["geo_summary"]["brands"] == 1
        assert response.context["geo_summary"]["designs"] == 1
        assert response.context["geo_summary"]["colors"] == 1

    def test_user_items_view_filters_by_club(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self._get_url(club=self.club.slug))

        assert response.status_code == HTTPStatus.OK
        assert len(response.context["items"]) == 1
        assert response.context["current_filters"]["club"] == self.club.slug

    def test_user_items_view_filters_by_country(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self._get_url(country="ES"))

        assert response.status_code == HTTPStatus.OK
        assert len(response.context["items"]) == 1
        assert response.context["current_filters"]["country"] == "ES"

    def test_user_items_view_filters_by_competition(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self._get_url(competition=self.league.slug))

        assert response.status_code == HTTPStatus.OK
        assert len(response.context["items"]) == 1
        assert response.context["current_filters"]["competition"] == self.league.slug

    def test_user_items_view_filters_by_brand(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self._get_url(brand=self.brand.slug))

        assert response.status_code == HTTPStatus.OK
        assert len(response.context["items"]) == 1
        assert response.context["current_filters"]["brand"] == self.brand.slug

    def test_user_items_view_filters_by_design(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self._get_url(design="PLAIN"))

        assert response.status_code == HTTPStatus.OK
        assert len(response.context["items"]) == 1
        assert response.context["current_filters"]["design"] == "PLAIN"

    def test_user_items_view_filters_by_color(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self._get_url(color=self.color.id))

        assert response.status_code == HTTPStatus.OK
        assert len(response.context["items"]) == 1
        assert str(self.color.id) == response.context["current_filters"]["color"]
