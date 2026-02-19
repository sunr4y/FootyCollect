"""Tests for collection factories."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from footycollect.collection.factories import (
    BaseItemFactory,
    BrandFactory,
    ClubFactory,
    CompetitionFactory,
    JerseyFactory,
    PhotoFactory,
    SeasonFactory,
    SizeFactory,
    UserFactory,
    UserWithJerseysFactory,
)

User = get_user_model()

USER_WITH_JERSEYS_FACTORY_JERSEY_COUNT = 3


class TestUserFactory(TestCase):
    """Test UserFactory."""

    def test_user_creation(self):
        """Test user creation with factory."""
        user = UserFactory()

        assert isinstance(user, User)
        assert user.username.startswith("testuser")
        assert user.email == f"{user.username}@example.com"
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser

    def test_user_sequence(self):
        """Test user sequence generation."""
        user1 = UserFactory()
        user2 = UserFactory()

        assert user1.username != user2.username
        assert user1.username.startswith("testuser")
        assert user2.username.startswith("testuser")


class TestBrandFactory(TestCase):
    """Test BrandFactory."""

    def test_brand_creation(self):
        """Test brand creation with factory."""
        brand = BrandFactory()

        assert brand.name is not None
        assert brand.slug is not None
        assert brand.name.startswith("Brand")
        assert brand.slug.startswith("brand-")

    def test_brand_sequence(self):
        """Test brand sequence generation."""
        brand1 = BrandFactory()
        brand2 = BrandFactory()

        assert brand1.name != brand2.name
        assert brand1.slug != brand2.slug


class TestClubFactory(TestCase):
    """Test ClubFactory."""

    def test_club_creation(self):
        """Test club creation with factory."""
        club = ClubFactory()

        assert club.name is not None
        assert club.slug is not None
        assert club.name.startswith("Club")
        assert club.slug.startswith("club-")


class TestCompetitionFactory(TestCase):
    """Test CompetitionFactory."""

    def test_competition_creation(self):
        """Test competition creation with factory."""
        competition = CompetitionFactory()

        assert competition.name is not None
        assert competition.slug is not None
        assert competition.name.startswith("Competition")
        assert competition.slug.startswith("competition-")


class TestSeasonFactory(TestCase):
    """Test SeasonFactory."""

    def test_season_creation(self):
        """Test season creation with factory."""
        season = SeasonFactory()

        assert season.year is not None
        assert season.first_year is not None
        assert season.second_year is not None


class TestSizeFactory(TestCase):
    """Test SizeFactory."""

    def test_size_creation(self):
        """Test size creation with factory."""
        size = SizeFactory()

        assert size.name is not None
        assert size.category in ["tops", "bottoms", "other"]


class TestBaseItemFactory(TestCase):
    """Test BaseItemFactory."""

    def test_base_item_creation(self):
        """Test base item creation with factory."""
        user = UserFactory()
        brand = BrandFactory()
        club = ClubFactory()
        season = SeasonFactory()

        base_item = BaseItemFactory(
            user=user,
            brand=brand,
            club=club,
            season=season,
        )

        assert base_item.user == user
        assert base_item.brand == brand
        assert base_item.club == club
        assert base_item.season == season
        assert base_item.name is not None


class TestJerseyFactory(TestCase):
    """Test JerseyFactory."""

    def test_jersey_creation(self):
        """Test jersey creation with factory."""
        from footycollect.collection.models import Color

        # Create a color first
        color = Color.objects.create(name="RED", hex_value="#FF0000")

        user = UserFactory()
        brand = BrandFactory()
        club = ClubFactory()
        season = SeasonFactory()

        base_item = BaseItemFactory(
            user=user,
            brand=brand,
            club=club,
            season=season,
            main_color=color,
            design="HOME",
        )

        jersey = JerseyFactory(base_item=base_item)

        assert jersey.base_item == base_item
        assert jersey.base_item.main_color == color
        assert jersey.base_item.design == "HOME"


class TestUserWithJerseysFactory(TestCase):
    """Test UserWithJerseysFactory."""

    def test_user_with_jerseys_creates_three_jerseys(self):
        """Test that UserWithJerseysFactory creates a user with 3 jerseys."""
        from footycollect.collection.models import Jersey

        user = UserWithJerseysFactory()
        jerseys = Jersey.objects.filter(base_item__user=user)
        assert jerseys.count() == USER_WITH_JERSEYS_FACTORY_JERSEY_COUNT


class TestPhotoFactory(TestCase):
    """Test PhotoFactory."""

    @patch("footycollect.collection.models.optimize_image")
    def test_photo_creation(self, mock_optimize):
        """Test photo creation with factory."""
        mock_optimize.return_value = None
        user = UserFactory()
        brand = BrandFactory()
        club = ClubFactory()
        season = SeasonFactory()

        base_item = BaseItemFactory(
            user=user,
            brand=brand,
            club=club,
            season=season,
        )

        jersey = JerseyFactory(base_item=base_item)

        photo = PhotoFactory(content_object=jersey)

        assert photo.content_object == jersey
        assert photo.image is not None
        assert photo.order == 0
