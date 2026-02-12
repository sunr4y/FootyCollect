"""
Extra tests to push coverage toward 80%.
Covers single-line missing branches and small gaps.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from footycollect.collection.models import BaseItem
from footycollect.collection.views.base import BaseItemListView
from footycollect.collection.views.feed_views import _secondary_color_display
from footycollect.core.models import Brand, Club, Season


class TestBaseItemListViewLenBranch(TestCase):
    """Test BaseItemListView context when object_list has no .count."""

    def test_get_context_data_uses_len_when_object_list_has_no_count(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="covuser", email="c@x.com", password="testpass123"
        )
        brand = Brand.objects.create(name="B", slug="b")
        club = Club.objects.create(name="C", slug="c")
        season = Season.objects.create(year="2024")
        item = BaseItem.objects.create(user=user, name="I", brand=brand, club=club, season=season)

        class ListWithoutCount:
            def __init__(self, items):
                self._items = list(items)

            def __len__(self):
                return len(self._items)

        view = BaseItemListView()
        view.request = RequestFactory().get("/")
        view.request.user = user
        view.object_list = ListWithoutCount([item])
        with patch("footycollect.collection.views.base.ListView.get_context_data") as m:
            m.return_value = {}
            ctx = view.get_context_data()
        assert ctx["total_items"] == 1


class TestSecondaryColorDisplayException(TestCase):
    """Test _secondary_color_display with invalid inputs."""

    def test_secondary_color_display_returns_none_on_invalid_value(self):
        assert _secondary_color_display(None) is None
        assert _secondary_color_display(123) is None
        assert _secondary_color_display([]) is None


class TestClubLogoDarkDisplayUrl(TestCase):
    """Test Club logo_dark_display_url."""

    def test_logo_dark_display_url_when_no_file(self):
        club = Club.objects.create(name="T", slug="t-dark")
        assert club.logo_dark_display_url == ""
        club.logo_dark = "http://example.com/dark.png"
        club.save()
        assert club.logo_dark_display_url == "http://example.com/dark.png"

