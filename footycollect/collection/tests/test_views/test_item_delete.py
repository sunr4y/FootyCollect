"""
Tests for ItemDeleteView functionality.

This module tests the delete view including:
- Authentication requirements
- User permission checks (users can only delete their own items)
- Page parameter handling in redirects
- Photo deletion cleanup
- Success message display
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from footycollect.collection.factories import (
    BaseItemFactory,
    BrandFactory,
    ClubFactory,
    JerseyFactory,
    PhotoFactory,
    SeasonFactory,
    SizeFactory,
    UserFactory,
)
from footycollect.collection.models import BaseItem, Jersey, Photo

User = get_user_model()

# Constants for test values
TEST_PASSWORD = "testpass123"
HTTP_OK = 200
HTTP_SUCCESS = 200
HTTP_REDIRECT = 302
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404

# Photo count constants
EXPECTED_THREE_PHOTOS = 3
EXPECTED_TWO_PHOTOS = 2


class TestItemDeleteViewAuthentication(TestCase):
    """Test ItemDeleteView authentication requirements."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.user.set_password(TEST_PASSWORD)
        self.user.save()

        self.brand = BrandFactory(name="Nike")
        self.club = ClubFactory(name="Barcelona")
        self.season = SeasonFactory(year="2023-24", first_year="2023", second_year="24")
        self.size = SizeFactory(name="M", category="tops")

        self.base_item = BaseItemFactory(
            user=self.user,
            brand=self.brand,
            club=self.club,
            season=self.season,
        )
        self.jersey = JerseyFactory(base_item=self.base_item, size=self.size)

    def test_delete_view_requires_login_get(self):
        """Test that GET request to delete view requires login."""
        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.get(url)

        assert response.status_code == HTTP_REDIRECT
        assert "/accounts/login/" in response.url

    def test_delete_view_requires_login_post(self):
        """Test that POST request to delete view requires login."""
        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.post(url)

        assert response.status_code == HTTP_REDIRECT
        assert "/accounts/login/" in response.url
        # Item should not be deleted
        assert BaseItem.objects.filter(pk=self.base_item.pk).exists()

    def test_delete_view_accessible_when_logged_in(self):
        """Test that delete view is accessible when user is logged in."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.get(url)

        assert response.status_code == HTTP_OK


class TestItemDeleteViewPermissions(TestCase):
    """Test ItemDeleteView user permission checks."""

    def setUp(self):
        """Set up test data with two users."""
        # Create first user with an item
        self.user1 = UserFactory()
        self.user1.set_password(TEST_PASSWORD)
        self.user1.save()

        # Create second user
        self.user2 = UserFactory()
        self.user2.set_password(TEST_PASSWORD)
        self.user2.save()

        self.brand = BrandFactory(name="Nike")
        self.club = ClubFactory(name="Barcelona")
        self.season = SeasonFactory(year="2023-24", first_year="2023", second_year="24")
        self.size = SizeFactory(name="M", category="tops")

        # Create item owned by user1
        self.base_item = BaseItemFactory(
            user=self.user1,
            brand=self.brand,
            club=self.club,
            season=self.season,
        )
        self.jersey = JerseyFactory(base_item=self.base_item, size=self.size)

    def test_user_can_delete_own_item(self):
        """Test that a user can delete their own item."""
        self.client.login(username=self.user1.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.post(url)

        assert response.status_code == HTTP_REDIRECT
        assert not BaseItem.objects.filter(pk=self.base_item.pk).exists()

    def test_user_cannot_delete_other_users_item(self):
        """Test that a user cannot delete another user's item."""
        self.client.login(username=self.user2.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.post(url)

        # Should return 404 because the item is not in user2's queryset
        assert response.status_code == HTTP_NOT_FOUND
        # Item should still exist
        assert BaseItem.objects.filter(pk=self.base_item.pk).exists()

    def test_user_cannot_view_delete_page_for_other_users_item(self):
        """Test that a user cannot view the delete confirmation page for another user's item."""
        self.client.login(username=self.user2.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.get(url)

        # Should return 404 because the item is not in user2's queryset
        assert response.status_code == HTTP_NOT_FOUND


class TestItemDeleteViewPageRedirects(TestCase):
    """Test ItemDeleteView page parameter handling in redirects."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.user.set_password(TEST_PASSWORD)
        self.user.save()

        self.brand = BrandFactory(name="Nike")
        self.club = ClubFactory(name="Barcelona")
        self.season = SeasonFactory(year="2023-24", first_year="2023", second_year="24")
        self.size = SizeFactory(name="M", category="tops")

        self.base_item = BaseItemFactory(
            user=self.user,
            brand=self.brand,
            club=self.club,
            season=self.season,
        )
        self.jersey = JerseyFactory(base_item=self.base_item, size=self.size)

    def test_delete_redirects_to_item_list_without_page_param(self):
        """Test that delete redirects to item_list when no page parameter is provided."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.post(url)

        assert response.status_code == HTTP_REDIRECT
        expected_url = reverse("collection:item_list")
        assert response.url == expected_url

    def test_delete_redirects_to_item_list_with_page_1(self):
        """Test that delete redirects to item_list without page param when page=1."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.post(url, data={"page": "1"})

        assert response.status_code == HTTP_REDIRECT
        expected_url = reverse("collection:item_list")
        assert response.url == expected_url

    def test_delete_redirects_to_page_3_when_page_param_is_3(self):
        """Test that delete redirects to page 3 when page=3 parameter is provided."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.post(url, data={"page": "3"})

        assert response.status_code == HTTP_REDIRECT
        expected_url = f"{reverse('collection:item_list')}?page=3"
        assert response.url == expected_url

    def test_delete_redirects_with_page_from_get_param(self):
        """Test that delete uses page parameter from GET if not in POST."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        url_with_page = f"{url}?page=5"
        response = self.client.post(url_with_page)

        assert response.status_code == HTTP_REDIRECT
        expected_url = f"{reverse('collection:item_list')}?page=5"
        assert response.url == expected_url

    def test_delete_post_page_param_takes_precedence_over_get(self):
        """Test that POST page parameter takes precedence over GET page parameter."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        url_with_page = f"{url}?page=5"
        response = self.client.post(url_with_page, data={"page": "3"})

        assert response.status_code == HTTP_REDIRECT
        expected_url = f"{reverse('collection:item_list')}?page=3"
        assert response.url == expected_url

    def test_delete_redirects_to_page_2(self):
        """Test that delete redirects correctly with page=2."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.post(url, data={"page": "2"})

        assert response.status_code == HTTP_REDIRECT
        expected_url = f"{reverse('collection:item_list')}?page=2"
        assert response.url == expected_url


class TestItemDeleteViewPhotoCleanup(TestCase):
    """Test that ItemDeleteView properly deletes associated photos."""

    def setUp(self):
        """Set up test data with photos."""
        self.user = UserFactory()
        self.user.set_password(TEST_PASSWORD)
        self.user.save()

        self.brand = BrandFactory(name="Nike")
        self.club = ClubFactory(name="Barcelona")
        self.season = SeasonFactory(year="2023-24", first_year="2023", second_year="24")
        self.size = SizeFactory(name="M", category="tops")

        self.base_item = BaseItemFactory(
            user=self.user,
            brand=self.brand,
            club=self.club,
            season=self.season,
        )
        self.jersey = JerseyFactory(base_item=self.base_item, size=self.size)

    @patch("footycollect.collection.models.optimize_image")
    def test_delete_removes_associated_photos(self, mock_optimize):
        """Test that deleting an item also deletes its associated photos."""
        mock_optimize.return_value = None

        # Create photos for the item
        photo1 = PhotoFactory(content_object=self.base_item, user=self.user, order=0)
        photo2 = PhotoFactory(content_object=self.base_item, user=self.user, order=1)
        photo3 = PhotoFactory(content_object=self.base_item, user=self.user, order=2)

        photo_pks = [photo1.pk, photo2.pk, photo3.pk]

        # Verify photos exist
        assert Photo.objects.filter(pk__in=photo_pks).count() == EXPECTED_THREE_PHOTOS

        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.post(url)

        assert response.status_code == HTTP_REDIRECT

        # Verify item is deleted
        assert not BaseItem.objects.filter(pk=self.base_item.pk).exists()

        # Verify all photos are deleted
        assert Photo.objects.filter(pk__in=photo_pks).count() == 0

    @patch("footycollect.collection.models.optimize_image")
    def test_delete_item_with_no_photos(self, mock_optimize):
        """Test that deleting an item with no photos works correctly."""
        mock_optimize.return_value = None

        # Verify no photos exist for this item
        assert self.base_item.photos.count() == 0

        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.post(url)

        assert response.status_code == HTTP_REDIRECT
        assert not BaseItem.objects.filter(pk=self.base_item.pk).exists()

    @patch("footycollect.collection.models.optimize_image")
    def test_delete_only_removes_photos_for_deleted_item(self, mock_optimize):
        """Test that deleting an item doesn't affect photos of other items."""
        mock_optimize.return_value = None

        # Create another item with photos
        other_base_item = BaseItemFactory(
            user=self.user,
            brand=self.brand,
            club=self.club,
            season=self.season,
        )
        JerseyFactory(base_item=other_base_item, size=self.size)

        # Create photos for both items
        photo_to_delete = PhotoFactory(content_object=self.base_item, user=self.user, order=0)
        photo_to_keep = PhotoFactory(content_object=other_base_item, user=self.user, order=0)

        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.post(url)

        assert response.status_code == HTTP_REDIRECT

        # Verify first item and its photo are deleted
        assert not BaseItem.objects.filter(pk=self.base_item.pk).exists()
        assert not Photo.objects.filter(pk=photo_to_delete.pk).exists()

        # Verify second item and its photo still exist
        assert BaseItem.objects.filter(pk=other_base_item.pk).exists()
        assert Photo.objects.filter(pk=photo_to_keep.pk).exists()


class TestItemDeleteViewSuccessMessage(TestCase):
    """Test that ItemDeleteView displays success message."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.user.set_password(TEST_PASSWORD)
        self.user.save()

        self.brand = BrandFactory(name="Nike")
        self.club = ClubFactory(name="Barcelona")
        self.season = SeasonFactory(year="2023-24", first_year="2023", second_year="24")
        self.size = SizeFactory(name="M", category="tops")

        self.base_item = BaseItemFactory(
            user=self.user,
            brand=self.brand,
            club=self.club,
            season=self.season,
        )
        self.jersey = JerseyFactory(base_item=self.base_item, size=self.size)

    def test_delete_shows_success_message(self):
        """Test that deletion succeeds and user is redirected to list."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.post(url, follow=True)

        # Verify successful redirect and item is deleted
        assert response.status_code == HTTP_SUCCESS
        assert not BaseItem.objects.filter(pk=self.base_item.pk).exists()
        # Verify we're on the item list page
        self.assertContains(response, "collection", status_code=HTTP_SUCCESS)

    @patch("footycollect.collection.models.optimize_image")
    def test_delete_with_photos_shows_appropriate_message(self, mock_optimize):
        """Test that success message mentions photos when item has photos."""
        mock_optimize.return_value = None

        # Create a photo for the item
        PhotoFactory(content_object=self.base_item, user=self.user, order=0)

        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.post(url, follow=True)

        # Verify the success message appears in the rendered HTML
        # The message should mention photos since photos were deleted
        self.assertContains(response, "photo", status_code=HTTP_SUCCESS)


class TestItemDeleteViewConfirmationPage(TestCase):
    """Test the delete confirmation page rendering."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.user.set_password(TEST_PASSWORD)
        self.user.save()

        self.brand = BrandFactory(name="Nike")
        self.club = ClubFactory(name="Barcelona")
        self.season = SeasonFactory(year="2023-24", first_year="2023", second_year="24")
        self.size = SizeFactory(name="M", category="tops")

        self.base_item = BaseItemFactory(
            user=self.user,
            brand=self.brand,
            club=self.club,
            season=self.season,
        )
        self.jersey = JerseyFactory(base_item=self.base_item, size=self.size)

    def test_delete_confirmation_page_renders(self):
        """Test that the delete confirmation page renders correctly."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.get(url)

        assert response.status_code == HTTP_OK
        assert "object" in response.context
        assert response.context["object"] == self.base_item

    def test_delete_confirmation_page_uses_correct_template(self):
        """Test that the delete view uses the correct template."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        response = self.client.get(url)

        assert response.status_code == HTTP_OK
        self.assertTemplateUsed(response, "collection/item_confirm_delete.html")

    def test_delete_nonexistent_item_returns_404(self):
        """Test that attempting to delete a nonexistent item returns 404."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": 99999})
        response = self.client.get(url)

        assert response.status_code == HTTP_NOT_FOUND

    def test_delete_confirmation_preserves_page_param_in_form(self):
        """Test that page parameter is available in the delete confirmation context."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": self.base_item.pk})
        url_with_page = f"{url}?page=3"
        response = self.client.get(url_with_page)

        assert response.status_code == HTTP_OK
        # The page parameter should be available in request.GET
        assert response.request["QUERY_STRING"] == "page=3"


class TestItemDeleteViewIntegration(TestCase):
    """Integration tests for ItemDeleteView with full workflow."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.user.set_password(TEST_PASSWORD)
        self.user.save()

        self.brand = BrandFactory(name="Nike")
        self.club = ClubFactory(name="Barcelona")
        self.season = SeasonFactory(year="2023-24", first_year="2023", second_year="24")
        self.size = SizeFactory(name="M", category="tops")

    @patch("footycollect.collection.models.optimize_image")
    def test_full_delete_workflow(self, mock_optimize):
        """Test the complete delete workflow from creation to deletion."""
        mock_optimize.return_value = None

        # Create an item with photos
        base_item = BaseItemFactory(
            user=self.user,
            brand=self.brand,
            club=self.club,
            season=self.season,
        )
        JerseyFactory(base_item=base_item, size=self.size)

        photo1 = PhotoFactory(content_object=base_item, user=self.user, order=0)
        photo2 = PhotoFactory(content_object=base_item, user=self.user, order=1)

        item_pk = base_item.pk
        photo_pks = [photo1.pk, photo2.pk]

        # Verify everything exists
        assert BaseItem.objects.filter(pk=item_pk).exists()
        assert Photo.objects.filter(pk__in=photo_pks).count() == EXPECTED_TWO_PHOTOS

        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        # Step 1: View the confirmation page
        url = reverse("collection:item_delete", kwargs={"pk": item_pk})
        response = self.client.get(url)
        assert response.status_code == HTTP_OK

        # Step 2: Confirm deletion
        response = self.client.post(url, follow=True)
        assert response.status_code == HTTP_OK

        # Step 3: Verify everything is deleted
        assert not BaseItem.objects.filter(pk=item_pk).exists()
        assert Photo.objects.filter(pk__in=photo_pks).count() == 0

        # Step 4: Verify successful redirect to item list
        self.assertContains(response, "collection", status_code=HTTP_OK)

    def test_delete_jersey_also_removes_jersey_specific_data(self):
        """Test that deleting a jersey removes both BaseItem and Jersey records."""
        base_item = BaseItemFactory(
            user=self.user,
            brand=self.brand,
            club=self.club,
            season=self.season,
        )
        jersey = JerseyFactory(base_item=base_item, size=self.size)

        base_item_pk = base_item.pk
        jersey_pk = jersey.pk

        # Verify both exist
        assert BaseItem.objects.filter(pk=base_item_pk).exists()
        assert Jersey.objects.filter(pk=jersey_pk).exists()

        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        url = reverse("collection:item_delete", kwargs={"pk": base_item_pk})
        response = self.client.post(url)

        assert response.status_code == HTTP_REDIRECT

        # Both should be deleted (Jersey is deleted via cascade)
        assert not BaseItem.objects.filter(pk=base_item_pk).exists()
        assert not Jersey.objects.filter(pk=jersey_pk).exists()
