from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from footycollect.collection.factories import KitFactory
from footycollect.collection.views.jersey.mixins.kit_data_processing_mixin import KitDataProcessingMixin

EXPECTED_COMPETITION_LOGOS_COUNT = 2


class TestKitDataProcessingMixin(TestCase):
    def setUp(self):
        class TestView(KitDataProcessingMixin):
            def __init__(self):
                # Deliberately avoid super() to keep it simple
                self.request = RequestFactory().get("/")

        self.view = TestView()

    def test_fetch_kit_data_from_api_none_logs_and_adds_message(self):
        with (
            patch(
                "footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.FKAPIClient",
            ) as mock_client_cls,
            patch(
                "footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.messages.warning",
            ) as mock_warning,
        ):
            mock_client = mock_client_cls.return_value
            mock_client.get_kit_details.return_value = None

            result = self.view._fetch_kit_data_from_api("123")

            assert result is None
            mock_client.get_kit_details.assert_called_once_with("123")
            mock_warning.assert_called_once()

    def test_extract_brand_and_team_and_competition_data_populates_fkapi_data(self):
        self.view.fkapi_data = {}
        self.view.form = MagicMock()
        self.view.form.data = {}

        kit_data = {
            "brand": {
                "logo": "https://example.com/brand.png",
                "logo_dark": "https://example.com/brand-dark.png",
            },
            "team": {
                "logo": "https://example.com/team.png",
                "country": "ES",
            },
            "competition": [
                {"logo": "https://example.com/comp1.png"},
                {"logo": "https://example.com/comp2.png"},
            ],
        }

        self.view._extract_logo_data_from_kit(kit_data)

        assert self.view.fkapi_data["brand_logo"] == "https://example.com/brand.png"
        assert self.view.fkapi_data["brand_logo_dark"] == "https://example.com/brand-dark.png"
        assert self.view.fkapi_data["team_logo"] == "https://example.com/team.png"
        assert self.view.fkapi_data["team_country"] == "ES"
        assert "competition_logos" in self.view.fkapi_data
        assert len(self.view.fkapi_data["competition_logos"]) == EXPECTED_COMPETITION_LOGOS_COUNT

        assert self.view.form.data["country_code"] == "ES"

    def test_extract_team_data_without_team_logs_warning(self):
        with patch(
            "footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.logger",
        ) as mock_logger:
            self.view._extract_team_data({})
            mock_logger.warning.assert_called_once()

    def test_find_and_assign_existing_kit_sets_kit_and_related_entities(self):
        form = MagicMock()
        form.instance = MagicMock()
        form.cleaned_data = {
            "competitions": [],
            "competition_name": "",
            "competition_names": [],
        }

        kit = KitFactory(id_fka=123)

        with patch.object(self.view, "_assign_existing_kit") as mock_assign:
            self.view._find_and_assign_existing_kit(form, 123)

        mock_assign.assert_called_once_with(form, kit, 123)

    def test_assign_existing_kit_populates_form_and_view_state(self):
        form = MagicMock()
        form.instance = MagicMock()
        form.cleaned_data = {
            "competitions": [],
            "competition_name": "",
            "competition_names": [],
        }

        kit = KitFactory()

        with (
            patch.object(self.view, "_log_kit_debug_info"),
            patch.object(self.view, "_assign_kit_entities") as mock_entities,
            patch.object(self.view, "_assign_kit_competitions") as mock_comps,
        ):
            self.view._assign_existing_kit(form, kit, "KIT999")

        assert form.instance.kit == kit
        assert self.view.kit == kit
        mock_entities.assert_called_once_with(form, kit)
        mock_comps.assert_called_once_with(form, kit)
