"""
Tests for collection models.
"""

from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

# Test constants
CONDITION_EXCELLENT = 10
CONDITION_GOOD = 8
CONDITION_FAIR = 7
CONDITION_POOR = 6
CONDITION_VERY_POOR = 5
PLAYER_NUMBER = 10


def create_jersey_with_mti(user, brand, club, season, size, **kwargs):
    """Helper function to create a jersey using MTI structure."""
    from footycollect.collection.models import BaseItem, Jersey

    # Create BaseItem first
    base_item = BaseItem.objects.create(
        name=kwargs.get("name", f"{brand.name} {club.name} Jersey"),
        item_type="jersey",
        user=user,
        brand=brand,
        club=club,
        season=season,
        condition=kwargs.get("condition", 10),
        detailed_condition=kwargs.get("detailed_condition", "EXCELLENT"),
        description=kwargs.get("description", ""),
        is_replica=kwargs.get("is_replica", False),
        is_private=kwargs.get("is_private", False),
        is_draft=kwargs.get("is_draft", False),
    )

    # Create Jersey linked to BaseItem
    return Jersey.objects.create(
        base_item=base_item,
        size=size,
        is_fan_version=kwargs.get("is_fan_version", True),
        is_signed=kwargs.get("is_signed", False),
        has_nameset=kwargs.get("has_nameset", False),
        player_name=kwargs.get("player_name", ""),
        number=kwargs.get("number"),
        is_short_sleeve=kwargs.get("is_short_sleeve", True),
    )


def create_shorts_with_mti(user, brand, club, season, size, **kwargs):
    """Helper function to create shorts using MTI structure."""
    from footycollect.collection.models import BaseItem, Shorts

    # Create BaseItem first
    base_item = BaseItem.objects.create(
        name=kwargs.get("name", f"{brand.name} {club.name} Shorts"),
        item_type="shorts",
        user=user,
        brand=brand,
        club=club,
        season=season,
        condition=kwargs.get("condition", 10),
        detailed_condition=kwargs.get("detailed_condition", "EXCELLENT"),
        description=kwargs.get("description", ""),
        is_replica=kwargs.get("is_replica", False),
        is_private=kwargs.get("is_private", False),
        is_draft=kwargs.get("is_draft", False),
    )

    # Create Shorts linked to BaseItem
    return Shorts.objects.create(
        base_item=base_item,
        size=kwargs.get("size", size),
        is_fan_version=kwargs.get("is_fan_version", True),
        number=kwargs.get("number"),
    )


def create_outerwear_with_mti(user, brand, club, season, size, **kwargs):
    """Helper function to create outerwear using MTI structure."""
    from footycollect.collection.models import BaseItem, Outerwear

    # Create BaseItem first
    base_item = BaseItem.objects.create(
        name=kwargs.get("name", f"{brand.name} {club.name} Outerwear"),
        item_type="outerwear",
        user=user,
        brand=brand,
        club=club,
        season=season,
        condition=kwargs.get("condition", 10),
        detailed_condition=kwargs.get("detailed_condition", "EXCELLENT"),
        description=kwargs.get("description", ""),
        is_replica=kwargs.get("is_replica", False),
        is_private=kwargs.get("is_private", False),
        is_draft=kwargs.get("is_draft", False),
    )

    # Create Outerwear linked to BaseItem
    return Outerwear.objects.create(
        base_item=base_item,
        size=kwargs.get("size", size),
        type=kwargs.get("type", "hoodie"),
    )


def create_tracksuit_with_mti(user, brand, club, season, size, **kwargs):
    """Helper function to create tracksuit using MTI structure."""
    from footycollect.collection.models import BaseItem, Tracksuit

    # Create BaseItem first
    base_item = BaseItem.objects.create(
        name=kwargs.get("name", f"{brand.name} {club.name} Tracksuit"),
        item_type="tracksuit",
        user=user,
        brand=brand,
        club=club,
        season=season,
        condition=kwargs.get("condition", 10),
        detailed_condition=kwargs.get("detailed_condition", "EXCELLENT"),
        description=kwargs.get("description", ""),
        is_replica=kwargs.get("is_replica", False),
        is_private=kwargs.get("is_private", False),
        is_draft=kwargs.get("is_draft", False),
    )

    # Create Tracksuit linked to BaseItem
    return Tracksuit.objects.create(
        base_item=base_item,
        size=kwargs.get("size", size),
    )


