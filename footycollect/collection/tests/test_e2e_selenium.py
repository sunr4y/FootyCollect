"""
End-to-end tests using Selenium for browser simulation.

These tests require selenium and a webdriver (Chrome/Firefox).
Install with: pip install selenium

For CI/CD: Uses selenium/standalone-chrome Docker service in GitHub Actions.
For local development: Install Chrome/Chromium and chromedriver, or use chromedriver-binary.

To run tests in visible mode (non-headless) for debugging:
    SELENIUM_HEADLESS=false pytest footycollect/collection/tests/test_e2e_selenium.py -v

By default, tests run in headless mode. Set SELENIUM_HEADLESS=false to see the browser.

The tests automatically detect if SELENIUM_URL is set (CI environment) and use Remote WebDriver,
otherwise they fall back to local Chrome/Firefox driver for local development.
"""

import logging
import os
import socket
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import Client, override_settings

from footycollect.collection.models import BaseItem, Brand, Club, Color, Jersey, Season, Size
from footycollect.core.models import Competition

logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

try:
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select, WebDriverWait

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    WebDriverException = Exception

HEADLESS_MODE = os.environ.get("SELENIUM_HEADLESS", "true").lower() == "true"

User = get_user_model()
TEST_PASSWORD = "testpass123"

pytestmark = pytest.mark.skipif(not SELENIUM_AVAILABLE, reason="Selenium not installed")


