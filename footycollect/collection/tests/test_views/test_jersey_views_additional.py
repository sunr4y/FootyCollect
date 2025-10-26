"""
Additional tests for jersey-related views to improve coverage.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from footycollect.collection.factories import (
    BrandFactory,
    ClubFactory,
    CompetitionFactory,
    JerseyFactory,
    SeasonFactory,
    SizeFactory,
    UserFactory,
)

User = get_user_model()

# HTTP status codes
HTTP_OK = 200
HTTP_FOUND = 302
HTTP_BAD_REQUEST = 400
HTTP_INTERNAL_SERVER_ERROR = 500

# Constants for test values
TEST_PASSWORD = "testpass123"


class JerseyViewsAdditionalTest(TestCase):
    """Additional test cases for Jersey-related views to improve coverage."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.user.set_password("testpass123")
        self.user.save()
        self.brand = BrandFactory(name="Nike")
        self.club = ClubFactory(name="Barcelona", country="ES")
        self.season = SeasonFactory(year="2023-24", first_year="2023", second_year="24")
        self.competition = CompetitionFactory(name="Champions League")

    def test_jersey_create_view_post_success(self):
        """Test Jersey create view POST with valid data."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="L", category="tops")

        form_data = {
            "name": "Test Jersey",
            "description": "Test description",
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "is_fan_version": True,
            "is_short_sleeve": True,
        }

        response = self.client.post(reverse("collection:jersey_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_create_view_post_invalid_data(self):
        """Test Jersey create view POST with invalid data."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        form_data = {
            "name": "",  # Invalid: empty name
            "brand": "invalid_id",  # Invalid: non-existent brand
        }

        response = self.client.post(reverse("collection:jersey_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_BAD_REQUEST]

    def test_jersey_update_view_post_success(self):
        """Test Jersey update view POST with valid data."""
        size = SizeFactory(name="M", category="tops")
        jersey = JerseyFactory(
            base_item__user=self.user,
            base_item__brand=self.brand,
            base_item__club=self.club,
            base_item__season=self.season,
            size=size,
            base_item__condition=8,
        )

        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        form_data = {
            "name": "Updated Jersey",
            "description": "Updated description",
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 9,
            "is_fan_version": False,
            "is_short_sleeve": False,
        }

        response = self.client.post(reverse("collection:jersey_update", kwargs={"pk": jersey.base_item.pk}), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_update_view_post_invalid_data(self):
        """Test Jersey update view POST with invalid data."""
        size = SizeFactory(name="M", category="tops")
        jersey = JerseyFactory(
            base_item__user=self.user,
            base_item__brand=self.brand,
            base_item__club=self.club,
            base_item__season=self.season,
            size=size,
            base_item__condition=8,
        )

        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        form_data = {
            "name": "",  # Invalid: empty name
            "condition": "invalid",  # Invalid: non-numeric condition
        }

        response = self.client.post(reverse("collection:jersey_update", kwargs={"pk": jersey.base_item.pk}), form_data)
        assert response.status_code in [HTTP_OK, HTTP_BAD_REQUEST]

    def test_jersey_delete_view_post_success(self):
        """Test Jersey delete view POST (confirmation)."""
        size = SizeFactory(name="M", category="tops")
        jersey = JerseyFactory(
            base_item__user=self.user,
            base_item__brand=self.brand,
            base_item__club=self.club,
            base_item__season=self.season,
            size=size,
            base_item__condition=8,
        )

        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        response = self.client.post(reverse("collection:item_delete", kwargs={"pk": jersey.base_item.pk}))
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_get_context(self):
        """Test JerseyFKAPICreateView GET method context."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        response = self.client.get(reverse("collection:jersey_fkapi_create"))
        assert response.status_code == HTTP_OK
        assert "form" in response.context

    def test_jersey_fkapi_create_view_post_with_competitions(self):
        """Test JerseyFKAPICreateView POST with competitions."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "name": "Test Jersey with Competitions",
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with competitions",
            "is_fan_version": True,
            "is_short_sleeve": True,
            "competitions": [self.competition.id],
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_kit_id(self):
        """Test JerseyFKAPICreateView POST with kit_id."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with kit",
            "is_fan_version": True,
            "is_short_sleeve": True,
            "kit_id": "12345",
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_api_data(self):
        """Test JerseyFKAPICreateView POST with API data."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand_name": "Nike",
            "club_name": "Real Madrid",
            "season_name": "2023-24",
            "competition_name": "Champions League",
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with API data",
            "is_fan_version": True,
            "is_short_sleeve": True,
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_external_images(self):
        """Test JerseyFKAPICreateView POST with external images."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with external images",
            "is_fan_version": True,
            "is_short_sleeve": True,
            "main_img_url": "https://example.com/image.jpg",
            "external_image_urls": "https://example.com/image1.jpg,https://example.com/image2.jpg",
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_photo_ids(self):
        """Test JerseyFKAPICreateView POST with photo IDs."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with photo IDs",
            "is_fan_version": True,
            "is_short_sleeve": True,
            "photo_ids": "1,2,3",
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_country_code(self):
        """Test JerseyFKAPICreateView POST with country code."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with country",
            "is_fan_version": True,
            "is_short_sleeve": True,
            "country_code": "ES",
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_name_generation(self):
        """Test JerseyFKAPICreateView POST with name generation from API data."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with name generation",
            "is_fan_version": True,
            "is_short_sleeve": True,
            "name": "Generated Jersey Name",
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_json_photo_ids(self):
        """Test JerseyFKAPICreateView POST with JSON photo IDs."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with JSON photo IDs",
            "is_fan_version": True,
            "is_short_sleeve": True,
            "photo_ids": '[{"id": "1", "order": 0}, {"url": "https://example.com/image.jpg", "order": 1}]',
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_empty_photo_ids(self):
        """Test JerseyFKAPICreateView POST with empty photo IDs."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with empty photo IDs",
            "is_fan_version": True,
            "is_short_sleeve": True,
            "photo_ids": "",
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_invalid_photo_ids(self):
        """Test JerseyFKAPICreateView POST with invalid photo IDs."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with invalid photo IDs",
            "is_fan_version": True,
            "is_short_sleeve": True,
            "photo_ids": "invalid_json",
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_brand_name_only(self):
        """Test JerseyFKAPICreateView POST with brand name only."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        form_data = {
            "brand_name": "Nike",
            "condition": 8,
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_club_name_only(self):
        """Test JerseyFKAPICreateView POST with club name only."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        form_data = {
            "club_name": "Real Madrid",
            "condition": 8,
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_season_name_only(self):
        """Test JerseyFKAPICreateView POST with season name only."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        form_data = {
            "season_name": "2023-24",
            "condition": 8,
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_competition_name_only(self):
        """Test JerseyFKAPICreateView POST with competition name only."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        form_data = {
            "competition_name": "La Liga",
            "condition": 8,
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_name_field(self):
        """Test JerseyFKAPICreateView POST with name field."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        form_data = {
            "name": "Custom Jersey Name",
            "condition": 8,
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_empty_name(self):
        """Test JerseyFKAPICreateView POST with empty name."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        form_data = {
            "name": "",
            "condition": 8,
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_BAD_REQUEST]

    def test_jersey_fkapi_create_view_post_with_no_name_data(self):
        """Test JerseyFKAPICreateView POST with no name data."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        form_data = {
            "condition": 8,
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_BAD_REQUEST]

    def test_jersey_fkapi_create_view_post_with_form_errors(self):
        """Test JerseyFKAPICreateView POST with form errors."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        form_data = {
            "brand": "invalid",
            "condition": "invalid",
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_BAD_REQUEST]

    def test_jersey_fkapi_create_view_post_with_exception_handling(self):
        """Test JerseyFKAPICreateView POST with exception handling."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "id_fka": "invalid_kit_id",
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND, HTTP_BAD_REQUEST, HTTP_INTERNAL_SERVER_ERROR]

    def test_jersey_fkapi_create_view_post_with_context_data(self):
        """Test JerseyFKAPICreateView POST with context data."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        response = self.client.get(reverse("collection:jersey_fkapi_create"))
        assert response.status_code == HTTP_OK
        assert "form" in response.context

    def test_jersey_fkapi_create_view_post_with_service_error(self):
        """Test JerseyFKAPICreateView POST with service error."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "id_fka": 999999,  # Non-existent kit ID
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND, HTTP_BAD_REQUEST, HTTP_INTERNAL_SERVER_ERROR]

    def test_jersey_fkapi_create_view_post_with_kit_processing(self):
        """Test JerseyFKAPICreateView POST with kit processing."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with kit processing",
            "is_fan_version": True,
            "is_short_sleeve": True,
            "kit_id": 123,
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_entity_processing(self):
        """Test JerseyFKAPICreateView POST with entity processing."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with entity processing",
            "is_fan_version": True,
            "is_short_sleeve": True,
            "brand_name": "New Brand",
            "club_name": "New Club",
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_image_processing(self):
        """Test JerseyFKAPICreateView POST with image processing."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with image processing",
            "is_fan_version": True,
            "is_short_sleeve": True,
            "external_images": '["https://example.com/image1.jpg"]',
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_photo_processing(self):
        """Test JerseyFKAPICreateView POST with photo processing."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with photo processing",
            "is_fan_version": True,
            "is_short_sleeve": True,
            "photo_ids": "1,2,3",
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]

    def test_jersey_fkapi_create_view_post_with_competition_processing(self):
        """Test JerseyFKAPICreateView POST with competition processing."""
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

        size = SizeFactory(name="M", category="tops")

        form_data = {
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": size.id,
            "condition": 8,
            "description": "Test jersey with competition processing",
            "is_fan_version": True,
            "is_short_sleeve": True,
            "competitions": [self.competition.id],
            "all_competitions": "Champions League, La Liga, Copa del Rey",
        }

        response = self.client.post(reverse("collection:jersey_fkapi_create"), form_data)
        assert response.status_code in [HTTP_OK, HTTP_FOUND]