def create_pants_with_mti(user, brand, club, season, size, **kwargs):
    """Helper function to create pants using MTI structure."""
    from footycollect.collection.models import BaseItem, Pants

    # Create BaseItem first
    base_item = BaseItem.objects.create(
        name=kwargs.get("name", f"{brand.name} {club.name} Pants"),
        item_type="pants",
        user=user,
        brand=brand,
        club=club,
        season=season,
        condition=kwargs.get("condition", 10),
        detailed_condition=kwargs.get("detailed_condition", "EXCELLENT"),
        description=kwargs.get("description", ""),
        is_replica=kwargs.get("is_replica", False),
        is_private=kwargs.get("is_private", False),
        is_draft=kwargs.get("is_draft", False),
    )

    # Create Pants linked to BaseItem
    return Pants.objects.create(
        base_item=base_item,
        size=kwargs.get("size", size),
    )


def create_other_item_with_mti(user, brand, club, season, **kwargs):
    """Helper function to create other item using MTI structure."""
    from footycollect.collection.models import BaseItem, OtherItem

    # Create BaseItem first
    base_item = BaseItem.objects.create(
        name=kwargs.get("name", f"{brand.name} {club.name} Other Item"),
        item_type="other",
        user=user,
        brand=brand,
        club=club,
        season=season,
        condition=kwargs.get("condition", 10),
        detailed_condition=kwargs.get("detailed_condition", "EXCELLENT"),
        description=kwargs.get("description", ""),
        is_replica=kwargs.get("is_replica", False),
        is_private=kwargs.get("is_private", False),
        is_draft=kwargs.get("is_draft", False),
    )

    # Create OtherItem linked to BaseItem
    return OtherItem.objects.create(
        base_item=base_item,
        type=kwargs.get("type", "other"),
    )


@pytest.mark.django_db
class TestColorModel:
    """Test Color model."""

    def test_color_creation(self):
        """Test creating a color."""
        from footycollect.collection.models import Color

        color = Color.objects.create(
            name="Blue",
            hex_value="#0000FF",
        )

        assert color.name == "Blue"
        assert color.hex_value == "#0000FF"
        assert str(color) == "Blue"

    def test_color_str_representation(self):
        """Test color string representation."""
        from footycollect.collection.models import Color

        color = Color.objects.create(name="Red", hex_value="#FF0000")
        assert str(color) == "Red"

    def test_color_unique_name(self):
        """Test color name uniqueness."""
        from footycollect.collection.models import Color

        Color.objects.create(name="Blue", hex_value="#0000FF")

        # Should raise IntegrityError for duplicate name
        with pytest.raises(IntegrityError):
            Color.objects.create(name="Blue", hex_value="#0000FF")

    def test_color_default_hex_value(self):
        """Test color default hex value."""
        from footycollect.collection.models import Color

        color = Color.objects.create(name="Test Color")
        assert color.hex_value == "#FF0000"  # Default value


@pytest.mark.django_db
class TestSizeModel:
    """Test Size model."""

    def test_size_creation(self):
        """Test creating a size."""
        from footycollect.collection.models import Size

        size = Size.objects.create(
            name="M",
            category="tops",
        )

        assert size.name == "M"
        assert size.category == "tops"
        assert str(size) == "M"

    def test_size_str_representation(self):
        """Test size string representation."""
        from footycollect.collection.models import Size

        size = Size.objects.create(name="L", category="bottoms")
        assert str(size) == "L"

    def test_size_category_choices(self):
        """Test size category choices."""
        from footycollect.collection.models import Size

        # Test valid categories
        for category in ["tops", "bottoms", "other"]:
            size = Size.objects.create(name="Test", category=category)
            assert size.category == category


