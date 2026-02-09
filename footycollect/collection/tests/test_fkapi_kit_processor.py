"""
Tests for FKAPIKitProcessor.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from footycollect.collection.services.fkapi_kit_processor import FKAPIKitProcessor
from footycollect.core.models import TypeK


class TestFKAPIKitProcessorProcessKitData(TestCase):
    def setUp(self):
        self.processor = FKAPIKitProcessor()

    @patch.object(FKAPIKitProcessor, "fetch_kit_data")
    def test_process_kit_data_success_updates_form(self, mock_fetch):
        mock_fetch.return_value = {"name": "API Kit Name", "description": "API desc"}
        form = MagicMock()
        form.fkapi_data = {}
        form.cleaned_data = {"name": "Old", "description": ""}
        form.data = {}
        self.processor._process_kit_information = MagicMock()
        self.processor._add_kit_id_to_description = MagicMock()

        self.processor.process_kit_data(form, "123")

        assert form.fkapi_data["name"] == "API Kit Name"
        mock_fetch.assert_called_once_with("123")
        self.processor._add_kit_id_to_description.assert_called_once()
        self.processor._process_kit_information.assert_called_once()

    @patch.object(FKAPIKitProcessor, "fetch_kit_data")
    def test_process_kit_data_no_kit_data_returns_early(self, mock_fetch):
        mock_fetch.return_value = None
        form = MagicMock()
        form.fkapi_data = {}

        self.processor.process_kit_data(form, "123")

        assert form.fkapi_data == {}
        mock_fetch.assert_called_once_with("123")

    @patch.object(FKAPIKitProcessor, "fetch_kit_data")
    def test_process_kit_data_creates_fkapi_data_if_missing(self, mock_fetch):
        mock_fetch.return_value = {"name": "X"}
        form = MagicMock(spec=[])
        form.cleaned_data = {}
        form.data = {}
        form.fkapi_data = {}
        del form.fkapi_data
        with (
            patch.object(self.processor, "_add_kit_id_to_description"),
            patch.object(self.processor, "_process_kit_information"),
        ):
            self.processor.process_kit_data(form, "1")
        assert form.fkapi_data["name"] == "X"


class TestFKAPIKitProcessorFetchKitData(TestCase):
    def setUp(self):
        self.processor = FKAPIKitProcessor()

    def test_fetch_kit_data_returns_client_result(self):
        mock_client = MagicMock()
        mock_client.get_kit_details.return_value = {"name": "Kit"}
        processor = FKAPIKitProcessor(fkapi_client=mock_client)

        result = processor.fetch_kit_data("42")

        assert result == {"name": "Kit"}
        mock_client.get_kit_details.assert_called_once_with("42")

    def test_fetch_kit_data_returns_none_when_client_returns_none(self):
        mock_client = MagicMock()
        mock_client.get_kit_details.return_value = None
        processor = FKAPIKitProcessor(fkapi_client=mock_client)

        result = processor.fetch_kit_data("99")

        assert result is None


class TestFKAPIKitProcessorAddKitIdToDescription(TestCase):
    def setUp(self):
        self.processor = FKAPIKitProcessor()

    def test_add_kit_id_to_description_appends_reference(self):
        form = MagicMock()
        form.cleaned_data = {"description": "Existing text"}

        self.processor._add_kit_id_to_description(form, "456")

        assert "[Kit ID: 456]" in form.cleaned_data["description"]
        assert form.cleaned_data["description"].startswith("Existing text")

    def test_add_kit_id_to_description_does_not_duplicate(self):
        form = MagicMock()
        form.cleaned_data = {"description": "Text\n\n[Kit ID: 456]"}

        self.processor._add_kit_id_to_description(form, "456")

        assert form.cleaned_data["description"].count("[Kit ID: 456]") == 1


class TestFKAPIKitProcessorProcessKitName(TestCase):
    def setUp(self):
        self.processor = FKAPIKitProcessor()

    def test_process_kit_name_sets_from_api(self):
        form = MagicMock()
        form.cleaned_data = {"name": "Old"}
        self.processor._process_kit_name(form, {"name": "API Name"})
        assert form.cleaned_data["name"] == "API Name"

    def test_process_kit_name_ignores_when_no_name_in_api(self):
        form = MagicMock()
        form.cleaned_data = {"name": "Kept"}
        self.processor._process_kit_name(form, {})
        assert form.cleaned_data["name"] == "Kept"


class TestFKAPIKitProcessorProcessKitDescription(TestCase):
    def setUp(self):
        self.processor = FKAPIKitProcessor()

    def test_process_kit_description_appends_api_description(self):
        form = MagicMock()
        form.cleaned_data = {"description": "Current"}

        self.processor._process_kit_description(form, {"description": "From API"})

        assert "Current" in form.cleaned_data["description"]
        assert "From API" in form.cleaned_data["description"]

    def test_process_kit_description_skips_when_no_description_in_api(self):
        form = MagicMock()
        form.cleaned_data = {"description": "Only"}

        self.processor._process_kit_description(form, {})

        assert form.cleaned_data["description"] == "Only"


class TestFKAPIKitProcessorProcessKitType(TestCase):
    def setUp(self):
        self.processor = FKAPIKitProcessor()

    def test_process_kit_type_creates_new_type_k(self):
        kit_data = {"type": {"name": "Third", "category": "match"}}
        self.processor._process_kit_type(kit_data)
        type_k = TypeK.objects.filter(name="Third").first()
        assert type_k is not None
        assert type_k.category == "match"

    def test_process_kit_type_uses_existing_type_k(self):
        TypeK.objects.create(name="Home", category="match")
        kit_data = {"type": {"name": "Home", "category": "match"}}
        self.processor._process_kit_type(kit_data)
        assert TypeK.objects.filter(name="Home").count() == 1

    def test_process_kit_type_skips_jacket(self):
        kit_data = {"type": {"name": "Jacket", "category": "jacket"}}
        self.processor._process_kit_type(kit_data)
        assert not TypeK.objects.filter(name="Jacket").exists()


class TestFKAPIKitProcessorProcessKitColors(TestCase):
    def setUp(self):
        self.processor = FKAPIKitProcessor()

    def test_process_kit_colors_sets_main_and_secondary_in_form_data(self):
        form = MagicMock()
        form.data = {}

        self.processor._process_kit_colors(
            form,
            [{"name": "RED"}, {"name": "BLUE"}],
        )

        assert form.data["main_color"] == "RED"
        assert form.data["secondary_colors"] == ["BLUE"]

    def test_process_kit_colors_empty_list_does_nothing(self):
        form = MagicMock()
        form.data = {}
        self.processor._process_kit_colors(form, [])
        assert "main_color" not in form.data