@override_settings(DEBUG=True)
class TestE2ESeleniumTests(StaticLiveServerTestCase):
    """End-to-end tests using Selenium for real browser simulation."""

    @classmethod
    def setUpClass(cls):
        """Set up Selenium WebDriver."""

        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            cls.host = socket.gethostbyname(socket.gethostname())
        else:
            cls.host = "localhost"
        super().setUpClass()
        if SELENIUM_AVAILABLE:
            chrome_options = ChromeOptions()
            if HEADLESS_MODE or os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
            chrome_options.add_experimental_option("useAutomationExtension", False)

            selenium_url = os.getenv("SELENIUM_URL")

            if selenium_url:
                cls.selenium = cls._create_remote_webdriver(selenium_url, chrome_options)
            else:
                cls.selenium = cls._create_local_webdriver(chrome_options)

            cls.selenium.set_page_load_timeout(30)
            cls.selenium.implicitly_wait(5)

    @classmethod
    def _create_remote_webdriver(cls, selenium_url, chrome_options):
        """Create remote WebDriver for Selenium Grid."""
        try:
            return webdriver.Remote(
                command_executor=selenium_url,
                options=chrome_options,
            )
        except Exception as e:
            pytest.skip(f"Could not connect to Selenium Grid at {selenium_url}: {e}")

    @classmethod
    def _create_local_webdriver(cls, chrome_options):
        """Create local WebDriver, trying Chrome first, then Firefox."""
        driver = cls._try_chrome_webdriver(chrome_options)
        if driver:
            return driver
        driver = cls._try_chrome_with_service(chrome_options)
        if driver:
            return driver
        driver = cls._try_firefox_webdriver()
        if driver:
            return driver
        pytest.skip("No webdriver available")

    @classmethod
    def _try_chrome_webdriver(cls, chrome_options):
        """Try to create Chrome WebDriver."""
        try:
            return webdriver.Chrome(options=chrome_options)
        except Exception:
            return None

    @classmethod
    def _try_chrome_with_service(cls, chrome_options):
        """Try to create Chrome WebDriver with Service."""
        try:
            from selenium.webdriver.chrome.service import Service

            service = Service()
            service.service_args = ["--silent", "--log-level=OFF"]
            return webdriver.Chrome(service=service, options=chrome_options)
        except WebDriverException:
            logging.debug("Failed to create Chrome WebDriver with Service", exc_info=True)
            return None

    @classmethod
    def _try_firefox_webdriver(cls):
        """Try to create Firefox WebDriver."""
        try:
            from selenium.webdriver.firefox.options import Options as FirefoxOptions

            firefox_options = FirefoxOptions()
            if HEADLESS_MODE or os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                firefox_options.add_argument("--headless")
            return webdriver.Firefox(options=firefox_options)
        except WebDriverException:
            logging.debug("Failed to create Firefox WebDriver", exc_info=True)
            return None

    @classmethod
    def tearDownClass(cls):
        """Close Selenium WebDriver."""
        if SELENIUM_AVAILABLE and hasattr(cls, "selenium"):
            try:
                cls.selenium.quit()
            except WebDriverException:
                logging.exception("Failed to quit WebDriver")
        super().tearDownClass()

    def tearDown(self):
        """Capture screenshot on test failure (only in visible mode)."""
        if SELENIUM_AVAILABLE and hasattr(self, "selenium") and not HEADLESS_MODE:
            if hasattr(self, "_outcome") and self._outcome and not self._outcome.success:
                try:
                    Path("test_screenshots").mkdir(parents=True, exist_ok=True)
                    screenshot_path = f"test_screenshots/{self._testMethodName}_failure.png"
                    self.selenium.save_screenshot(screenshot_path)
                except WebDriverException:
                    logging.exception("Failed to save screenshot")
        super().tearDown()

    def setUp(self):
        """Set up test data."""
        if SELENIUM_AVAILABLE and hasattr(self, "selenium"):
            try:
                self.selenium.get(self.live_server_url)
                self.selenium.delete_all_cookies()
                self.selenium.execute_script("window.localStorage.clear();")
            except WebDriverException:
                logging.debug("Could not clear browser state", exc_info=True)

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )

        self.brand = Brand.objects.create(name="Nike", slug="nike")
        self.club = Club.objects.create(name="Barcelona", slug="barcelona", country="ES")
        self.season = Season.objects.create(year="2023-24", first_year="2023", second_year="24")
        self.size = Size.objects.create(name="M", category="tops")
        self.color_red = Color.objects.create(name="RED", hex_value="#FF0000")
        self.color_blue = Color.objects.create(name="BLUE", hex_value="#0000FF")
        self.competition = Competition.objects.create(name="La Liga", slug="la-liga")

    def _login_user(self):
        """Helper to authenticate user using Django session cookies (faster than form login)."""
        client = Client()
        client.force_login(self.user)

        session_cookie = client.cookies.get(settings.SESSION_COOKIE_NAME)
        if session_cookie:
            self.selenium.get(self.live_server_url)
            self.selenium.add_cookie(
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": session_cookie.value,
                    "path": "/",
                },
            )

    def test_create_item_page_loads_without_errors(self):
        """Test that the item creation page loads without JavaScript errors."""
        if not SELENIUM_AVAILABLE:
            pytest.skip("Selenium not available")

        self._login_user()

        url = f"{self.live_server_url}/collection/jersey/create/automatic/"
        self.selenium.get(url)

        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body")),
        )

        page_source = self.selenium.page_source.lower()
        self.assertNotIn("traceback", page_source)
        self.assertNotIn("django exception", page_source)
        self.assertNotIn("server error", page_source)
        self.assertNotIn("internal server error", page_source)

        try:
            console_logs = self.selenium.get_log("browser")
            severe_logs = [log for log in console_logs if log["level"] == "SEVERE"]
            errors = [
                log
                for log in severe_logs
                if not (
                    log.get("source") == "network"
                    or "Failed to load resource" in log.get("message", "")
                    or "ERR_NAME_NOT_RESOLVED" in log.get("message", "")
                    or "media.testserver" in log.get("message", "")
                    or "Cross-Origin-Opener-Policy" in log.get("message", "")
                    or "untrustworthy" in log.get("message", "").lower()
                )
            ]
            self.assertEqual(len(errors), 0, f"JavaScript errors found: {errors}")
        except WebDriverException:
            logging.warning("Could not retrieve browser console logs", exc_info=True)

    @patch("footycollect.api.client.FKAPIClient.get_kit_details")
    @patch("footycollect.api.client.FKAPIClient.search_kits")
    def test_create_item_form_submission(self, mock_search_kits, mock_get_kit_details):
        """Test submitting the item creation form through the browser."""
        if not SELENIUM_AVAILABLE:
            pytest.skip("Selenium not available")

        mock_search_result = [
            {
                "id": 12345,
                "name": "Real Madrid Castilla 2023-24 Home",
                "slug": "real-madrid-castilla-2023-24-home-kit",
                "team": {
                    "name": "Real Madrid Castilla",
                },
                "season": {
                    "year": "2023-24",
                },
                "main_img_url": "https://cdn.footballkitarchive.com/2023/06/14/PlusudOvMM3EbPj.jpg",
            },
        ]
        mock_search_kits.return_value = mock_search_result

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

        self._login_user()

        url = f"{self.live_server_url}/collection/jersey/create/automatic/"
        self.selenium.get(url)

        WebDriverWait(self.selenium, 15).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete",
        )

        WebDriverWait(self.selenium, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "form")),
        )

        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.ID, "id_kit_search")),
        )

        kit_search_input = self.selenium.find_element(By.ID, "id_kit_search")
        kit_search_input.clear()
        kit_search_input.send_keys("Real Madrid")

        kit_result_item = WebDriverWait(self.selenium, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".kit-search-item")),
        )
        kit_result_item.click()

        WebDriverWait(self.selenium, 10).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete",
        )

        try:
            name_input = WebDriverWait(self.selenium, 5).until(
                EC.presence_of_element_located((By.NAME, "name")),
            )
            name_input.clear()
            name_input.send_keys("Selenium Test Jersey")
        except WebDriverException:
            logging.debug("Could not find or interact with name input", exc_info=True)

        try:
            description_input = WebDriverWait(self.selenium, 5).until(
                EC.presence_of_element_located((By.NAME, "description")),
            )
            description_input.clear()
            description_input.send_keys("Test description from Selenium")
        except WebDriverException:
            logging.debug("Could not find or interact with description input", exc_info=True)

        size_select = WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.NAME, "size")),
        )
        size_dropdown = Select(size_select)
        size_dropdown.select_by_value(str(self.size.id))

        submit_button = WebDriverWait(self.selenium, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]')),
        )

        self.selenium.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)

        WebDriverWait(self.selenium, 1).until(
            lambda driver: driver.execute_script(
                "return document.querySelector('[name=\"size\"]').value;",
            )
            == str(self.size.id),
        )

        try:
            submit_button.click()
        except WebDriverException:
            self.selenium.execute_script("arguments[0].click();", submit_button)

        WebDriverWait(self.selenium, 20).until(
            lambda driver: (
                "detail" in driver.current_url or "items" in driver.current_url or driver.current_url.endswith("/")
            ),
        )

        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete",
        )

        page_source = self.selenium.page_source.lower()

        self.assertNotIn("traceback", page_source)
        self.assertNotIn("django exception", page_source)
        self.assertNotIn("server error", page_source)
        self.assertNotIn("internal server error", page_source)

        item = BaseItem.objects.filter(user=self.user).order_by("-id").first()
        self.assertIsNotNone(item, "Item should be created in database after form submission")
        self.assertFalse(item.is_draft, "Item should not be a draft")

        jersey = Jersey.objects.filter(base_item=item).first()
        self.assertIsNotNone(jersey, "Jersey should be created")
        self.assertIsNotNone(jersey.size, "Jersey size should be saved")
        expected_msg = (
            f"Jersey size should be {self.size.name} (ID: {self.size.id}), "
            f"got {jersey.size.name if jersey.size else 'None'} "
            f"(ID: {jersey.size.id if jersey.size else 'None'})"
        )
        self.assertEqual(jersey.size.id, self.size.id, expected_msg)

    def test_item_detail_page_renders_correctly(self):
        """Test that item detail page renders all attributes correctly."""
        if not SELENIUM_AVAILABLE:
            pytest.skip("Selenium not available")

        item = BaseItem.objects.create(
            user=self.user,
            name="Selenium Detail Test",
            description="Testing detail page with Selenium",
            brand=self.brand,
            club=self.club,
            season=self.season,
            main_color=self.color_red,
            condition=10,
            detailed_condition="EXCELLENT",
            design="PLAIN",
        )
        item.secondary_colors.add(self.color_blue)
        Jersey.objects.create(base_item=item, size=self.size)

        self._login_user()

        url = f"{self.live_server_url}/collection/items/{item.id}/"
        self.selenium.get(url)

        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body")),
        )

        current_url = self.selenium.current_url
        if "login" in current_url.lower():
            self.fail(f"Redirected to login page. Current URL: {current_url}")

        page_source = self.selenium.page_source
        self.assertIn(item.name, page_source)
        self.assertIn(self.brand.name, page_source)
        self.assertIn(self.club.name, page_source)
        self.assertIn(self.season.year, page_source)

        try:
            console_logs = self.selenium.get_log("browser")
            severe_logs = [log for log in console_logs if log["level"] == "SEVERE"]
            errors = [
                log
                for log in severe_logs
                if not (
                    log.get("source") == "network"
                    or "Failed to load resource" in log.get("message", "")
                    or "ERR_NAME_NOT_RESOLVED" in log.get("message", "")
                    or "media.testserver" in log.get("message", "")
                    or "Cross-Origin-Opener-Policy" in log.get("message", "")
                    or "untrustworthy" in log.get("message", "").lower()
                )
            ]
            self.assertEqual(len(errors), 0, f"JavaScript errors found: {errors}")
        except WebDriverException:
            logging.warning("Could not retrieve browser console logs", exc_info=True)