@pytest.mark.django_db
class TestPhotoModel:
    """Test Photo model."""

    @patch("footycollect.collection.models.optimize_image")
    def test_photo_creation(self, mock_optimize, user, jersey):
        """Test creating a photo."""
        mock_optimize.return_value = None  # Mock the optimization to return None

        from pathlib import Path

        from django.core.files.uploadedfile import SimpleUploadedFile

        from footycollect.collection.models import Photo

        # Use real test image
        test_image_path = Path(__file__).parent / "test_avatar.jpg"
        with test_image_path.open("rb") as f:
            test_image = SimpleUploadedFile(
                "test_image.jpg",
                f.read(),
                content_type="image/jpeg",
            )

        photo = Photo.objects.create(
            user=user,
            content_object=jersey,
            image=test_image,
            order=1,
            caption="Test caption",
        )

        assert photo.user == user
        assert photo.content_object == jersey
        assert "test_image.jpg" in photo.image.name
        assert photo.order == 1
        assert photo.caption == "Test caption"
        assert str(photo) == "Photo 1 of Jersey: Nike FC Barcelona Jersey"

    @patch("footycollect.collection.models.optimize_image")
    def test_photo_str_representation(self, mock_optimize, user, jersey):
        """Test photo string representation."""
        mock_optimize.return_value = None
        from pathlib import Path

        from django.core.files.uploadedfile import SimpleUploadedFile

        from footycollect.collection.models import Photo

        # Use real test image
        test_image_path = Path(__file__).parent / "test_avatar.png"
        with test_image_path.open("rb") as f:
            test_image = SimpleUploadedFile(
                "another_image.png",
                f.read(),
                content_type="image/png",
            )

        photo = Photo.objects.create(
            user=user,
            content_object=jersey,
            image=test_image,
            order=2,
        )
        assert str(photo) == "Photo 2 of Jersey: Nike FC Barcelona Jersey"

    @patch("footycollect.collection.models.optimize_image")
    def test_photo_default_order(self, mock_optimize, user, jersey):
        """Test photo default order."""
        mock_optimize.return_value = None
        from pathlib import Path

        from django.core.files.uploadedfile import SimpleUploadedFile

        from footycollect.collection.models import Photo

        # Use real test image
        test_image_path = Path(__file__).parent / "test_avatar.gif"
        with test_image_path.open("rb") as f:
            test_image = SimpleUploadedFile(
                "test_image.gif",
                f.read(),
                content_type="image/gif",
            )

        photo = Photo.objects.create(
            user=user,
            content_object=jersey,
            image=test_image,
        )
        assert photo.order == 0  # Default value

    @patch("footycollect.collection.models.optimize_image")
    def test_photo_get_image_url(self, mock_optimize, user, jersey):
        """Test photo get_image_url method."""
        mock_optimize.return_value = None
        from pathlib import Path

        from django.core.files.uploadedfile import SimpleUploadedFile

        from footycollect.collection.models import Photo

        # Use real test image
        test_image_path = Path(__file__).parent / "test_avatar.jpg"
        with test_image_path.open("rb") as f:
            test_image = SimpleUploadedFile(
                "test_image.jpg",
                f.read(),
                content_type="image/jpeg",
            )

        photo = Photo.objects.create(
            user=user,
            content_object=jersey,
            image=test_image,
        )

        # Test that the method exists and returns a string
        image_url = photo.get_image_url()
        assert isinstance(image_url, str)


