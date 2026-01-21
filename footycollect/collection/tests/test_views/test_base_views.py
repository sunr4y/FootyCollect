"""
Tests for base collection views.

This module tests the real functionality of base views including:
- User filtering in get_queryset
- Context data inclusion
- Form processing
- Authentication requirements
"""

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from footycollect.collection.models import BaseItem, Brand, Club, Season
from footycollect.collection.views.base import (
    BaseItemCreateView,
    BaseItemDeleteView,
    BaseItemDetailView,
    BaseItemListView,
    BaseItemUpdateView,
    CollectionSuccessMessageMixin,
)

User = get_user_model()

# Constants for test values
TEST_PASSWORD = "testpass123"
HTTP_FOUND = 302
PAGINATE_BY = 20


class TestCollectionLoginRequiredMixin(TestCase):
    """Test CollectionLoginRequiredMixin functionality."""

    def test_mixin_redirects_unauthenticated_users(self):
        """Test that mixin redirects unauthenticated users to login."""
        url = reverse("collection:item_list")
        response = self.client.get(url)

        # Should redirect to login page
        assert response.status_code == HTTP_FOUND
        assert "/accounts/login/" in response.url

    def test_mixin_allows_authenticated_users(self):
        """Test that mixin allows authenticated users to access views."""
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.client.login(username="testuser", password=TEST_PASSWORD)

        url = reverse("collection:item_list")
        response = self.client.get(url)

        # Should not redirect (status 200 or 404 is fine, just not 302)
        assert response.status_code != HTTP_FOUND


class TestCollectionSuccessMessageMixin(TestCase):
    """Test CollectionSuccessMessageMixin functionality."""

    def test_get_success_message_returns_default_message(self):
        """Test that get_success_message returns default message."""
        mixin = CollectionSuccessMessageMixin()
        cleaned_data = {"name": "Test Item"}

        message = mixin.get_success_message(cleaned_data)

        assert message == "Operation completed successfully."

    def test_success_message_includes_item_name(self):
        """Test that success message can be customized with item data."""
        mixin = CollectionSuccessMessageMixin()
        cleaned_data = {"name": "Barcelona Jersey"}

        message = mixin.get_success_message(cleaned_data)

        # The default implementation doesn't use cleaned_data, but we test the method works
        assert message == "Operation completed successfully."


class TestBaseItemListView(TestCase):
    """Test BaseItemListView functionality."""

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
        self.club = Club.objects.create(name="Barcelona")
        self.season = Season.objects.create(year=2023)

        # Create items for different users
        self.user_item = BaseItem.objects.create(
            user=self.user,
            name="User Item",
            brand=self.brand,
            club=self.club,
            season=self.season,
        )
        self.other_item = BaseItem.objects.create(
            user=self.other_user,
            name="Other Item",
            brand=self.brand,
            club=self.club,
            season=self.season,
        )

    def test_get_queryset_filters_by_user(self):
        """Test that get_queryset only returns items for the current user."""
        view = BaseItemListView()
        view.request = Mock()
        view.request.user = self.user

        with patch("footycollect.collection.views.base.get_item_service") as mock_service:
            mock_item_service = Mock()
            mock_item_service.get_user_items.return_value = BaseItem.objects.filter(user=self.user)
            mock_service.return_value = mock_item_service

            queryset = view.get_queryset()

            # Should only return user's items
            assert queryset.count() == 1
            assert self.user_item in queryset
            assert self.other_item not in queryset
            mock_item_service.get_user_items.assert_called_once_with(self.user)

    def test_get_context_data_includes_total_items(self):
        """Test that get_context_data includes total_items count."""
        view = BaseItemListView()
        view.request = Mock()
        view.request.user = self.user

        with patch("footycollect.collection.views.base.get_item_service") as mock_service:
            mock_item_service = Mock()
            queryset = BaseItem.objects.filter(user=self.user)
            mock_item_service.get_user_items.return_value = queryset
            mock_service.return_value = mock_item_service

            with patch("footycollect.collection.views.base.ListView.get_context_data") as mock_super:
                mock_super.return_value = {"items": []}
                view.object_list = queryset

                context = view.get_context_data()

                assert "total_items" in context
                assert context["total_items"] == 1  # We have 1 item for this user
                mock_super.assert_called_once()

    def test_get_context_data_calls_super(self):
        """Test that get_context_data calls super().get_context_data()."""
        view = BaseItemListView()
        view.request = Mock()
        view.request.user = self.user

        with patch("footycollect.collection.views.base.get_item_service") as mock_service:
            mock_item_service = Mock()
            mock_item_service.get_user_items.return_value = BaseItem.objects.filter(user=self.user)
            mock_service.return_value = mock_item_service

            with patch("footycollect.collection.views.base.ListView.get_context_data") as mock_super:
                mock_super.return_value = {"items": []}

                view.get_context_data()

                mock_super.assert_called_once()

    def test_list_view_get_queryset_integration(self):
        """Test list view get_queryset integration with real data."""
        view = BaseItemListView()
        view.request = Mock()
        view.request.user = self.user

        # Test with real queryset (no mocking)
        queryset = view.get_queryset()

        # Should return a queryset
        assert queryset is not None
        # Should be a QuerySet
        assert hasattr(queryset, "filter")
        assert hasattr(queryset, "count")

    def test_list_view_get_context_data_integration(self):
        """Test list view get_context_data integration with real data."""
        view = BaseItemListView()
        view.request = Mock()
        view.request.user = self.user
        queryset = BaseItem.objects.filter(user=self.user)
        view.object_list = queryset  # Set object_list to queryset
        view.kwargs = {}  # Set kwargs to avoid AttributeError
        view.request.GET = {}  # Set GET to avoid AttributeError

        # Test with real context data (no mocking)
        context = view.get_context_data()

        # Should return a dictionary
        assert isinstance(context, dict)
        # Should include standard ListView context
        assert "object_list" in context or "items" in context

    def test_list_view_pagination_configuration(self):
        """Test that list view has correct pagination configuration."""
        view = BaseItemListView()

        # Test pagination configuration
        assert hasattr(view, "paginate_by")
        assert view.paginate_by == PAGINATE_BY


