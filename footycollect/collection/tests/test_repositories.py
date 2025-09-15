"""
Tests for repository classes.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from footycollect.collection.models import BaseItem, Brand, Club, Season
from footycollect.collection.repositories.item_repository import ItemRepository

User = get_user_model()


class TestItemRepository(TestCase):
    """Test cases for ItemRepository."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",  # noqa: S106
        )
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="testpass123",  # noqa: S106
        )

        # Create test data
        self.brand = Brand.objects.create(name="Nike")
        self.club = Club.objects.create(name="FC Barcelona", country="ES")
        self.season = Season.objects.create(year="2023-24", first_year="2023", second_year="24")

        # Create test items using MTI structure
        self.jersey = self._create_jersey_with_mti(
            user=self.user,
            name="Test Jersey",
            brand=self.brand,
            club=self.club,
            season=self.season,
        )

        self.other_jersey = self._create_jersey_with_mti(
            user=self.other_user,
            name="Other Jersey",
            brand=self.brand,
            club=self.club,
            season=self.season,
        )

        self.repository = ItemRepository()

    def _create_jersey_with_mti(self, user, name, brand, club, season, **kwargs):
        """Helper method to create jersey with STI structure."""
        # Create BaseItem with item_type="jersey" (MTI structure)
        return BaseItem.objects.create(
            item_type="jersey",
            name=name,
            user=user,
            brand=brand,
            club=club,
            season=season,
            condition=5,
            design="PLAIN",
            country="ES",
            **kwargs,
        )

    def test_get_user_items(self):
        """Test getting items for a specific user."""
        items = self.repository.get_user_items(self.user)

        assert items.count() == 1
        assert items.first().user == self.user

    def test_get_user_items_with_type_filter(self):
        """Test getting user items filtered by type."""
        items = self.repository.get_user_items(self.user, item_type="jersey")

        assert items.count() == 1

    def test_get_public_items(self):
        """Test getting public items."""
        # Make items public
        self.jersey.is_draft = False
        self.jersey.is_private = False
        self.jersey.save()

        self.other_jersey.is_draft = False
        self.other_jersey.is_private = False
        self.other_jersey.save()

        items = self.repository.get_public_items()

        expected_count = 2
        assert items.count() == expected_count

    def test_search_items(self):
        """Test searching items by description."""
        # Make items public
        self.jersey.is_draft = False
        self.jersey.is_private = False
        self.jersey.description = "Test jersey description"
        self.jersey.save()

        items = self.repository.search_items("Test")

        assert items.count() == 1

    def test_get_items_by_club(self):
        """Test getting items by club."""
        # Make items public
        self.jersey.is_draft = False
        self.jersey.is_private = False
        self.jersey.save()

        self.other_jersey.is_draft = False
        self.other_jersey.is_private = False
        self.other_jersey.save()

        items = self.repository.get_items_by_club(self.club.id)

        expected_count = 2
        assert items.count() == expected_count

    def test_get_items_by_season(self):
        """Test getting items by season."""
        # Make items public
        self.jersey.is_draft = False
        self.jersey.is_private = False
        self.jersey.save()

        self.other_jersey.is_draft = False
        self.other_jersey.is_private = False
        self.other_jersey.save()

        items = self.repository.get_items_by_season(self.season.id)

        expected_count = 2
        assert items.count() == expected_count

    def test_get_items_by_brand(self):
        """Test getting items by brand."""
        # Make items public
        self.jersey.is_draft = False
        self.jersey.is_private = False
        self.jersey.save()

        self.other_jersey.is_draft = False
        self.other_jersey.is_private = False
        self.other_jersey.save()

        items = self.repository.get_items_by_brand(self.brand.id)

        expected_count = 2
        assert items.count() == expected_count

    def test_get_recent_items(self):
        """Test getting recent items."""
        # Make items public
        self.jersey.is_draft = False
        self.jersey.is_private = False
        self.jersey.save()

        self.other_jersey.is_draft = False
        self.other_jersey.is_private = False
        self.other_jersey.save()

        items = self.repository.get_recent_items(limit=5)

        expected_count = 2
        assert items.count() == expected_count

    def test_get_user_item_count(self):
        """Test getting user item count."""
        count = self.repository.get_user_item_count(self.user)

        assert count == 1

    def test_get_user_item_count_by_type(self):
        """Test getting user item count by type."""
        counts = self.repository.get_user_item_count_by_type(self.user)

        assert counts["jersey"] == 1
        assert counts["shorts"] == 0
        assert counts["outerwear"] == 0
        assert counts["tracksuit"] == 0
        assert counts["pants"] == 0
        assert counts["other"] == 0

    def test_get_user_items_excludes_other_users(self):
        """Test that get_user_items only returns items for the specified user."""
        items = self.repository.get_user_items(self.user)

        # Should only get the user's items, not other user's items
        assert items.count() == 1
        assert items.first().user == self.user

        # Verify other user's items are not included
        other_items = self.repository.get_user_items(self.other_user)
        assert other_items.count() == 1
        assert other_items.first().user == self.other_user