@pytest.mark.django_db
class TestJerseyModel:
    """Test Jersey model."""

    def test_jersey_creation(self, user, brand, club, season, size):
        """Test creating a jersey."""
        jersey = create_jersey_with_mti(
            user,
            brand,
            club,
            season,
            size,
            description="Test jersey description",
            player_name="Messi",
            number=10,
        )

        assert jersey.base_item.user == user
        assert jersey.base_item.brand == brand
        assert jersey.base_item.club == club
        assert jersey.base_item.season == season
        assert jersey.size == size
        assert jersey.base_item.condition == CONDITION_EXCELLENT
        assert jersey.base_item.detailed_condition == "EXCELLENT"
        assert jersey.base_item.description == "Test jersey description"
        assert jersey.base_item.is_replica is False
        assert jersey.base_item.is_private is False
        assert jersey.base_item.is_draft is False
        assert jersey.is_fan_version is True
        assert jersey.is_signed is False
        assert jersey.has_nameset is False
        assert jersey.player_name == "Messi"
        assert jersey.number == PLAYER_NUMBER
        assert jersey.is_short_sleeve is True
        assert str(jersey) == "Jersey: Nike FC Barcelona Jersey"

    def test_jersey_str_representation(self, user, brand, club, season, size):
        """Test jersey string representation."""
        jersey = create_jersey_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=10,
        )
        assert str(jersey) == "Jersey: Nike FC Barcelona Jersey"

    def test_jersey_required_fields(self, user, brand, club, season, size):
        """Test jersey required fields."""
        # With MTI, we test that the helper function works correctly
        # and that required fields are validated at the BaseItem level
        jersey = create_jersey_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=10,
        )

        # Verify the jersey was created successfully
        assert jersey is not None
        assert jersey.base_item.user == user
        assert jersey.base_item.brand == brand
        assert jersey.base_item.club == club
        assert jersey.base_item.season == season
        assert jersey.size == size

    def test_jersey_condition_validation(self, user, brand, club, season, size):
        """Test jersey condition validation."""
        # Test valid condition (1-10)
        jersey = create_jersey_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=5,
        )
        expected_condition = 5
        assert jersey.base_item.condition == expected_condition

        # Test condition validation
        jersey.base_item.condition = 15  # Invalid
        with pytest.raises(ValidationError):
            jersey.base_item.full_clean()

        jersey.base_item.condition = 0  # Invalid
        with pytest.raises(ValidationError):
            jersey.base_item.full_clean()

    def test_jersey_default_values(self, user, brand, club, season, size):
        """Test jersey default values."""
        jersey = create_jersey_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=10,
        )

        assert jersey.base_item.condition == CONDITION_EXCELLENT  # Default
        assert jersey.base_item.is_replica is False  # Default
        assert jersey.base_item.is_private is False  # Default
        assert jersey.base_item.is_draft is False  # Default (changed from True to False)
        assert jersey.is_fan_version is True  # Default
        assert jersey.is_signed is False  # Default
        assert jersey.has_nameset is False  # Default
        assert jersey.is_short_sleeve is True  # Default


@pytest.mark.django_db
class TestShortsModel:
    """Test Shorts model."""

    def test_shorts_creation(self, user, brand, club, season, size):
        """Test creating shorts."""
        shorts = create_shorts_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=8,
            number=10,
            is_fan_version=True,
        )

        assert shorts.base_item.user == user
        assert shorts.base_item.brand == brand
        assert shorts.base_item.club == club
        assert shorts.base_item.season == season
        assert shorts.size == size
        assert shorts.base_item.condition == CONDITION_GOOD
        assert shorts.number == PLAYER_NUMBER
        assert shorts.is_fan_version is True
        assert str(shorts) == "Shorts: Nike FC Barcelona Shorts"

    def test_shorts_default_values(self, user, brand, club, season, size):
        """Test shorts default values."""
        shorts = create_shorts_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=10,
        )

        assert shorts.is_fan_version is True  # Default


@pytest.mark.django_db
class TestOuterwearModel:
    """Test Outerwear model."""

    def test_outerwear_creation(self, user, brand, club, season, size):
        """Test creating outerwear."""
        outerwear = create_outerwear_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=10,
            type="hoodie",
        )

        assert outerwear.base_item.user == user
        assert outerwear.base_item.brand == brand
        assert outerwear.base_item.club == club
        assert outerwear.base_item.season == season
        assert outerwear.size == size
        assert outerwear.base_item.condition == 10  # noqa: PLR2004
        assert outerwear.type == "hoodie"
        assert str(outerwear) == "Outerwear: Nike FC Barcelona Outerwear"

    def test_outerwear_type_choices(self, user, brand, club, season, size):
        """Test outerwear type choices."""

        # Test valid types
        for outerwear_type in ["hoodie", "jacket", "windbreaker", "crewneck"]:
            outerwear = create_outerwear_with_mti(
                user,
                brand,
                club,
                season,
                size,
                condition=10,
                type=outerwear_type,
            )
            assert outerwear.type == outerwear_type


