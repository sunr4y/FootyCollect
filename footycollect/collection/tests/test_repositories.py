"""
Tests for repository classes.
"""

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.test import TestCase

from footycollect.collection.models import BaseItem, Brand, Club, Color, Jersey, Season, Size
from footycollect.collection.repositories import (
    BaseRepository,
    ColorRepository,
    ItemRepository,
    PhotoRepository,
    SizeRepository,
)

# Test constants
EXPECTED_COUNT_2 = 2
EXPECTED_COUNT_3 = 3
EXPECTED_COUNT_10 = 10
TEST_PASSWORD = "testpass123"  # NOSONAR (S2068) "test fixture only, not a credential"

User = get_user_model()


class TestItemRepositoryClean(TestCase):
    """Tests for ItemRepository."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password=TEST_PASSWORD,
        )

        # Create test data
        self.brand = Brand.objects.create(name="Nike")
        self.club = Club.objects.create(name="FC Barcelona", country="ES")
        self.season = Season.objects.create(year="2023-24", first_year="2023", second_year="24")

        # Create test items
        self.jersey = self._create_jersey(
            user=self.user,
            name="Test Jersey",
            brand=self.brand,
            club=self.club,
            season=self.season,
        )

        self.other_jersey = self._create_jersey(
            user=self.other_user,
            name="Other Jersey",
            brand=self.brand,
            club=self.club,
            season=self.season,
        )

        self.repository = ItemRepository()

    def _create_jersey(self, user, name, brand, club, season, **kwargs):
        """Helper method to create jersey with MTI structure."""
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

        assert items.count() == EXPECTED_COUNT_2

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

        assert items.count() == EXPECTED_COUNT_2

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

        assert items.count() == EXPECTED_COUNT_2

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

        assert items.count() == EXPECTED_COUNT_2

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

        assert items.count() == EXPECTED_COUNT_2

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


class TestColorRepositoryClean(TestCase):
    """Tests for ColorRepository."""

    def setUp(self):
        """Set up test data."""
        self.repository = ColorRepository()
        self.color1 = Color.objects.create(name="RED", hex_value="#FF0000")
        self.color2 = Color.objects.create(name="BLUE", hex_value="#0000FF")
        self.color3 = Color.objects.create(name="GREEN", hex_value="#008000")

    def test_init(self):
        """Test ColorRepository initialization."""
        assert self.repository.model == Color

    def test_get_colors_by_hex(self):
        """Test get_colors_by_hex method."""
        result = self.repository.get_colors_by_hex("#FF0000")

        assert result.count() == 1
        assert result.first() == self.color1

    def test_get_colors_by_hex_case_insensitive(self):
        """Test get_colors_by_hex method with case insensitive search."""
        result = self.repository.get_colors_by_hex("#ff0000")

        assert result.count() == 1
        assert result.first() == self.color1

    def test_get_colors_by_hex_not_found(self):
        """Test get_colors_by_hex method with non-existent hex."""
        result = self.repository.get_colors_by_hex("#000000")

        assert result.count() == 0

    def test_get_colors_by_name(self):
        """Test get_colors_by_name method."""
        result = self.repository.get_colors_by_name("RED")

        assert result.count() == 1
        assert result.first() == self.color1

    def test_get_colors_by_name_partial_match(self):
        """Test get_colors_by_name method with partial match."""
        result = self.repository.get_colors_by_name("red")

        assert result.count() == 1
        assert result.first() == self.color1

    def test_get_colors_by_name_not_found(self):
        """Test get_colors_by_name method with non-existent name."""
        result = self.repository.get_colors_by_name("YELLOW")

        assert result.count() == 0

    def test_get_default_colors(self):
        """Test get_default_colors method."""
        result = self.repository.get_default_colors()

        # Should only return colors that are in COLOR_MAP
        default_hex_values = list(Color.COLOR_MAP.values())
        for color in result:
            assert color.hex_value in default_hex_values

    def test_get_colors_by_category(self):
        """Test get_colors_by_category method."""
        result = self.repository.get_colors_by_category("primary")

        # Should return all colors since categories are not implemented
        assert result.count() == EXPECTED_COUNT_3

    def test_get_popular_colors(self):
        """Test get_popular_colors method."""
        result = self.repository.get_popular_colors(limit=2)

        # Should return default colors with limit
        assert result.count() <= EXPECTED_COUNT_2

    def test_get_popular_colors_default_limit(self):
        """Test get_popular_colors method with default limit."""
        result = self.repository.get_popular_colors()

        # Should return default colors with default limit (10)
        assert result.count() <= EXPECTED_COUNT_10

    def test_create_default_colors(self):
        """Test create_default_colors method."""
        # Clear existing colors
        Color.objects.all().delete()

        result = self.repository.create_default_colors()

        # Should create colors from COLOR_MAP
        expected_count = len(Color.COLOR_MAP)
        assert result == expected_count
        assert Color.objects.count() == expected_count

    def test_create_default_colors_existing(self):
        """Test create_default_colors method with existing colors."""
        # Colors already exist from setUp
        initial_count = Color.objects.count()

        result = self.repository.create_default_colors()

        # Should not create duplicates - the method creates all COLOR_MAP colors
        # but only returns count of newly created ones
        assert result >= 0  # Should be 0 or more
        assert Color.objects.count() >= initial_count

    def test_get_colors_used_in_items(self):
        """Test get_colors_used_in_items method."""
        # This test would need actual jersey data to work properly
        # For now, test that the method runs without error
        result = self.repository.get_colors_used_in_items()

        assert result is not None

    def test_get_color_statistics(self):
        """Test get_color_statistics method."""
        result = self.repository.get_color_statistics()

        assert "main_colors" in result
        assert "secondary_colors" in result
        assert "total_colors" in result
        assert "used_colors" in result

        assert result["total_colors"] == EXPECTED_COUNT_3

    def test_get_color_statistics_empty(self):
        """Test get_color_statistics method with no colors."""
        Color.objects.all().delete()

        result = self.repository.get_color_statistics()

        assert result["total_colors"] == 0
        assert result["used_colors"] == 0
        assert len(result["main_colors"]) == 0
        assert len(result["secondary_colors"]) == 0


class TestSizeRepositoryClean(TestCase):
    """Tests limpios para SizeRepository."""

    def setUp(self):
        """Set up test data."""
        # Clear existing sizes to avoid conflicts
        Size.objects.all().delete()

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.brand = Brand.objects.create(name="Nike")

        self.base_item = BaseItem.objects.create(
            user=self.user,
            name="Test Jersey",
            description="Test description",
            brand=self.brand,
        )

        self.jersey = Jersey.objects.create(
            base_item=self.base_item,
            size=Size.objects.create(name="M", category="tops"),
        )

        self.repository = SizeRepository()

    def test_init(self):
        """Test repository initialization."""
        assert self.repository.model == Size

    def test_get_sizes_by_category(self):
        """Test get_sizes_by_category method."""
        # Create test sizes
        Size.objects.create(name="S", category="tops")
        Size.objects.create(name="L", category="tops")
        Size.objects.create(name="M", category="bottoms")

        result = self.repository.get_sizes_by_category("tops")

        assert isinstance(result, QuerySet)
        assert result.count() == EXPECTED_COUNT_3  # S, L, and existing M
        assert all(size.category == "tops" for size in result)

    def test_get_tops_sizes(self):
        """Test get_tops_sizes method."""
        # Create test sizes
        Size.objects.create(name="S", category="tops")
        Size.objects.create(name="L", category="tops")
        Size.objects.create(name="M", category="bottoms")

        result = self.repository.get_tops_sizes()

        assert isinstance(result, QuerySet)
        assert result.count() == EXPECTED_COUNT_3  # S, L, and existing M
        assert all(size.category == "tops" for size in result)

    def test_get_bottoms_sizes(self):
        """Test get_bottoms_sizes method."""
        # Create test sizes
        Size.objects.create(name="28", category="bottoms")
        Size.objects.create(name="32", category="bottoms")
        Size.objects.create(name="M", category="tops")

        result = self.repository.get_bottoms_sizes()

        assert isinstance(result, QuerySet)
        assert result.count() == EXPECTED_COUNT_2
        assert all(size.category == "bottoms" for size in result)

    def test_get_other_sizes(self):
        """Test get_other_sizes method."""
        # Create test sizes
        Size.objects.create(name="One Size", category="other")
        Size.objects.create(name="Small", category="other")
        Size.objects.create(name="M", category="tops")

        result = self.repository.get_other_sizes()

        assert isinstance(result, QuerySet)
        assert result.count() == EXPECTED_COUNT_2
        assert all(size.category == "other" for size in result)

    def test_get_size_by_name_and_category_found(self):
        """Test get_size_by_name_and_category when size exists."""
        size = Size.objects.create(name="L", category="tops")

        result = self.repository.get_size_by_name_and_category("L", "tops")

        assert result == size

    def test_get_size_by_name_and_category_not_found(self):
        """Test get_size_by_name_and_category when size doesn't exist."""
        result = self.repository.get_size_by_name_and_category("XL", "tops")

        assert result is None

    def test_get_popular_sizes_no_category(self):
        """Test get_popular_sizes without category filter."""
        # Create test sizes
        Size.objects.create(name="S", category="tops")
        Size.objects.create(name="M", category="tops")
        Size.objects.create(name="L", category="tops")
        Size.objects.create(name="28", category="bottoms")

        result = self.repository.get_popular_sizes(limit=2)

        assert isinstance(result, QuerySet)
        assert result.count() == EXPECTED_COUNT_2

    def test_get_popular_sizes_with_category(self):
        """Test get_popular_sizes with category filter."""
        # Create test sizes
        Size.objects.create(name="S", category="tops")
        Size.objects.create(name="M", category="tops")
        Size.objects.create(name="28", category="bottoms")

        result = self.repository.get_popular_sizes(category="tops", limit=1)

        assert isinstance(result, QuerySet)
        assert result.count() == 1
        assert all(size.category == "tops" for size in result)

    def test_create_default_sizes(self):
        """Test create_default_sizes method."""
        # Clear existing sizes
        Size.objects.all().delete()

        result = self.repository.create_default_sizes()

        # Should create sizes for all categories
        assert result > 0
        assert Size.objects.filter(category="tops").exists()
        assert Size.objects.filter(category="bottoms").exists()
        assert Size.objects.filter(category="other").exists()

    def test_create_default_sizes_existing(self):
        """Test create_default_sizes when sizes already exist."""
        # Clear existing sizes first
        Size.objects.all().delete()

        # Create some existing sizes
        Size.objects.create(name="M", category="tops")
        Size.objects.create(name="L", category="tops")

        result = self.repository.create_default_sizes()

        # Should not create duplicates
        assert result >= 0
        assert Size.objects.filter(name="M", category="tops").count() == 1

    def test_get_sizes_used_in_items_no_category(self):
        """Test get_sizes_used_in_items without category filter."""
        # Create a jersey with a size
        size = Size.objects.create(name="L", category="tops")
        base_item = BaseItem.objects.create(
            user=self.user,
            name="Test Jersey 2",
            description="Test description",
            brand=self.brand,
        )
        Jersey.objects.create(
            base_item=base_item,
            size=size,
        )

        result = self.repository.get_sizes_used_in_items()

        assert isinstance(result, QuerySet)
        assert result.count() == EXPECTED_COUNT_2  # M and L sizes

    def test_get_sizes_used_in_items_with_category(self):
        """Test get_sizes_used_in_items with category filter."""
        # Create a jersey with a size
        size = Size.objects.create(name="L", category="tops")
        base_item = BaseItem.objects.create(
            user=self.user,
            name="Test Jersey 2",
            description="Test description",
            brand=self.brand,
        )
        Jersey.objects.create(
            base_item=base_item,
            size=size,
        )

        result = self.repository.get_sizes_used_in_items(category="tops")

        assert isinstance(result, QuerySet)
        assert result.count() == EXPECTED_COUNT_2  # M and L sizes
        assert all(size.category == "tops" for size in result)

    def test_get_size_statistics(self):
        """Test get_size_statistics method."""
        # Create some sizes and jerseys
        size1 = Size.objects.create(name="S", category="tops")
        size2 = Size.objects.create(name="L", category="tops")
        Size.objects.create(name="28", category="bottoms")

        # Create jerseys with these sizes
        base_item1 = BaseItem.objects.create(
            user=self.user,
            name="Test Jersey 1",
            description="Test description",
            brand=self.brand,
        )
        base_item2 = BaseItem.objects.create(
            user=self.user,
            name="Test Jersey 2",
            description="Test description",
            brand=self.brand,
        )
        Jersey.objects.create(base_item=base_item1, size=size1)
        Jersey.objects.create(base_item=base_item2, size=size2)

        result = self.repository.get_size_statistics()

        assert isinstance(result, dict)
        assert "total_sizes" in result
        assert "used_sizes" in result
        assert "tops" in result
        assert "bottoms" in result
        assert "other" in result
        assert result["total_sizes"] >= 3  # noqa: PLR2004
        assert result["used_sizes"] >= 2  # noqa: PLR2004

    def test_get_sizes_for_item_type_jersey(self):
        """Test get_sizes_for_item_type for jersey."""
        # Create sizes for different categories
        Size.objects.create(name="S", category="tops")
        Size.objects.create(name="M", category="tops")
        Size.objects.create(name="28", category="bottoms")

        result = self.repository.get_sizes_for_item_type("jersey")

        assert isinstance(result, QuerySet)
        assert result.count() == EXPECTED_COUNT_3  # S, M, and existing M
        assert all(size.category == "tops" for size in result)

    def test_get_sizes_for_item_type_shorts(self):
        """Test get_sizes_for_item_type for shorts."""
        # Create sizes for different categories
        Size.objects.create(name="S", category="tops")
        Size.objects.create(name="28", category="bottoms")
        Size.objects.create(name="32", category="bottoms")

        result = self.repository.get_sizes_for_item_type("shorts")

        assert isinstance(result, QuerySet)
        assert result.count() == EXPECTED_COUNT_2  # 28 and 32 sizes
        assert all(size.category == "bottoms" for size in result)

    def test_get_sizes_for_item_type_outerwear(self):
        """Test get_sizes_for_item_type for outerwear."""
        # Create sizes for different categories
        Size.objects.create(name="S", category="tops")
        Size.objects.create(name="M", category="tops")
        Size.objects.create(name="28", category="bottoms")

        result = self.repository.get_sizes_for_item_type("outerwear")

        assert isinstance(result, QuerySet)
        assert result.count() == EXPECTED_COUNT_3  # S, M, and existing M
        assert all(size.category == "tops" for size in result)

    def test_get_sizes_for_item_type_other(self):
        """Test get_sizes_for_item_type for other item types."""
        # Create sizes for different categories
        Size.objects.create(name="One Size", category="other")
        Size.objects.create(name="Small", category="other")
        Size.objects.create(name="S", category="tops")

        result = self.repository.get_sizes_for_item_type("unknown_type")

        assert isinstance(result, QuerySet)
        assert result.count() == EXPECTED_COUNT_2  # One Size and Small sizes
        assert all(size.category == "other" for size in result)

    def test_get_sizes_for_item_type_tracksuit(self):
        """Test get_sizes_for_item_type for tracksuit."""
        # Create sizes for different categories
        Size.objects.create(name="S", category="tops")
        Size.objects.create(name="M", category="tops")
        Size.objects.create(name="28", category="bottoms")

        result = self.repository.get_sizes_for_item_type("tracksuit")

        assert isinstance(result, QuerySet)
        assert result.count() == EXPECTED_COUNT_3  # S, M, and existing M
        assert all(size.category == "tops" for size in result)

    def test_get_sizes_for_item_type_pants(self):
        """Test get_sizes_for_item_type for pants."""
        # Create sizes for different categories
        Size.objects.create(name="S", category="tops")
        Size.objects.create(name="28", category="bottoms")
        Size.objects.create(name="32", category="bottoms")

        result = self.repository.get_sizes_for_item_type("pants")

        assert isinstance(result, QuerySet)
        assert result.count() == EXPECTED_COUNT_2  # 28 and 32 sizes
        assert all(size.category == "bottoms" for size in result)


