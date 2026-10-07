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
        response = self.client.get(self._get_url(), follow=True)

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
        response = self.client.get(self._get_url(club=self.club.slug), follow=True)

        assert response.status_code == HTTPStatus.OK
        assert len(response.context["items"]) == 1
        assert response.context["current_filters"]["club"] == self.club.slug

    def test_user_items_view_filters_by_country(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self._get_url(country="ES"), follow=True)

        assert response.status_code == HTTPStatus.OK
        assert len(response.context["items"]) == 1
        assert response.context["current_filters"]["country"] == "ES"

    def test_user_items_view_filters_by_competition(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self._get_url(competition=self.league.slug), follow=True)

        assert response.status_code == HTTPStatus.OK
        assert len(response.context["items"]) == 1
        assert response.context["current_filters"]["competition"] == self.league.slug

    def test_user_items_view_filters_by_brand(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self._get_url(brand=self.brand.slug), follow=True)

        assert response.status_code == HTTPStatus.OK
        assert len(response.context["items"]) == 1
        assert response.context["current_filters"]["brand"] == self.brand.slug

    def test_user_items_view_filters_by_design(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self._get_url(design="PLAIN"), follow=True)

        assert response.status_code == HTTPStatus.OK
        assert len(response.context["items"]) == 1
        assert response.context["current_filters"]["design"] == "PLAIN"

    def test_user_items_view_filters_by_color(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self._get_url(color=self.color.id), follow=True)

        assert response.status_code == HTTPStatus.OK
        assert len(response.context["items"]) == 1
        assert str(self.color.id) == response.context["current_filters"]["color"]

    def test_user_items_view_filters_by_fit_for_owner_only(self):
        """Fit filter is applied but only exposed as 'How it fits' to the owner."""
        # First, owner with valid fit value
        self.client.force_login(self.user)
        Jersey.objects.update(fit="TRUE_TO_SIZE")
        response = self.client.get(self._get_url(fit="TRUE_TO_SIZE"), follow=True)

        assert response.status_code == HTTPStatus.OK
        assert len(response.context["items"]) == 1
        assert response.context["profile_user"] == self.user

        # Now, other user hitting the same URL: queryset still filtered,
        # but active fit filter chip should not be rendered for non-owners.
        self.client.force_login(self.other_user)
        response_other = self.client.get(self._get_url(fit="TRUE_TO_SIZE"), follow=True)

        assert response_other.status_code == HTTPStatus.OK
        assert len(response_other.context["items"]) == 1
        assert response_other.context["profile_user"] == self.user
        active_filters = response_other.context["active_filters_display"]
        assert all(f["type"] != "fit" for f in active_filters)
