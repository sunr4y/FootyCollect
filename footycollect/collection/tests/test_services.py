"""Tests for collection services."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from footycollect.collection.services.collection_service import CollectionService
from footycollect.collection.services.size_service import SizeService

User = get_user_model()

# Constants for test values
TEST_PASSWORD = "testpass123"  # NOSONAR (S2068) "test fixture only, not a credential"
EXPECTED_ITEMS_COUNT_5 = 5
EXPECTED_ITEMS_COUNT_8 = 8
EXPECTED_ITEMS_COUNT_2 = 2


class TestCollectionService(TestCase):
    """Test CollectionService."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.service = CollectionService()

    def test_init(self):
        """Test service initialization."""
        service = CollectionService()
        assert isinstance(service, CollectionService)
        assert service.item_service is not None
        assert service.photo_service is not None
        assert service.color_service is not None
        assert service.size_service is not None

    def test_initialize_collection_data(self):
        """Test initialize_collection_data method."""
        with (
            patch.object(self.service.color_service, "initialize_default_colors") as mock_colors,
            patch.object(self.service.size_service, "initialize_default_sizes") as mock_sizes,
        ):
            mock_colors.return_value = 5
            mock_sizes.return_value = 8

            result = self.service.initialize_collection_data()

            assert result["colors"] == EXPECTED_ITEMS_COUNT_5
            assert result["sizes"] == EXPECTED_ITEMS_COUNT_8
            mock_colors.assert_called_once()
            mock_sizes.assert_called_once()


class TestSizeService(TestCase):
    """Test SizeService."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.service = SizeService()

    def test_init(self):
        """Test service initialization."""
        service = SizeService()
        assert isinstance(service, SizeService)
        assert service.size_repository is not None

    def test_initialize_default_sizes(self):
        """Test initialize_default_sizes method."""
        with patch.object(self.service.size_repository, "create_default_sizes") as mock_create:
            mock_create.return_value = 8

            result = self.service.initialize_default_sizes()

            assert result == EXPECTED_ITEMS_COUNT_8
            mock_create.assert_called_once()

    def test_get_sizes_for_item_form(self):
        """Test get_sizes_for_item_form method."""
        from footycollect.collection.models import Size

        # Create test sizes
        Size.objects.create(name="S", category="tops")
        Size.objects.create(name="M", category="tops")
        Size.objects.create(name="L", category="bottoms")

        result = self.service.get_sizes_for_item_form()

        assert "tops" in result
        assert "bottoms" in result
        assert "accessories" in result
        assert len(result["tops"]) == EXPECTED_ITEMS_COUNT_2
        assert len(result["bottoms"]) == 1
        assert len(result["accessories"]) == 0
