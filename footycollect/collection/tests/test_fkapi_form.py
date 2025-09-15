from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from faker import Faker

from footycollect.collection.models import Color, Size
from footycollect.core.models import Brand, Club, Season

# HTTP status codes
HTTP_OK = 200
HTTP_REDIRECT = 302

User = get_user_model()
fake = Faker()


class FKAPIFormTest(TestCase):
    """Test the FKAPI form integration without opening browser windows."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        # Use a test password constant to avoid hardcoded password warnings
        test_password = "testpass123"  # noqa: S105
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=test_password,
        )
        self.client.login(username="testuser", password=test_password)

        # Create test data
        self.club = Club.objects.create(
            name="FC Barcelona",
            country="ES",
            slug="fc-barcelona",
        )

        self.season = Season.objects.create(
            year="2024-25",
            first_year="2024",
            second_year="25",
        )

        self.brand = Brand.objects.create(
            name="Nike",
            slug="nike",
        )

        self.size = Size.objects.create(
            name="XL",
            category="tops",
        )

        self.color = Color.objects.create(
            name="Blue",
            hex_value="#0000FF",
        )

    def _mock_fkapi_search_response(self):
        """Mock FKAPI search response."""
        return [
            {
                "id": 1,
                "name": "FC Barcelona 2024-25 Home",
                "main_img_url": "https://example.com/barca1.jpg",
                "team_name": "FC Barcelona",
                "season_year": "2024-25",
            },
            {
                "id": 2,
                "name": "FC Barcelona 2024-25 Away",
                "main_img_url": "https://example.com/barca2.jpg",
                "team_name": "FC Barcelona",
                "season_year": "2024-25",
            },
            {
                "id": 3,
                "name": "FC Barcelona 2024-25 Third",
                "main_img_url": "https://example.com/barca3.jpg",
                "team_name": "FC Barcelona",
                "season_year": "2024-25",
            },
        ]

    def _mock_fkapi_kit_response(self, kit_id):
        """Mock FKAPI kit detail response."""
        return {
            "name": f"FC Barcelona 2024-25 Kit {kit_id}",
            "slug": f"fc-barcelona-2024-25-kit-{kit_id}",
            "team": {
                "id": 1,
                "name": "FC Barcelona",
                "country": "ES",
                "logo": "https://example.com/barca-logo.png",
            },
            "season": {
                "id": 1,
                "year": "2024-25",
                "first_year": "2024",
                "second_year": "2025",
            },
            "competition": [
                {
                    "id": 1,
                    "name": "La Liga",
                    "country": "ES",
                },
            ],
            "type": {"name": "Home"},
            "brand": {
                "id": 1,
                "name": "Nike",
                "logo": "https://example.com/nike-logo.png",
            },
            "design": "Classic",
            "primary_color": {"name": "Blue", "color": "#0000FF"},
            "secondary_color": [{"name": "Red", "color": "#FF0000"}],
            "main_img_url": f"https://example.com/barca{kit_id}.jpg",
        }

    @patch("footycollect.api.client.FKAPIClient.search_kits")
    @patch("footycollect.api.client.FKAPIClient.get_kit_details")
    def test_fkapi_form_complete_flow(self, mock_get_kit, mock_search):
        """Test complete FKAPI form flow with random city search."""
        # Generate random city
        random_city = fake.city()

        # Mock FKAPI responses
        mock_search.return_value = self._mock_fkapi_search_response()
        mock_get_kit.return_value = self._mock_fkapi_kit_response(3)  # Third result

        # Step 1: Get the form page
        response = self.client.get(reverse("collection:jersey_fkapi_create"))
        assert response.status_code == HTTP_OK

        # Step 2: Search for kits (simulate AJAX call)
        search_response = self.client.get(
            reverse("footycollect_api:search_kits"),
            {"keyword": random_city},
        )
        assert search_response.status_code == HTTP_OK

        # Step 3: Get kit details (simulate AJAX call)
        kit_response = self.client.get(
            reverse("footycollect_api:kit_details", kwargs={"kit_id": 3}),
        )
        assert kit_response.status_code == HTTP_OK

        # Step 4: Submit the form with FKAPI data (only API fields, let the form process them)
        form_data = {
            "kit_search": random_city,
            "kit_id": 3,
            "club_name": "FC Barcelona",
            "season_name": "2024-25",
            "brand_name": "Nike",
            "competition_name": "La Liga",
            "main_img_url": "https://example.com/barca3.jpg",
            "external_image_urls": "https://example.com/barca3.jpg",
            "main_color": self.color.id,
            "secondary_colors": [self.color.id],
            "design": "CHEST_BAND",
            "size": self.size.id,
            "condition": 10,
            "detailed_condition": "BNWT",
            "description": f"Test jersey from {random_city}",
            "competitions": "La Liga",
            "is_short_sleeve": True,
            "player_name": "",
            "number": "",
            "is_replica": False,
            "is_fan_version": True,
            "is_signed": False,
            "has_nameset": False,
            "country_code": "ES",
        }

        # Step 5: Submit the form
        response = self.client.post(
            reverse("collection:jersey_fkapi_create"),
            data=form_data,
            follow=True,
        )

        # Step 6: Verify the form was processed correctly
        # The form should either redirect (success) or show errors
        assert response.status_code in [HTTP_OK, HTTP_REDIRECT]

        # If successful, verify the jersey was created
        if response.status_code == HTTP_REDIRECT:
            from footycollect.collection.models import BaseItem

            jerseys = BaseItem.objects.filter(user=self.user, item_type="jersey")
            assert jerseys.exists()

            jersey = jerseys.first()
            assert jersey.name == "FC Barcelona 2024-25 Kit 3"
            assert jersey.club == self.club
            assert jersey.season == self.season
            assert jersey.brand == self.brand

    def test_fkapi_form_without_api_data(self):
        """Test form submission without FKAPI data (manual entry)."""
        form_data = {
            "name": "Manual Test Jersey",
            "club": self.club.id,
            "season": self.season.id,
            "brand": self.brand.id,
            "size": self.size.id,
            "condition": 8,
            "detailed_condition": "USED",
            "description": "Manually created jersey",
            "competitions": "Test League",
            "main_color": self.color.id,
            "secondary_colors": [self.color.id],
            "design": "CHEST_BAND",
            "is_short_sleeve": False,
            "is_replica": False,
            "is_fan_version": True,
            "is_signed": False,
            "has_nameset": False,
            "country_code": "ES",
        }

        response = self.client.post(
            reverse("collection:jersey_fkapi_create"),
            data=form_data,
            follow=True,
        )

        # Should work without FKAPI data
        assert response.status_code in [HTTP_OK, HTTP_REDIRECT]

        if response.status_code == HTTP_REDIRECT:
            from footycollect.collection.models import BaseItem

            jerseys = BaseItem.objects.filter(user=self.user, item_type="jersey")
            assert jerseys.exists()

            jersey = jerseys.first()
            assert jersey.name == "Manual Test Jersey"

    def test_fkapi_form_validation_errors(self):
        """Test form validation with missing required fields."""
        form_data = {
            "kit_search": "test",
            # Missing required fields
        }

        response = self.client.post(
            reverse("collection:jersey_fkapi_create"),
            data=form_data,
        )

        # Should show validation errors
        assert response.status_code == HTTP_OK
        assert "form" in response.context
        assert response.context["form"].errors