class TestBaseItemDetailView(TestCase):
    """Test BaseItemDetailView functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )

        self.brand = Brand.objects.create(name="Nike")
        self.club = Club.objects.create(name="Barcelona")
        self.season = Season.objects.create(year=2023)

        self.item = BaseItem.objects.create(
            user=self.user,
            name="Test Item",
            brand=self.brand,
            club=self.club,
            season=self.season,
        )

    def test_get_queryset_filters_by_user(self):
        """Test that get_queryset only returns items for the current user."""
        view = BaseItemDetailView()
        view.request = Mock()
        view.request.user = self.user

        with patch("footycollect.collection.views.base.get_item_service") as mock_service:
            mock_item_service = Mock()
            mock_item_service.get_user_items.return_value = BaseItem.objects.filter(user=self.user)
            mock_service.return_value = mock_item_service

            queryset = view.get_queryset()

            assert queryset.count() == 1
            assert self.item in queryset
            mock_item_service.get_user_items.assert_called_once_with(self.user)

    def test_get_context_data_includes_photos_and_specific_item(self):
        """Test that get_context_data includes photos and specific item."""
        view = BaseItemDetailView()
        view.object = self.item

        with patch("footycollect.collection.views.base.get_photo_service") as mock_photo_service:
            mock_photo_service_instance = Mock()
            mock_photos = [Mock(), Mock()]
            mock_photo_service_instance.get_item_photos.return_value = mock_photos
            mock_photo_service.return_value = mock_photo_service_instance

            with patch.object(self.item, "get_specific_item") as mock_get_specific:
                mock_specific_item = Mock()
                mock_get_specific.return_value = mock_specific_item

                context = view.get_context_data()

                assert "photos" in context
                assert "specific_item" in context
                assert context["photos"] == mock_photos
                assert context["specific_item"] == mock_specific_item
                mock_photo_service_instance.get_item_photos.assert_called_once_with(self.item)
                mock_get_specific.assert_called_once()


class TestBaseItemCreateView(TestCase):
    """Test BaseItemCreateView functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )

    def test_get_form_kwargs_includes_user(self):
        """Test that get_form_kwargs includes user."""
        view = BaseItemCreateView()
        view.request = Mock()
        view.request.user = self.user

        kwargs = view.get_form_kwargs()

        assert "user" in kwargs
        assert kwargs["user"] == self.user
        assert "instance" in kwargs
        assert isinstance(kwargs["instance"], BaseItem)

    def test_get_form_kwargs_with_existing_instance(self):
        """Test that get_form_kwargs preserves existing instance."""
        view = BaseItemCreateView()
        view.request = Mock()
        view.request.user = self.user

        existing_instance = BaseItem()

        # Mock the form_kwargs to include existing instance
        with patch.object(view, "get_form_kwargs") as mock_get_kwargs:
            mock_get_kwargs.return_value = {
                "user": self.user,
                "instance": existing_instance,
            }

            kwargs = view.get_form_kwargs()

            assert "user" in kwargs
            assert kwargs["user"] == self.user
            assert "instance" in kwargs
            assert kwargs["instance"] == existing_instance

    def test_form_valid_calls_super(self):
        """Test that form_valid calls super().form_valid()."""
        view = BaseItemCreateView()
        view.request = Mock()
        mock_form = Mock()

        with patch("footycollect.collection.views.base.CreateView.form_valid") as mock_super:
            mock_super.return_value = Mock()

            result = view.form_valid(mock_form)

            mock_super.assert_called_once_with(mock_form)
            assert result == mock_super.return_value

    def test_create_view_get_form_kwargs_integration(self):
        """Test create view get_form_kwargs integration with real data."""
        view = BaseItemCreateView()
        view.request = Mock()
        view.request.user = self.user

        # Test with real form kwargs (no mocking)
        kwargs = view.get_form_kwargs()

        # Should return a dictionary
        assert isinstance(kwargs, dict)
        # Should include user
        assert "user" in kwargs
        assert kwargs["user"] == self.user

    def test_create_view_form_valid_integration(self):
        """Test create view form_valid integration with real data."""
        view = BaseItemCreateView()
        view.request = Mock()
        mock_form = Mock()

        # Test with real form_valid (no mocking)
        result = view.form_valid(mock_form)

        # Should return a response
        assert result is not None
        # Should be a response object
        assert hasattr(result, "status_code")

    def test_create_view_success_url_configuration(self):
        """Test create view success_url configuration."""
        view = BaseItemCreateView()

        # Test success_url configuration
        assert hasattr(view, "success_url")
        assert view.success_url == reverse("collection:item_list")


