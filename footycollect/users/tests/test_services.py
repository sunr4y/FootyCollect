"""
Tests for user services.
"""
# ruff: noqa: SLF001

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from footycollect.users.services import UserService

User = get_user_model()

# Constants for test values
TEST_PASSWORD = "testpass123"
EXPECTED_ITEMS_COUNT_5 = 5
EXPECTED_ITEMS_COUNT_3 = 3
EXPECTED_ITEMS_COUNT_10 = 10
EXPECTED_ITEMS_COUNT_15 = 15


class TestUserService(TestCase):
    """Test cases for UserService."""

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

    def test_init(self):
        """Test service initialization."""
        with patch("footycollect.users.services.get_item_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service

            service = UserService()

            assert service.item_service == mock_service
            mock_get_service.assert_called_once()

    @patch("footycollect.collection.models.Jersey")
    @patch("footycollect.users.services.get_item_service")
    def test_get_user_profile_data_public_user(self, mock_get_service, mock_jersey_model):
        """Test get_user_profile_data with public user."""
        mock_item_service = Mock()
        mock_get_service.return_value = mock_item_service

        mock_items = Mock()
        mock_items.count.return_value = EXPECTED_ITEMS_COUNT_5
        mock_items.filter.return_value.values.return_value.distinct.return_value.count.return_value = (
            EXPECTED_ITEMS_COUNT_3
        )
        mock_item_service.get_user_items.return_value = mock_items

        mock_recent_qs = Mock()
        mock_recent_qs.__getitem__ = Mock(return_value=[])
        (
            mock_jersey_model.objects.filter.return_value.select_related.return_value.prefetch_related.return_value.order_by.return_value
        ) = mock_recent_qs

        service = UserService()
        result = service.get_user_profile_data(self.user, self.other_user)

        assert result["show_details"]
        assert result["user"] == self.user
        assert result["total_items"] == 5  # noqa: PLR2004
        assert result["total_teams"] == 3  # noqa: PLR2004
        assert result["total_competitions"] == 3  # noqa: PLR2004
        assert list(result["recent_items"]) == []

    @patch("footycollect.users.services.get_item_service")
    def test_get_user_profile_data_private_user(self, mock_get_service):
        """Test get_user_profile_data with private user."""
        mock_item_service = Mock()
        mock_get_service.return_value = mock_item_service

        # Make user private
        self.user.is_private = True
        self.user.save()

        service = UserService()
        result = service.get_user_profile_data(self.user, self.other_user)

        assert not result["show_details"]
        assert result["user"] == self.user

    @patch("footycollect.collection.models.Jersey")
    @patch("footycollect.users.services.get_item_service")
    def test_get_user_profile_data_own_profile(self, mock_get_service, mock_jersey_model):
        """Test get_user_profile_data with own profile."""
        mock_item_service = Mock()
        mock_get_service.return_value = mock_item_service

        self.user.is_private = True
        self.user.save()

        mock_items = Mock()
        mock_items.count.return_value = 2
        mock_items.filter.return_value.values.return_value.distinct.return_value.count.return_value = 1
        mock_item_service.get_user_items.return_value = mock_items

        mock_recent_qs = Mock()
        mock_recent_qs.__getitem__ = Mock(return_value=[])
        (
            mock_jersey_model.objects.filter.return_value.select_related.return_value.prefetch_related.return_value.order_by.return_value
        ) = mock_recent_qs

        service = UserService()
        result = service.get_user_profile_data(self.user, self.user)

        assert result["show_details"]
        assert result["user"] == self.user

    @patch("footycollect.users.services.get_item_service")
    def test_get_user_statistics(self, mock_get_service):
        """Test get_user_statistics method."""
        mock_item_service = Mock()
        mock_get_service.return_value = mock_item_service

        mock_items = Mock()
        mock_items.count.return_value = 10
        mock_items.filter.return_value.values.return_value.distinct.return_value.count.return_value = 5
        mock_item_service.get_user_items.return_value = mock_items

        service = UserService()

        with (
            patch.object(service, "_get_items_by_type") as mock_by_type,
            patch.object(service, "_get_items_by_year") as mock_by_year,
        ):
            mock_by_type.return_value = {"jersey": 8, "shorts": 2}
            mock_by_year.return_value = {2023: 5, 2024: 5}

            result = service.get_user_statistics(self.user)

            assert result["total_items"] == EXPECTED_ITEMS_COUNT_10
            assert result["total_teams"] == EXPECTED_ITEMS_COUNT_5
            assert result["total_competitions"] == EXPECTED_ITEMS_COUNT_5
            assert result["items_by_type"] == {"jersey": 8, "shorts": 2}
            assert result["items_by_year"] == {2023: 5, 2024: 5}

    def test_can_view_profile_public_user(self):
        """Test can_view_profile with public user."""
        service = UserService()

        result = service.can_view_profile(self.user, self.other_user)

        assert result

    def test_can_view_profile_private_user(self):
        """Test can_view_profile with private user."""
        self.user.is_private = True
        self.user.save()

        service = UserService()

        result = service.can_view_profile(self.user, self.other_user)

        assert not result

    def test_can_view_profile_own_profile(self):
        """Test can_view_profile with own profile."""
        self.user.is_private = True
        self.user.save()

        service = UserService()

        result = service.can_view_profile(self.user, self.user)

        assert result

    def test_get_public_users(self):
        """Test get_public_users method."""
        service = UserService()

        result = service.get_public_users(limit=5)

        assert self.user in result
        assert self.other_user in result

    @patch("footycollect.users.services.get_item_service")
    def test_get_user_activity_summary(self, mock_get_service):
        """Test get_user_activity_summary method."""
        mock_item_service = Mock()
        mock_get_service.return_value = mock_item_service

        mock_items = Mock()
        mock_items.count.return_value = 15
        # Mock the queryset slicing
        mock_queryset = Mock()
        mock_queryset.__getitem__ = Mock(return_value=[])
        mock_items.order_by.return_value = mock_queryset
        mock_item_service.get_user_items.return_value = mock_items

        service = UserService()

        with (
            patch.object(service, "_get_most_common_club") as mock_club,
            patch.object(service, "_get_most_common_competition") as mock_competition,
        ):
            mock_club.return_value = "Real Madrid"
            mock_competition.return_value = "La Liga"

            result = service.get_user_activity_summary(self.user)

            assert result["total_items"] == EXPECTED_ITEMS_COUNT_15
            assert result["recent_activity"] == []
            assert result["most_common_club"] == "Real Madrid"
            assert result["most_common_competition"] == "La Liga"

    def test_get_items_by_type(self):
        """Test _get_items_by_type method."""
        service = UserService()

        mock_items = Mock()
        mock_items.values.return_value.annotate.return_value.values_list.return_value = [("jersey", 5), ("shorts", 2)]

        result = service._get_items_by_type(mock_items)

        assert result == {"jersey": 5, "shorts": 2}

    def test_get_items_by_year(self):
        """Test _get_items_by_year method."""
        service = UserService()

        mock_items = Mock()
        mock_items.annotate.return_value.values.return_value.annotate.return_value.values_list.return_value = [
            (2023, 3),
            (2024, 4),
        ]

        result = service._get_items_by_year(mock_items)

        assert result == {2023: 3, 2024: 4}

    def test_get_most_common_club(self):
        """Test _get_most_common_club method."""
        service = UserService()

        mock_items = Mock()
        mock_items.filter.return_value.values.return_value.annotate.return_value.order_by.return_value.first.return_value = {  # noqa: E501
            "club__name": "Real Madrid",
        }

        result = service._get_most_common_club(mock_items)

        assert result == "Real Madrid"

    def test_get_most_common_club_no_clubs(self):
        """Test _get_most_common_club method with no clubs."""
        service = UserService()

        mock_items = Mock()
        mock_items.filter.return_value.values.return_value.annotate.return_value.order_by.return_value.first.return_value = None  # noqa: E501

        result = service._get_most_common_club(mock_items)

        assert result is None

    def test_get_most_common_competition(self):
        """Test _get_most_common_competition method."""
        service = UserService()

        mock_items = Mock()
        mock_items.filter.return_value.values.return_value.annotate.return_value.order_by.return_value.first.return_value = {  # noqa: E501
            "competitions__name": "La Liga",
        }

        result = service._get_most_common_competition(mock_items)

        assert result == "La Liga"

    def test_get_most_common_competition_no_competitions(self):
        """Test _get_most_common_competition method with no competitions."""
        service = UserService()

        mock_items = Mock()
        mock_items.filter.return_value.values.return_value.annotate.return_value.order_by.return_value.first.return_value = None  # noqa: E501

        result = service._get_most_common_competition(mock_items)

        assert result is None