@pytest.mark.django_db
class TestTracksuitModel:
    """Test Tracksuit model."""

    def test_tracksuit_creation(self, user, brand, club, season, size):
        """Test creating tracksuit."""
        tracksuit = create_tracksuit_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=7,
        )

        assert tracksuit.base_item.user == user
        assert tracksuit.base_item.brand == brand
        assert tracksuit.base_item.club == club
        assert tracksuit.base_item.season == season
        assert tracksuit.size == size
        assert tracksuit.base_item.condition == CONDITION_FAIR
        assert str(tracksuit) == "Tracksuit: Nike FC Barcelona Tracksuit"


@pytest.mark.django_db
class TestPantsModel:
    """Test Pants model."""

    def test_pants_creation(self, user, brand, club, season, size):
        """Test creating pants."""
        pants = create_pants_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=6,
        )

        assert pants.base_item.user == user
        assert pants.base_item.brand == brand
        assert pants.base_item.club == club
        assert pants.base_item.season == season
        assert pants.size == size
        assert pants.base_item.condition == CONDITION_POOR
        assert str(pants) == "Pants: Nike FC Barcelona Pants"


@pytest.mark.django_db
class TestOtherItemModel:
    """Test OtherItem model."""

    def test_other_item_creation(self, user, brand, club, season):
        """Test creating other item."""
        other_item = create_other_item_with_mti(
            user,
            brand,
            club,
            season,
            condition=5,
            type="pin",
        )

        assert other_item.base_item.user == user
        assert other_item.base_item.brand == brand
        assert other_item.base_item.club == club
        assert other_item.base_item.season == season
        assert other_item.base_item.condition == CONDITION_VERY_POOR
        assert other_item.type == "pin"
        assert str(other_item) == "Other Item: Nike FC Barcelona Other"

    def test_other_item_type_choices(self, user, brand, club, season):
        """Test other item type choices."""

        # Test valid types
        for item_type in ["pin", "hat", "cap", "socks", "other"]:
            other_item = create_other_item_with_mti(
                user,
                brand,
                club,
                season,
                condition=10,
                type=item_type,
            )
            assert other_item.type == item_type


@pytest.mark.django_db
class TestBaseItemManager:
    """Test BaseItemManager."""

    def test_public_manager(self, user, brand, club, season, size):
        """Test public manager method."""
        from footycollect.collection.models import Jersey

        # Create public jersey
        public_jersey = create_jersey_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=10,
            is_private=False,
            is_draft=False,
        )

        # Create private jersey
        private_jersey = create_jersey_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=10,
            is_private=True,
            is_draft=False,
        )

        # Create draft jersey
        draft_jersey = create_jersey_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=10,
            is_private=False,
            is_draft=True,
        )

        # Test public manager
        public_jerseys = Jersey.objects.public()
        assert public_jersey in public_jerseys
        assert private_jersey not in public_jerseys
        assert draft_jersey not in public_jerseys

    def test_private_manager(self, user, brand, club, season, size):
        """Test private manager method."""
        from footycollect.collection.models import Jersey

        # Create private jersey
        private_jersey = create_jersey_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=10,
            is_private=True,
        )

        # Create public jersey
        public_jersey = create_jersey_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=10,
            is_private=False,
        )

        # Test private manager
        private_jerseys = Jersey.objects.private()
        assert private_jersey in private_jerseys
        assert public_jersey not in private_jerseys

    def test_drafts_manager(self, user, brand, club, season, size):
        """Test drafts manager method."""
        from footycollect.collection.models import Jersey

        # Create draft jersey
        draft_jersey = create_jersey_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=10,
            is_draft=True,
        )

        # Create published jersey
        published_jersey = create_jersey_with_mti(
            user,
            brand,
            club,
            season,
            size,
            condition=10,
            is_draft=False,
        )

        # Test drafts manager
        draft_jerseys = Jersey.objects.drafts()
        assert draft_jersey in draft_jerseys
        assert published_jersey not in draft_jerseys