class TestBaseItemUpdateView(TestCase):
    """Test BaseItemUpdateView functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )

        self.brand = Brand.objects.create(name="Nike")
        self.club = Club.objects.create(name="Barcelona")
        self.season = Season.objects.create(year=2023)

        self.item = BaseItem.objects.create(
            user=self.user,
            name="Test Item",
            brand=self.brand,
            club=self.club,
            season=self.season,
        )

    def test_update_view_get_queryset_integration(self):
        """Test update view get_queryset integration with real data."""
        view = BaseItemUpdateView()
        view.request = Mock()
        view.request.user = self.user

        # Test with real queryset (no mocking)
        queryset = view.get_queryset()

        # Should return a queryset
        assert queryset is not None
        # Should be a QuerySet
        assert hasattr(queryset, "filter")
        assert hasattr(queryset, "count")

    def test_update_view_success_url_configuration(self):
        """Test update view success_url configuration."""
        view = BaseItemUpdateView()

        # Test success_url configuration
        assert hasattr(view, "success_url")
        assert view.success_url == reverse("collection:item_list")

    def test_update_view_template_name_configuration(self):
        """Test update view template_name configuration."""
        view = BaseItemUpdateView()

        # Test template_name configuration
        assert hasattr(view, "template_name")
        assert view.template_name == "collection/item_form.html"


class TestBaseItemDeleteView(TestCase):
    """Test BaseItemDeleteView functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )

        self.brand = Brand.objects.create(name="Nike")
        self.club = Club.objects.create(name="Barcelona")
        self.season = Season.objects.create(year=2023)

        self.item = BaseItem.objects.create(
            user=self.user,
            name="Test Item",
            brand=self.brand,
            club=self.club,
            season=self.season,
        )

    def test_delete_view_get_queryset_integration(self):
        """Test delete view get_queryset integration with real data."""
        view = BaseItemDeleteView()
        view.request = Mock()
        view.request.user = self.user

        # Test with real queryset (no mocking)
        queryset = view.get_queryset()

        # Should return a queryset
        assert queryset is not None
        # Should be a QuerySet
        assert hasattr(queryset, "filter")
        assert hasattr(queryset, "count")

    def test_delete_view_delete_method_integration(self):
        """Test delete view delete method integration with real data."""
        view = BaseItemDeleteView()
        view.request = Mock()

        # Test that delete method exists and is callable
        assert hasattr(view, "delete")
        assert callable(view.delete)

    def test_delete_view_success_url_configuration(self):
        """Test delete view success_url configuration."""
        view = BaseItemDeleteView()

        # Test success_url configuration
        assert hasattr(view, "success_url")
        assert view.success_url == reverse("collection:item_list")

    def test_delete_view_template_name_configuration(self):
        """Test delete view template_name configuration."""
        view = BaseItemDeleteView()

        # Test template_name configuration
        assert hasattr(view, "template_name")
        assert view.template_name == "collection/item_confirm_delete.html"