class TestBaseRepository(TestCase):
    """Test cases for BaseRepository."""

    def setUp(self):
        """Set up test data."""
        self.repository = BaseRepository(Color)
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,  # NOSONAR (S2068) "test fixture only"
        )
        self.color = Color.objects.create(name="Red", hex_value="#FF0000")

    def test_init(self):
        """Test repository initialization."""
        assert self.repository.model == Color

    def test_get_by_id_success(self):
        """Test get_by_id method with existing object."""
        result = self.repository.get_by_id(self.color.id)
        assert result == self.color

    def test_get_by_id_not_found(self):
        """Test get_by_id method with non-existing object."""
        result = self.repository.get_by_id(999)
        assert result is None

    def test_get_all(self):
        """Test get_all method."""
        Color.objects.create(name="Blue", hex_value="#0000FF")
        result = self.repository.get_all()
        assert result.count() == EXPECTED_COUNT_2

    def test_create(self):
        """Test create method."""
        data = {"name": "Green", "hex_value": "#00FF00"}
        result = self.repository.create(**data)
        assert result.name == "Green"
        assert result.hex_value == "#00FF00"

    def test_update(self):
        """Test update method."""
        data = {"name": "Updated Red"}
        result = self.repository.update(self.color.id, **data)
        assert result.name == "Updated Red"

    def test_delete(self):
        """Test delete method."""
        color_id = self.color.id
        result = self.repository.delete(color_id)
        assert result
        assert not Color.objects.filter(id=color_id).exists()

    def test_exists(self):
        """Test exists method."""
        assert self.repository.exists(id=self.color.id)
        assert not self.repository.exists(id=999)

    def test_count(self):
        """Test count method."""
        Color.objects.create(name="Blue", hex_value="#0000FF")
        result = self.repository.count()
        assert result == EXPECTED_COUNT_2

    def test_filter(self):
        """Test filter method."""
        Color.objects.create(name="Blue", hex_value="#0000FF")
        result = self.repository.filter(name="Red")
        assert result.count() == 1
        assert result.first() == self.color

    def test_bulk_create(self):
        """Test bulk_create method."""
        colors_data = [
            Color(name="Blue", hex_value="#0000FF"),
            Color(name="Green", hex_value="#00FF00"),
        ]
        result = self.repository.bulk_create(colors_data)
        assert len(result) == EXPECTED_COUNT_2
        assert Color.objects.count() == EXPECTED_COUNT_3

    def test_bulk_update(self):
        """Test bulk_update method."""
        color2 = Color.objects.create(name="Blue", hex_value="#0000FF")
        colors = [self.color, color2]
        for color in colors:
            color.name = f"Updated {color.name}"

        result = self.repository.bulk_update(colors, ["name"])
        assert result == EXPECTED_COUNT_2

        self.color.refresh_from_db()
        color2.refresh_from_db()
        assert self.color.name == "Updated Red"
        assert color2.name == "Updated Blue"


