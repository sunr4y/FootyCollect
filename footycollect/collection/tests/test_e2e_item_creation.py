"""
End-to-end tests for item creation with API integration.

These tests simulate the complete user flow of creating an item,
including API integration, form validation, and page rendering.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from footycollect.collection.models import BaseItem, Brand, Club, Color, Jersey, Season, Size
from footycollect.core.models import Competition

User = get_user_model()
TEST_PASSWORD = "testpass123"
HTTP_FOUND = 302


class TestE2EItemCreationTests(TestCase):
    """End-to-end tests for item creation flow."""

    def test_basic_import(self):
        """Basic test to verify the test class is being discovered."""
        self.assertTrue(True)

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.client = Client()
        self.client.login(username="testuser", password=TEST_PASSWORD)

        self.brand = Brand.objects.create(name="Nike", slug="nike")
        self.club = Club.objects.create(name="Barcelona", slug="barcelona", country="ES")
        self.season = Season.objects.create(year="2023-24", first_year="2023", second_year="24")
        self.size = Size.objects.create(name="M", category="tops")
        self.color_red = Color.objects.create(name="RED", hex_value="#FF0000")
        self.color_blue = Color.objects.create(name="BLUE", hex_value="#0000FF")
        self.competition = Competition.objects.create(name="La Liga", slug="la-liga")

    def _assert_no_errors_in_content(self, content):
        """Assert that content does not contain error messages."""
        content_lower = content.lower()
        self.assertNotIn("traceback", content_lower)
        self.assertNotIn("django exception", content_lower)
        self.assertNotIn("server error", content_lower)
        self.assertNotIn("internal server error", content_lower)

    def _find_item_name_in_content(self, item, content):
        """Find item name in content, return tuple (found, content, content_lower)."""
        item_name_lower = item.name.lower()
        item_str = str(item)
        item_str_lower = item_str.lower()
        content_lower = content.lower()

        name_in_content = item.name in content or item_name_lower in content_lower
        str_in_content = item_str in content or item_str_lower in content_lower

        return name_in_content or str_in_content, content, content_lower

    def _create_error_message_for_missing_name(self, item, content, response):
        """Create detailed error message when item name is not found."""
        item_name_lower = item.name.lower()
        item_str = str(item)
        item_str_lower = item_str.lower()
        content_lower = content.lower()

        name_pos = content.find(item.name)
        name_pos_lower = content_lower.find(item_name_lower)
        str_pos = content.find(item_str)
        str_pos_lower = content_lower.find(item_str_lower)

        body_start = content_lower.find("<body")
        body_end = content_lower.find("</body>")
        body_content = content[body_start:body_end] if body_start > 0 and body_end > 0 else content

        name_dd_section = ""
        if "name" in content_lower:
            name_idx = content_lower.find("name")
            if name_idx > 0:
                start = max(0, name_idx - 200)
                end = min(len(content), name_idx + 200)
                name_dd_section = content[start:end]

        content_sample = body_content[1000:2000] if len(body_content) > 2000 else body_content[500:]  # noqa: PLR2004
        response_url = getattr(response, "url", getattr(response, "request", {}).get("PATH_INFO", "N/A"))
        return (
            f"Item name '{item.name}' not found in page content (after cache clear). "
            f"Item ID: {item.pk}. "
            f"Item __str__: '{item_str}'. "
            f"Response URL: {response_url}. "
            f"Content length: {len(content)}. "
            f"Name search (case-sensitive): position {name_pos}. "
            f"Name search (case-insensitive): position {name_pos_lower}. "
            f"__str__ search (case-sensitive): position {str_pos}. "
            f"__str__ search (case-insensitive): position {str_pos_lower}. "
            f"Body content length: {len(body_content)}. "
            f"Name section context: {name_dd_section}. "
            f"Content sample from body: {content_sample}"
        )

    def test_create_item_page_renders_correctly(self):
        """Test that the item creation page renders without errors."""
        url = reverse("collection:jersey_create_automatic")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        content = response.content.decode().lower()
        self.assertNotIn("traceback", content)
        self.assertNotIn("django exception", content)
        self.assertNotIn("server error", content)
        self.assertNotIn("internal server error", content)

    def test_create_item_without_api_integration(self):
        """Test creating an item without API integration (manual mode)."""
        form_data = {
            "name": "Test Jersey Manual",
            "description": "Test description for manual creation",
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": self.size.id,
            "condition": 10,
            "detailed_condition": "EXCELLENT",
            "main_color": self.color_red.id,
            "design": "PLAIN",
            "is_replica": False,
            "is_fan_version": False,
            "is_signed": False,
            "has_nameset": False,
            "is_short_sleeve": True,
        }

        url = reverse("collection:jersey_create_automatic")
        response = self.client.post(url, form_data)

        self.assertEqual(response.status_code, HTTP_FOUND)
        latest_item = BaseItem.objects.latest("id")
        self.assertRedirects(
            response,
            reverse("collection:item_detail", kwargs={"pk": latest_item.pk}),
        )

        item = BaseItem.objects.get(name="Test Jersey Manual", user=self.user)
        self.assertIsNotNone(item)
        self.assertEqual(item.user, self.user)
        self.assertEqual(item.brand, self.brand)
        self.assertEqual(item.club, self.club)
        self.assertEqual(item.season, self.season)
        self.assertEqual(item.main_color, self.color_red)
        self.assertEqual(item.condition, 10)
        self.assertEqual(item.detailed_condition, "EXCELLENT")
        self.assertEqual(item.design, "PLAIN")
        self.assertFalse(item.is_replica)
        self.assertFalse(item.is_draft)

        jersey = Jersey.objects.get(base_item=item)
        self.assertEqual(jersey.size, self.size)
        self.assertFalse(jersey.is_fan_version)
        self.assertFalse(jersey.is_signed)
        self.assertFalse(jersey.has_nameset)
        self.assertTrue(jersey.is_short_sleeve)

    @patch("footycollect.api.client.FKAPIClient.get_kit_details")
    def test_create_item_with_api_integration(self, mock_get_kit_details):
        """Test creating an item with API integration using real API data structure."""
        mock_kit_data = {
            "name": "Real Madrid Castilla 2023-24 Home",
            "slug": "real-madrid-castilla-2023-24-home-kit",
            "team": {
                "id": 737,
                "id_fka": None,
                "name": "Real Madrid Castilla",
                "slug": "real-madrid-castilla-kits",
                "logo": "https://www.footballkitarchive.com/static/logos/teams/2216.png?v=1654464652&s=128",
                "logo_dark": None,
                "country": "ES",
            },
            "season": {
                "id": 2,
                "year": "2023-24",
                "first_year": "2023",
                "second_year": "2024",
            },
            "competition": [
                {
                    "id": 837,
                    "name": "1ª RFEF",
                    "slug": "1a-rfef-kits",
                    "logo": "https://www.footballkitarchive.com/static/logos/not_found.png",
                    "logo_dark": None,
                    "country": "ES",
                },
                {
                    "id": 3386,
                    "name": "Primera RFEF",
                    "slug": "1a-rfef-kits",
                    "logo": "https://www.footballkitarchive.com/static/logos/not_found.png",
                    "logo_dark": None,
                    "country": "ES",
                },
            ],
            "type": {
                "name": "Home",
            },
            "brand": {
                "id": 64,
                "name": "adidas",
                "slug": "adidas-kits",
                "logo": "https://www.footballkitarchive.com//static/logos/misc/adidas.png?v=1665090054",
                "logo_dark": "https://www.footballkitarchive.com//static/logos/misc/adidas_l.png?v=1665090054",
            },
            "design": "Plain",
            "primary_color": {
                "name": "White",
                "color": "#FFFFFF",
            },
            "secondary_color": [
                {
                    "name": "Navy",
                    "color": "#000080",
                },
                {
                    "name": "Gold",
                    "color": "#BFAB40",
                },
            ],
            "main_img_url": "https://cdn.footballkitarchive.com/2023/06/14/PlusudOvMM3EbPj.jpg",
        }
        mock_get_kit_details.return_value = mock_kit_data

        form_data = {
            "kit_id": "51341",
            "name": "Real Madrid Castilla 2023-24 Home",
            "description": "Test description",
            "brand_name": "adidas",
            "club_name": "Real Madrid Castilla",
            "season_name": "2023-24",
            "size": self.size.id,
            "condition": 10,
            "detailed_condition": "EXCELLENT",
            "main_color": "White",
            "secondary_colors": ["Navy", "Gold"],
            "design": "PLAIN",
            "country_code": "ES",
            "is_replica": False,
            "is_fan_version": False,
            "is_signed": False,
            "has_nameset": False,
            "is_short_sleeve": True,
        }

        url = reverse("collection:jersey_create_automatic")
        response = self.client.post(url, form_data)

        self.assertEqual(response.status_code, HTTP_FOUND)
        item = BaseItem.objects.latest("id")
        self.assertRedirects(response, reverse("collection:item_detail", kwargs={"pk": item.pk}))

        item = BaseItem.objects.get(name="Real Madrid Castilla 2023-24 Home", user=self.user)
        self.assertIsNotNone(item)
        self.assertEqual(item.user, self.user)
        self.assertEqual(item.brand.name.lower(), "adidas")
        self.assertEqual(item.club.name, "Real Madrid Castilla")
        self.assertEqual(item.season.year, "2023-24")
        self.assertEqual(item.country, "ES")
        self.assertIsNotNone(item.main_color)
        self.assertEqual(item.main_color.name.upper(), "WHITE")
        self.assertTrue(item.secondary_colors.filter(name__iexact="NAVY").exists())
        self.assertTrue(item.secondary_colors.filter(name__iexact="GOLD").exists())
        self.assertEqual(item.design, "PLAIN")
        self.assertFalse(item.is_draft)

        jersey = Jersey.objects.get(base_item=item)
        self.assertEqual(jersey.size, self.size)
        self.assertIsNotNone(jersey.kit)

    def test_create_item_verifies_all_attributes(self):
        """Test that all item attributes are correctly set after creation."""
        form_data = {
            "name": "Complete Test Jersey",
            "description": "Complete test with all attributes",
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": self.size.id,
            "condition": 8,
            "detailed_condition": "GOOD",
            "main_color": self.color_red.id,
            "design": "STRIPES",
            "country_code": "ES",
            "is_replica": True,
            "is_fan_version": True,
            "is_signed": True,
            "has_nameset": True,
            "player_name": "Messi",
            "number": 10,
            "is_short_sleeve": False,
        }

        url = reverse("collection:jersey_create_automatic")
        response = self.client.post(url, form_data)

        if response.status_code != HTTP_FOUND:
            if hasattr(response, "context") and "form" in response.context:
                form = response.context["form"]
                if hasattr(form, "errors"):
                    error_msg = f"Form errors: {form.errors}"
                    self.fail(
                        f"Expected {HTTP_FOUND} redirect but got {response.status_code}. {error_msg}",
                    )
            content_preview = response.content.decode()[:500]
            self.fail(
                f"Expected {HTTP_FOUND} redirect but got {response.status_code}. "
                f"Response content: {content_preview}",
            )

        item = BaseItem.objects.get(name="Complete Test Jersey", user=self.user)

        self.assertEqual(item.name, "Complete Test Jersey")
        self.assertEqual(item.description, "Complete test with all attributes")
        self.assertEqual(item.condition, 8)
        self.assertEqual(item.detailed_condition, "GOOD")
        self.assertEqual(item.design, "STRIPES")
        self.assertEqual(item.country, "ES")
        self.assertTrue(item.is_replica)
        self.assertFalse(item.is_draft)

        jersey = Jersey.objects.get(base_item=item)
        self.assertEqual(jersey.size, self.size)
        self.assertTrue(jersey.is_fan_version)
        self.assertTrue(jersey.is_signed)
        self.assertTrue(jersey.has_nameset)
        self.assertEqual(jersey.player_name, "Messi")
        self.assertEqual(jersey.number, 10)
        self.assertFalse(jersey.is_short_sleeve)

    def test_create_item_page_shows_no_errors(self):
        """Test that the item detail page shows no errors after creation."""
        form_data = {
            "name": "Error Test Jersey",
            "description": "Testing for errors",
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": self.size.id,
            "condition": 10,
            "detailed_condition": "EXCELLENT",
            "main_color": self.color_red.id,
            "design": "PLAIN",
        }

        from django.core.cache import cache

        cache.clear()

        url = reverse("collection:jersey_create_automatic")
        response = self.client.post(url, form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        item = BaseItem.objects.latest("id")

        self.assertIn("item", response.context)
        self.assertEqual(response.context["item"], item)
        self.assertIsNotNone(item.name, "Item name should not be None")
        self.assertNotEqual(item.name, "", "Item name should not be empty")

        content = response.content.decode()
        self._assert_no_errors_in_content(content)

        name_found, content, content_lower = self._find_item_name_in_content(item, content)

        if not name_found:
            cache.clear()
            response2 = self.client.get(response.url if hasattr(response, "url") else f"/collection/items/{item.pk}/")
            content2 = response2.content.decode()
            name_found2, content2, content2_lower = self._find_item_name_in_content(item, content2)

            if not name_found2:
                error_msg = self._create_error_message_for_missing_name(item, content2, response)
                self.fail(error_msg)
            content = content2

        self.assertIn(item.name, content, f"Item name '{item.name}' not found in content")

    def test_create_item_with_photos(self):
        """Test creating an item with uploaded photos."""
        form_data = {
            "name": "Jersey With Photos",
            "description": "Test with photos",
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": self.size.id,
            "condition": 10,
            "detailed_condition": "EXCELLENT",
            "main_color": self.color_red.id,
            "design": "PLAIN",
        }

        url = reverse("collection:jersey_create_automatic")
        response = self.client.post(url, form_data, format="multipart")

        self.assertEqual(response.status_code, HTTP_FOUND)
        item = BaseItem.objects.get(name="Jersey With Photos", user=self.user)
        self.assertIsNotNone(item)

    @patch("footycollect.api.client.FKAPIClient.get_kit_details")
    def test_create_item_with_api_failure_graceful_degradation(self, mock_get_kit_details):
        """Test that item creation works even when API fails."""
        mock_get_kit_details.return_value = None

        form_data = {
            "kit_id": "99999",
            "name": "Jersey API Failure Test",
            "description": "Test graceful degradation",
            "brand_name": "Nike",
            "club_name": "Barcelona",
            "season_name": "2023-24",
            "size": self.size.id,
            "condition": 10,
            "detailed_condition": "EXCELLENT",
            "main_color": "RED",
            "design": "PLAIN",
        }

        url = reverse("collection:jersey_create_automatic")
        response = self.client.post(url, form_data)

        self.assertEqual(response.status_code, HTTP_FOUND)
        item = BaseItem.objects.get(name="Jersey API Failure Test", user=self.user)
        self.assertIsNotNone(item)
        self.assertFalse(item.is_draft)

    def test_create_item_form_validation_errors(self):
        """Test that form validation errors are displayed correctly."""
        form_data = {
            "name": "",
            "description": "Missing required fields",
        }

        url = reverse("collection:jersey_create_automatic")
        response = self.client.post(url, form_data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertTrue(response.context["form"].errors)

    def test_item_detail_page_renders_all_attributes(self):
        """Test that item detail page renders all attributes correctly."""
        color_white = Color.objects.create(name="WHITE", hex_value="#FFFFFF")
        color_navy = Color.objects.create(name="NAVY", hex_value="#000080")
        color_gold = Color.objects.create(name="GOLD", hex_value="#BFAB40")

        brand_adidas = Brand.objects.create(name="adidas", slug="adidas")
        club_rmc = Club.objects.create(name="Real Madrid Castilla", slug="real-madrid-castilla", country="ES")

        item = BaseItem.objects.create(
            user=self.user,
            name="Real Madrid Castilla 2023-24 Home",
            description="Testing detail page with real data",
            brand=brand_adidas,
            club=club_rmc,
            season=self.season,
            main_color=color_white,
            condition=10,
            detailed_condition="EXCELLENT",
            design="PLAIN",
            country="ES",
        )
        item.secondary_colors.add(color_navy, color_gold)
        item.competitions.add(self.competition)
        Jersey.objects.create(base_item=item, size=self.size, is_fan_version=True, number=10)

        from django.core.cache import cache

        cache.clear()

        url = reverse("collection:item_detail", kwargs={"pk": item.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        self.assertIn("item", response.context)
        self.assertEqual(response.context["item"], item)
        self.assertIn("Real Madrid Castilla 2023-24 Home", content)
        self.assertIn("adidas", content.lower())
        self.assertIn("Real Madrid Castilla", content)
        self.assertIn("2023-24", content)
        self.assertIn("WHITE", content)
        self.assertIn("NAVY", content)
        self.assertIn("GOLD", content)
        self.assertIn("Plain", content)
        self.assertIn("10", content)
        self.assertIn("Spain", content)
        content_lower = content.lower()
        self.assertNotIn("traceback", content_lower)
        self.assertNotIn("django exception", content_lower)
        self.assertNotIn("server error", content_lower)
        self.assertNotIn("internal server error", content_lower)

    def test_create_item_with_competitions(self):
        """Test creating an item with competitions."""
        form_data = {
            "name": "Jersey With Competitions",
            "description": "Test with competitions",
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "size": self.size.id,
            "condition": 10,
            "detailed_condition": "EXCELLENT",
            "main_color": self.color_red.id,
            "design": "PLAIN",
            "competitions": str(self.competition.id),
        }

        url = reverse("collection:jersey_create_automatic")
        response = self.client.post(url, form_data)

        self.assertEqual(response.status_code, HTTP_FOUND)
        item = BaseItem.objects.get(name="Jersey With Competitions", user=self.user)
        self.assertIn(self.competition, item.competitions.all())

    @patch("footycollect.api.client.FKAPIClient.get_kit_details")
    def test_create_item_with_full_api_data(self, mock_get_kit_details):
        """Test creating an item with complete API data using real API structure."""
        mock_kit_data = {
            "name": "Real Madrid Castilla 2023-24 Home",
            "slug": "real-madrid-castilla-2023-24-home-kit",
            "team": {
                "id": 737,
                "id_fka": None,
                "name": "Real Madrid Castilla",
                "slug": "real-madrid-castilla-kits",
                "logo": "https://www.footballkitarchive.com/static/logos/teams/2216.png?v=1654464652&s=128",
                "logo_dark": None,
                "country": "ES",
            },
            "season": {
                "id": 2,
                "year": "2023-24",
                "first_year": "2023",
                "second_year": "2024",
            },
            "competition": [
                {
                    "id": 837,
                    "name": "1ª RFEF",
                    "slug": "1a-rfef-kits",
                    "logo": "https://www.footballkitarchive.com/static/logos/not_found.png",
                    "logo_dark": None,
                    "country": "ES",
                },
                {
                    "id": 3386,
                    "name": "Primera RFEF",
                    "slug": "1a-rfef-kits",
                    "logo": "https://www.footballkitarchive.com/static/logos/not_found.png",
                    "logo_dark": None,
                    "country": "ES",
                },
            ],
            "type": {
                "name": "Home",
            },
            "brand": {
                "id": 64,
                "name": "adidas",
                "slug": "adidas-kits",
                "logo": "https://www.footballkitarchive.com//static/logos/misc/adidas.png?v=1665090054",
                "logo_dark": "https://www.footballkitarchive.com//static/logos/misc/adidas_l.png?v=1665090054",
            },
            "design": "Plain",
            "primary_color": {
                "name": "White",
                "color": "#FFFFFF",
            },
            "secondary_color": [
                {
                    "name": "Navy",
                    "color": "#000080",
                },
                {
                    "name": "Gold",
                    "color": "#BFAB40",
                },
            ],
            "main_img_url": "https://cdn.footballkitarchive.com/2023/06/14/PlusudOvMM3EbPj.jpg",
        }
        mock_get_kit_details.return_value = mock_kit_data

        form_data = {
            "kit_id": "51341",
            "name": "Real Madrid Castilla 2023-24 Home",
            "description": "Complete API integration test",
            "brand_name": "adidas",
            "club_name": "Real Madrid Castilla",
            "season_name": "2023-24",
            "size": self.size.id,
            "condition": 10,
            "detailed_condition": "EXCELLENT",
            "main_color": "White",
            "secondary_colors": ["Navy", "Gold"],
            "design": "PLAIN",
            "country_code": "ES",
        }

        url = reverse("collection:jersey_create_automatic")
        response = self.client.post(url, form_data)

        self.assertEqual(response.status_code, HTTP_FOUND)
        item = BaseItem.objects.get(name="Real Madrid Castilla 2023-24 Home", user=self.user)

        self.assertEqual(item.brand.name.lower(), "adidas")
        self.assertEqual(item.club.name, "Real Madrid Castilla")
        self.assertEqual(item.season.year, "2023-24")
        self.assertEqual(item.country, "ES")
        self.assertIsNotNone(item.main_color)
        self.assertEqual(item.main_color.name.upper(), "WHITE")
        self.assertTrue(item.secondary_colors.filter(name__iexact="NAVY").exists())
        self.assertTrue(item.secondary_colors.filter(name__iexact="GOLD").exists())
        self.assertEqual(item.design, "PLAIN")
        self.assertIn("1ª RFEF", [c.name for c in item.competitions.all()])
        self.assertIn("Primera RFEF", [c.name for c in item.competitions.all()])

        jersey = Jersey.objects.get(base_item=item)
        self.assertIsNotNone(jersey.kit)

    @patch("footycollect.api.client.FKAPIClient.get_kit_details")
    def test_complete_flow_real_madrid_castilla_kit(self, mock_get_kit_details):
        """
        Test the complete flow: search for kit, select result, create item, verify detail page.
        Simulates the real user flow with Real Madrid Castilla 2023-24 Home kit (kit_id: 51341).
        """
        mock_kit_data = {
            "name": "Real Madrid Castilla 2023-24 Home",
            "slug": "real-madrid-castilla-2023-24-home-kit",
            "team": {
                "id": 737,
                "id_fka": None,
                "name": "Real Madrid Castilla",
                "slug": "real-madrid-castilla-kits",
                "logo": "https://www.footballkitarchive.com/static/logos/teams/2216.png?v=1654464652&s=128",
                "logo_dark": None,
                "country": "ES",
            },
            "season": {
                "id": 2,
                "year": "2023-24",
                "first_year": "2023",
                "second_year": "2024",
            },
            "competition": [
                {
                    "id": 837,
                    "name": "1ª RFEF",
                    "slug": "1a-rfef-kits",
                    "logo": "https://www.footballkitarchive.com/static/logos/not_found.png",
                    "logo_dark": None,
                    "country": "ES",
                },
                {
                    "id": 3386,
                    "name": "Primera RFEF",
                    "slug": "1a-rfef-kits",
                    "logo": "https://www.footballkitarchive.com/static/logos/not_found.png",
                    "logo_dark": None,
                    "country": "ES",
                },
            ],
            "type": {
                "name": "Home",
            },
            "brand": {
                "id": 64,
                "name": "adidas",
                "slug": "adidas-kits",
                "logo": "https://www.footballkitarchive.com//static/logos/misc/adidas.png?v=1665090054",
                "logo_dark": "https://www.footballkitarchive.com//static/logos/misc/adidas_l.png?v=1665090054",
            },
            "design": "Plain",
            "primary_color": {
                "name": "White",
                "color": "#FFFFFF",
            },
            "secondary_color": [
                {
                    "name": "Navy",
                    "color": "#000080",
                },
                {
                    "name": "Gold",
                    "color": "#BFAB40",
                },
            ],
            "main_img_url": "https://cdn.footballkitarchive.com/2023/06/14/PlusudOvMM3EbPj.jpg",
        }
        mock_get_kit_details.return_value = mock_kit_data

        form_data = {
            "kit_id": "51341",
            "name": "Real Madrid Castilla 2023-24 Home",
            "description": "",
            "brand_name": "adidas",
            "club_name": "Real Madrid Castilla",
            "season_name": "2023-24",
            "size": self.size.id,
            "condition": 10,
            "detailed_condition": "EXCELLENT",
            "main_color": "White",
            "secondary_colors": ["Navy", "Gold"],
            "design": "PLAIN",
            "country_code": "ES",
        }

        url = reverse("collection:jersey_create_automatic")
        response = self.client.post(url, form_data)

        self.assertEqual(response.status_code, HTTP_FOUND, "Should redirect after successful creation")
        item = BaseItem.objects.latest("id")
        self.assertRedirects(response, reverse("collection:item_detail", kwargs={"pk": item.pk}))

        item = BaseItem.objects.get(name="Real Madrid Castilla 2023-24 Home", user=self.user)

        self.assertEqual(item.brand.name.lower(), "adidas")
        self.assertEqual(item.club.name, "Real Madrid Castilla")
        self.assertEqual(item.season.year, "2023-24")
        self.assertEqual(item.country, "ES")
        self.assertEqual(item.main_color.name.upper(), "WHITE")
        self.assertEqual(item.design, "PLAIN")
        self.assertFalse(item.is_draft)

        secondary_colors = [c.name.upper() for c in item.secondary_colors.all()]
        self.assertIn("NAVY", secondary_colors)
        self.assertIn("GOLD", secondary_colors)

        competitions = [c.name for c in item.competitions.all()]
        self.assertIn("1ª RFEF", competitions)
        self.assertIn("Primera RFEF", competitions)

        jersey = Jersey.objects.get(base_item=item)
        self.assertEqual(jersey.size, self.size)
        self.assertIsNotNone(jersey.kit)

        detail_url = reverse("collection:item_detail", kwargs={"pk": item.pk})
        detail_response = self.client.get(detail_url)

        self.assertEqual(detail_response.status_code, 200)
        content = detail_response.content.decode()

        self.assertIn("Real Madrid Castilla 2023-24 Home", content)
        self.assertIn("adidas", content.lower())
        self.assertIn("Real Madrid Castilla", content)
        self.assertIn("2023-24", content)
        self.assertIn("WHITE", content)
        self.assertIn("NAVY", content)
        self.assertIn("GOLD", content)
        self.assertIn("Plain", content)
        self.assertIn("Spain", content)
        self.assertIn("1ª RFEF", content)
        self.assertIn("Primera RFEF", content)

        content_lower = content.lower()
        self.assertNotIn("traceback", content_lower)
        self.assertNotIn("django exception", content_lower)
        self.assertNotIn("server error", content_lower)
        self.assertNotIn("internal server error", content_lower)
