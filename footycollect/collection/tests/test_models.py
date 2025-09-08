"""
Tests for collection models.
"""

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
        assert str(size) == "Tops - M"

    def test_size_str_representation(self):
        """Test size string representation."""
        from footycollect.collection.models import Size

        size = Size.objects.create(name="L", category="bottoms")
        assert str(size) == "Bottoms - L"

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

    def test_photo_creation(self, user, jersey):
        """Test creating a photo."""
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
        assert str(photo) == "Photo 1 of Nike FC Barcelona Item"

    def test_photo_str_representation(self, user, jersey):
        """Test photo string representation."""
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
        assert str(photo) == "Photo 2 of Nike FC Barcelona Item"

    def test_photo_default_order(self, user, jersey):
        """Test photo default order."""
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

    def test_photo_get_image_url(self, user, jersey):
        """Test photo get_image_url method."""
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
        from footycollect.collection.models import Jersey

        jersey = Jersey.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
            condition=10,
            detailed_condition="EXCELLENT",
            description="Test jersey description",
            is_replica=False,
            is_private=False,
            is_draft=False,
            is_fan_version=True,
            is_signed=False,
            has_nameset=False,
            player_name="Messi",
            number=10,
            is_short_sleeve=True,
        )

        assert jersey.user == user
        assert jersey.brand == brand
        assert jersey.club == club
        assert jersey.season == season
        assert jersey.size == size
        assert jersey.condition == CONDITION_EXCELLENT
        assert jersey.detailed_condition == "EXCELLENT"
        assert jersey.description == "Test jersey description"
        assert jersey.is_replica is False
        assert jersey.is_private is False
        assert jersey.is_draft is False
        assert jersey.is_fan_version is True
        assert jersey.is_signed is False
        assert jersey.has_nameset is False
        assert jersey.player_name == "Messi"
        assert jersey.number == PLAYER_NUMBER
        assert jersey.is_short_sleeve is True
        assert str(jersey) == "Nike FC Barcelona Item"

    def test_jersey_str_representation(self, user, brand, club, season, size):
        """Test jersey string representation."""
        from footycollect.collection.models import Jersey

        jersey = Jersey.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
            condition=10,
        )
        assert str(jersey) == "Nike FC Barcelona Item"

    def test_jersey_required_fields(self, user, brand, club, season, size):
        """Test jersey required fields."""
        from django.db import transaction

        from footycollect.collection.models import Jersey

        # Test that user is required
        with pytest.raises(IntegrityError), transaction.atomic():
            Jersey.objects.create(
                brand=brand,
                club=club,
                season=season,
                size=size,
                condition=10,
            )

        # Test that brand is required
        with pytest.raises(IntegrityError), transaction.atomic():
            Jersey.objects.create(
                user=user,
                club=club,
                season=season,
                size=size,
                condition=10,
            )

        # Test that size is required
        with pytest.raises(IntegrityError), transaction.atomic():
            Jersey.objects.create(
                user=user,
                brand=brand,
                club=club,
                season=season,
                condition=10,
            )

    def test_jersey_condition_validation(self, user, brand, club, season, size):
        """Test jersey condition validation."""
        from footycollect.collection.models import Jersey

        # Test valid condition (1-10)
        jersey = Jersey.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
            condition=5,
        )
        assert jersey.condition == CONDITION_VERY_POOR

        # Test condition validation
        jersey.condition = 15  # Invalid
        with pytest.raises(ValidationError):
            jersey.full_clean()

        jersey.condition = 0  # Invalid
        with pytest.raises(ValidationError):
            jersey.full_clean()

    def test_jersey_default_values(self, user, brand, club, season, size):
        """Test jersey default values."""
        from footycollect.collection.models import Jersey

        jersey = Jersey.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
            condition=10,
        )

        assert jersey.condition == CONDITION_EXCELLENT  # Default
        assert jersey.is_replica is False  # Default
        assert jersey.is_private is False  # Default
        assert jersey.is_draft is True  # Default
        assert jersey.is_fan_version is True  # Default
        assert jersey.is_signed is False  # Default
        assert jersey.has_nameset is False  # Default
        assert jersey.is_short_sleeve is True  # Default