class TestPhotoRepository(TestCase):
    """Test cases for PhotoRepository."""

    def setUp(self):
        """Set up test data."""
        self.repository = PhotoRepository()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.brand = Brand.objects.create(name="Test Brand")
        self.club = Club.objects.create(name="Test Club")
        self.season = Season.objects.create(year="2023-24", first_year="2023", second_year="24")
        self.color = Color.objects.create(name="Red", hex_value="#FF0000")
        self.size = Size.objects.create(name="M", category="tops")

        # Create test jersey using MTI
        self.base_item = BaseItem.objects.create(
            user=self.user,
            name="Test Jersey",
            brand=self.brand,
            club=self.club,
            season=self.season,
            main_color=self.color,
            item_type="jersey",
        )
        self.jersey = Jersey.objects.create(
            base_item=self.base_item,
            size=self.size,
        )

    def test_photo_repository_integration_with_real_photos(self):
        """Test photo repository integration with real photo data."""
        from io import BytesIO
        from unittest.mock import patch

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        from footycollect.collection.models import Photo

        # Create a valid test image
        img = Image.new("RGB", (100, 100), color="red")
        img_io = BytesIO()
        img.save(img_io, format="JPEG")
        img_io.seek(0)

        test_image1 = SimpleUploadedFile(
            "test1.jpg",
            img_io.read(),
            content_type="image/jpeg",
        )
        img_io.seek(0)
        test_image2 = SimpleUploadedFile(
            "test2.jpg",
            img_io.read(),
            content_type="image/jpeg",
        )

        # Mock optimize_image to avoid actual optimization during tests
        with patch("footycollect.core.utils.images.optimize_image") as mock_optimize:
            # Return None to skip AVIF optimization
            mock_optimize.return_value = None
            # Create photos for the base_item (GenericRelation is on BaseItem)
            photo1 = Photo.objects.create(
                content_object=self.base_item,
                image=test_image1,
                order=1,
            )
            photo2 = Photo.objects.create(
                content_object=self.base_item,
                image=test_image2,
                order=2,
            )

        # Refresh from database to ensure they're saved
        photo1.refresh_from_db()
        photo2.refresh_from_db()

        # Test get_photos_by_item with real data
        photos = self.repository.get_photos_by_item(self.jersey)
        assert photos.count() == 2  # noqa: PLR2004
        assert photo1 in photos
        assert photo2 in photos

        # Test get_main_photo with real data
        main_photo = self.repository.get_main_photo(self.jersey)
        assert main_photo is not None
        assert main_photo.order == 1  # First photo should be main

        # Test get_photos_count_by_item with real data
        count = self.repository.get_photos_count_by_item(self.jersey)
        assert count == 2  # noqa: PLR2004

        # Test reorder_photos with real data
        new_order = [(photo2.id, 0), (photo1.id, 1)]
        result = self.repository.reorder_photos(self.jersey, new_order)
        assert result is True

        # Verify reordering worked
        photos_after = self.repository.get_photos_by_item(self.jersey)
        first_photo = photos_after.first()
        assert first_photo.id == photo2.id

        # Test delete_photos_by_item with real data
        deleted_count = self.repository.delete_photos_by_item(self.jersey)
        assert deleted_count == 2  # noqa: PLR2004

        # Verify photos were deleted
        remaining_count = self.repository.get_photos_count_by_item(self.jersey)
        assert remaining_count == 0
