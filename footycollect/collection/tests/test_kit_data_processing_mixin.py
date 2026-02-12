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

    def test_process_kit_data_returns_early_when_fetch_returns_none(self):
        form = MagicMock()
        form.fkapi_data = MagicMock()
        with patch.object(self.view, "_fetch_kit_data_from_api", return_value=None):
            self.view._process_kit_data(form, "999")
        form.fkapi_data.update.assert_not_called()

    def test_process_kit_data_creates_fkapi_data_if_missing(self):
        form = MagicMock()
        form.fkapi_data = MagicMock()
        kit_data = {"brand": {}}
        with (
            patch.object(self.view, "_fetch_kit_data_from_api", return_value=kit_data),
            patch.object(self.view, "_add_kit_id_to_description"),
            patch.object(self.view, "_extract_logo_data_from_kit"),
            patch.object(self.view, "_find_and_assign_existing_kit"),
        ):
            self.view._process_kit_data(form, "42")
        form.fkapi_data.update.assert_called_once_with(kit_data)

    def test_process_kit_data_logs_exception_on_value_error(self):
        form = MagicMock()
        with (
            patch.object(self.view, "_fetch_kit_data_from_api", return_value={"x": 1}),
            patch.object(self.view, "_add_kit_id_to_description", side_effect=ValueError),
            patch(
                "footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.logger",
            ) as mock_logger,
        ):
            self.view._process_kit_data(form, "42")
        mock_logger.exception.assert_called_once()

    def test_fetch_kit_data_from_api_returns_data_when_available(self):
        kit_data = {"name": "Test Kit"}
        with patch(
            "footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.FKAPIClient",
        ) as mock_client_cls:
            mock_client_cls.return_value.get_kit_details.return_value = kit_data
            result = self.view._fetch_kit_data_from_api("1")
        assert result == kit_data

    def test_add_kit_id_to_description_appends_when_empty(self):
        form = MagicMock()
        form.instance.description = None
        self.view._add_kit_id_to_description(form, 123)
        assert form.instance.description == "\nKit ID from API: 123"

    def test_add_kit_id_to_description_appends_when_existing(self):
        form = MagicMock()
        form.instance.description = "Existing"
        self.view._add_kit_id_to_description(form, 456)
        assert form.instance.description == "Existing\nKit ID from API: 456"

    def test_extract_brand_logo_skips_not_found_url(self):
        self.view.fkapi_data = {}
        kit_data = {
            "brand": {
                "logo": "https://www.footballkitarchive.com/static/logos/not_found.png",
                "logo_dark": "https://www.footballkitarchive.com/static/logos/not_found.png",
            },
        }
        self.view._extract_brand_logo(kit_data)
        assert "brand_logo" not in self.view.fkapi_data
        assert "brand_logo_dark" not in self.view.fkapi_data

    def test_extract_competition_logos_skips_not_found_url(self):
        self.view.fkapi_data = {}
        kit_data = {
            "competition": [
                {"logo": "https://www.footballkitarchive.com/static/logos/not_found.png"},
                {"logo": "https://example.com/real.png"},
            ],
        }
        self.view._extract_competition_logos(kit_data)
        assert self.view.fkapi_data["competition_logos"] == ["https://example.com/real.png"]

    def test_find_and_assign_existing_kit_does_nothing_when_kit_not_found(self):
        from footycollect.collection.models import Kit

        form = MagicMock()
        form.instance = type("Obj", (), {})()
        with patch.object(Kit, "objects") as mock_objs:
            mock_objs.get.side_effect = Kit.DoesNotExist
            self.view._find_and_assign_existing_kit(form, 99999)
        assert not hasattr(form.instance, "kit")

    def test_assign_kit_entities_assigns_brand_club_season_when_missing(self):
        form = MagicMock()
        form.instance.brand_id = None
        form.instance.club_id = None
        form.instance.season_id = None
        kit = KitFactory()
        with patch(
            "footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.logger",
        ):
            self.view._assign_kit_entities(form, kit)
        assert form.instance.brand == kit.brand
        assert form.instance.club == kit.team
        assert form.instance.season == kit.season

    def test_assign_kit_entities_skips_when_already_set(self):
        form = MagicMock()
        form.instance.brand_id = 1
        form.instance.club_id = 2
        form.instance.season_id = 3
        form.instance.brand = "existing_brand"
        form.instance.club = "existing_club"
        form.instance.season = "existing_season"
        kit = KitFactory()
        self.view._assign_kit_entities(form, kit)
        assert form.instance.brand == "existing_brand"
        assert form.instance.club == "existing_club"
        assert form.instance.season == "existing_season"

    def test_assign_kit_competitions_calls_set_with_kit_competitions_list(self):
        from footycollect.core.models import Competition

        comp = Competition.objects.create(name="Cup", slug="cup", logo="")
        kit = KitFactory()
        kit.competition.add(comp)
        form = MagicMock()
        form.instance.competitions = MagicMock()
        with patch(
            "footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.logger",
        ):
            self.view._assign_kit_competitions(form, kit)
        form.instance.competitions.set.assert_called_once()
        (passed_arg,) = form.instance.competitions.set.call_args[0]
        assert list(passed_arg) == list(kit.competition.all())

    def test_assign_kit_competitions_logs_warning_when_no_competitions(self):
        kit = KitFactory()
        form = MagicMock()
        with patch(
            "footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.logger",
        ) as mock_logger:
            self.view._assign_kit_competitions(form, kit)
        assert any("No competitions" in str(c) for c in mock_logger.warning.call_args_list)