@pytest.mark.django_db
class TestShortsModel:
    """Test Shorts model."""

    def test_shorts_creation(self, user, brand, club, season, size):
        """Test creating shorts."""
        from footycollect.collection.models import Shorts

        shorts = Shorts.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
            condition=8,
            number=10,
            is_fan_version=True,
        )

        assert shorts.user == user
        assert shorts.brand == brand
        assert shorts.club == club
        assert shorts.season == season
        assert shorts.size == size
        assert shorts.condition == CONDITION_GOOD
        assert shorts.number == PLAYER_NUMBER
        assert shorts.is_fan_version is True
        assert str(shorts) == "Nike FC Barcelona Item"

    def test_shorts_default_values(self, user, brand, club, season, size):
        """Test shorts default values."""
        from footycollect.collection.models import Shorts

        shorts = Shorts.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
            condition=10,
        )

        assert shorts.is_fan_version is True  # Default


@pytest.mark.django_db
class TestOuterwearModel:
    """Test Outerwear model."""

    def test_outerwear_creation(self, user, brand, club, season, size):
        """Test creating outerwear."""
        from footycollect.collection.models import Outerwear

        outerwear = Outerwear.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
            condition=9,
            type="hoodie",
        )

        assert outerwear.user == user
        assert outerwear.brand == brand
        assert outerwear.club == club
        assert outerwear.season == season
        assert outerwear.size == size
        assert outerwear.condition == 9  # noqa: PLR2004
        assert outerwear.type == "hoodie"
        assert str(outerwear) == "Nike FC Barcelona Item"

    def test_outerwear_type_choices(self, user, brand, club, season, size):
        """Test outerwear type choices."""
        from footycollect.collection.models import Outerwear

        # Test valid types
        for outerwear_type in ["hoodie", "jacket", "windbreaker", "crewneck"]:
            outerwear = Outerwear.objects.create(
                user=user,
                brand=brand,
                club=club,
                season=season,
                size=size,
                condition=10,
                type=outerwear_type,
            )
            assert outerwear.type == outerwear_type


@pytest.mark.django_db
class TestTracksuitModel:
    """Test Tracksuit model."""

    def test_tracksuit_creation(self, user, brand, club, season, size):
        """Test creating tracksuit."""
        from footycollect.collection.models import Tracksuit

        tracksuit = Tracksuit.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
            condition=7,
        )

        assert tracksuit.user == user
        assert tracksuit.brand == brand
        assert tracksuit.club == club
        assert tracksuit.season == season
        assert tracksuit.size == size
        assert tracksuit.condition == CONDITION_FAIR
        assert str(tracksuit) == "Nike FC Barcelona Item"


@pytest.mark.django_db
class TestPantsModel:
    """Test Pants model."""

    def test_pants_creation(self, user, brand, club, season, size):
        """Test creating pants."""
        from footycollect.collection.models import Pants

        pants = Pants.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
            condition=6,
        )

        assert pants.user == user
        assert pants.brand == brand
        assert pants.club == club
        assert pants.season == season
        assert pants.size == size
        assert pants.condition == CONDITION_POOR
        assert str(pants) == "Nike FC Barcelona Item"


@pytest.mark.django_db
class TestOtherItemModel:
    """Test OtherItem model."""

    def test_other_item_creation(self, user, brand, club, season):
        """Test creating other item."""
        from footycollect.collection.models import OtherItem

        other_item = OtherItem.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            condition=5,
            type="pin",
        )

        assert other_item.user == user
        assert other_item.brand == brand
        assert other_item.club == club
        assert other_item.season == season
        assert other_item.condition == CONDITION_VERY_POOR
        assert other_item.type == "pin"
        assert str(other_item) == "Nike FC Barcelona Item"

    def test_other_item_type_choices(self, user, brand, club, season):
        """Test other item type choices."""
        from footycollect.collection.models import OtherItem

        # Test valid types
        for item_type in ["pin", "hat", "cap", "socks", "other"]:
            other_item = OtherItem.objects.create(
                user=user,
                brand=brand,
                club=club,
                season=season,
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
        public_jersey = Jersey.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
            condition=10,
            is_private=False,
            is_draft=False,
        )

        # Create private jersey
        private_jersey = Jersey.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
            condition=10,
            is_private=True,
            is_draft=False,
        )

        # Create draft jersey
        draft_jersey = Jersey.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
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
        private_jersey = Jersey.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
            condition=10,
            is_private=True,
        )

        # Create public jersey
        public_jersey = Jersey.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
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
        draft_jersey = Jersey.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
            condition=10,
            is_draft=True,
        )

        # Create published jersey
        published_jersey = Jersey.objects.create(
            user=user,
            brand=brand,
            club=club,
            season=season,
            size=size,
            condition=10,
            is_draft=False,
        )

        # Test drafts manager
        draft_jerseys = Jersey.objects.drafts()
        assert draft_jersey in draft_jerseys
        assert published_jersey not in draft_jerseys
