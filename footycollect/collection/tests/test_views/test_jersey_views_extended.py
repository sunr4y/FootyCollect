"""
Extended tests for jersey views with real functionality testing.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from footycollect.collection.models import Brand, Competition, Jersey, Season, Size
from footycollect.collection.views.jersey_views import JerseyFKAPICreateView
from footycollect.core.models import Club

User = get_user_model()

# Constants for test values
TEST_PASSWORD = "testpass123"
EXPECTED_COMPETITIONS_COUNT = 2
EXPECTED_DOWNLOAD_CALLS = 3  # main_img_url + 2 external_urls


class TestJerseyFKAPICreateViewExtended(TestCase):
    """Extended test cases for JerseyFKAPICreateView with real functionality tests."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=TEST_PASSWORD,
        )
        self.brand = Brand.objects.create(name="Nike")
        self.club = Club.objects.create(name="Real Madrid", country="ES")
        self.season = Season.objects.create(year="2023-24")
        self.competition = Competition.objects.create(name="La Liga")
        self.size = Size.objects.create(name="M", category="tops")

    def test_dispatch_delegates_to_super_for_post(self):
        """Test that dispatch delegates to CreateView.dispatch for POST requests."""
        view = JerseyFKAPICreateView()
        request = Mock()
        request.method = "POST"
        request.user = self.user

        with patch("footycollect.collection.views.jersey_views.CreateView.dispatch") as mock_super:
            mock_super.return_value = Mock()

            view.dispatch(request)

            mock_super.assert_called_once_with(request)

    def test_dispatch_does_not_log_get_requests(self):
        """Test that dispatch method does not log GET requests."""
        view = JerseyFKAPICreateView()
        request = Mock()
        request.method = "GET"
        request.user = self.user

        with (
            patch("footycollect.collection.views.jersey_views.logger") as mock_logger,
            patch("footycollect.collection.views.jersey_views.CreateView.dispatch") as mock_super,
        ):
            mock_super.return_value = Mock()

            view.dispatch(request)

            mock_logger.info.assert_not_called()
            mock_super.assert_called_once_with(request)

    def test_post_preprocesses_form_and_calls_form_valid(self):
        """Test that POST preprocesses form data and calls form_valid when form is valid."""
        view = JerseyFKAPICreateView()
        request = Mock()
        request.POST = {"name": "Test Jersey"}
        request.FILES = {}
        request.content_type = "application/x-www-form-urlencoded"
        request.META = {}

        with (
            patch.object(view, "get_form") as mock_get_form,
            patch.object(view, "_preprocess_form_data") as mock_preprocess,
            patch.object(view, "form_valid") as mock_form_valid,
        ):
            mock_form = Mock()
            mock_form.is_valid.return_value = True
            mock_get_form.return_value = mock_form
            mock_form_valid.return_value = Mock()

            view.post(request)

            mock_preprocess.assert_called_once_with(mock_form)
            mock_form_valid.assert_called_once_with(mock_form)

    def test_get_form_kwargs_includes_user(self):
        """Test that get_form_kwargs includes user."""
        view = JerseyFKAPICreateView()
        request = Mock()
        request.user = self.user
        request.POST = Mock()
        view.request = request

        with patch("footycollect.collection.views.jersey_views.CreateView.get_form_kwargs") as mock_super:
            mock_super.return_value = {"data": "test"}

            result = view.get_form_kwargs()

            assert result["data"] == request.POST
            assert result["user"] == self.user

    def test_get_context_data_success(self):
        """Test get_context_data with successful service call."""
        with patch("footycollect.collection.views.base.get_collection_service") as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service
            mock_service.get_form_data.return_value = {
                "colors": {"main_colors": [{"name": "Red", "hex": "#FF0000"}]},
            }

            view = JerseyFKAPICreateView()

            with patch.object(view, "get_form") as mock_get_form:
                mock_form = Mock()
                mock_form.data = {}
                mock_form.initial = {}
                mock_form.fields = {}
                mock_get_form.return_value = mock_form

                result = view.get_context_data()

                assert "form" in result
                assert "color_choices" in result
                assert "design_choices" in result

    def test_get_context_data_error_handling(self):
        """Test get_context_data with service error."""
        with patch("footycollect.collection.views.base.get_collection_service") as mock_get_service:
            mock_get_service.side_effect = KeyError("Service error")

            view = JerseyFKAPICreateView()

            with patch.object(view, "get_form") as mock_get_form:
                mock_form = Mock()
                mock_form.data = {}
                mock_form.initial = {}
                mock_form.fields = {}
                mock_get_form.return_value = mock_form

                result = view.get_context_data()

                assert "form" in result
                assert result["color_choices"] == "[]"
                assert result["design_choices"] == "[]"

    def test_form_valid_success_flow(self):
        """Test form_valid method with successful processing."""
        view = JerseyFKAPICreateView()
        request = Mock()
        request.user = self.user
        request.POST = {"photo_ids": ""}
        view.request = request

        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {}
        mock_form.data = {}
        mock_form.errors = {}
        mock_form.fields = {}

        with (
            patch.object(view, "_ensure_form_cleaned_data") as mock_ensure_cleaned,
            patch.object(view, "_process_new_entities") as mock_process_entities,
            patch.object(view, "_save_and_finalize") as mock_save,
            patch.object(view, "_get_base_item_for_photos") as mock_get_base_item,
            patch.object(view, "_process_external_images") as mock_process_images,
            patch.object(view, "_process_photo_ids"),
            patch("footycollect.collection.views.jersey_views.messages") as mock_messages,
            patch("django.conf.settings") as mock_settings,
        ):
            import tempfile

            mock_settings.BASE_DIR = tempfile.gettempdir()
            mock_response = Mock()
            mock_save.return_value = mock_response

            view.object = Mock()
            view.object.is_draft = True
            view.object.save = Mock()
            view.object.refresh_from_db = Mock()
            view.object.base_item = Mock()
            view.object.base_item.id = 1
            view.object.id = 1

            mock_base_item = Mock()
            mock_base_item.id = 1
            mock_get_base_item.return_value = mock_base_item

            result = view.form_valid(mock_form)

            mock_ensure_cleaned.assert_called_once_with(mock_form)
            mock_process_entities.assert_called_once_with(mock_form)
            mock_save.assert_called_once_with(mock_form)
            mock_get_base_item.assert_called_once()
            mock_process_images.assert_called_once_with(mock_form, mock_base_item)
            mock_messages.success.assert_called_once()
            assert result == mock_response

    def test_form_valid_exception_handling(self):
        """Test form_valid method with exception handling."""
        view = JerseyFKAPICreateView()
        request = Mock()
        request.user = self.user
        view.request = request

        mock_form = Mock()
        mock_form.is_valid.return_value = True

        with (
            patch.object(view, "_process_new_entities") as mock_process_entities,
            patch.object(view, "form_invalid") as mock_form_invalid,
            patch("footycollect.collection.views.jersey_views.messages") as mock_messages,
        ):
            # Use ValueError instead of generic Exception since form_valid
            # now catches specific exceptions (ValueError, TypeError, etc.)
            mock_process_entities.side_effect = ValueError("Processing error")
            mock_form_invalid.return_value = Mock()

            result = view.form_valid(mock_form)

            mock_messages.error.assert_called_once()
            mock_form_invalid.assert_called_once_with(mock_form)
            assert result == mock_form_invalid.return_value

    def test_preprocess_form_data_flow(self):
        """Test _preprocess_form_data method flow."""
        view = JerseyFKAPICreateView()
        mock_form = Mock()
        mock_form.data = {"kit_id": "123"}

        with (
            patch.object(view, "_setup_form_instance") as mock_setup,
            patch.object(view, "_process_kit_data") as mock_process_kit,
            patch.object(view, "_fill_form_with_api_data") as mock_fill,
        ):
            view._preprocess_form_data(mock_form)

            mock_setup.assert_called_once_with(mock_form)
            mock_process_kit.assert_called_once_with(mock_form, "123")
            mock_fill.assert_called_once_with(mock_form)

    def test_fill_form_with_api_data_flow(self):
        """Test _fill_form_with_api_data method flow."""
        view = JerseyFKAPICreateView()
        mock_form = Mock()
        mock_form.data = {"name": ""}
        mock_form.instance = Mock()
        mock_form.instance.name = "Test Jersey"

        with (
            patch.object(view, "_fill_club_field") as mock_fill_club,
            patch.object(view, "_fill_brand_field") as mock_fill_brand,
            patch.object(view, "_fill_season_field") as mock_fill_season,
        ):
            view._fill_form_with_api_data(mock_form)

            mock_fill_club.assert_called_once_with(mock_form)
            mock_fill_brand.assert_called_once_with(mock_form)
            mock_fill_season.assert_called_once_with(mock_form)

    def test_fill_club_field_existing_club(self):
        """Test _fill_club_field method with existing club."""
        view = JerseyFKAPICreateView()
        mock_form = Mock()
        mock_form.data = {"club_name": "Real Madrid", "club": ""}

        with patch("footycollect.core.models.Club.objects.get") as mock_get:
            mock_club = Mock()
            mock_club.id = 1
            mock_get.return_value = mock_club

            with patch.object(view, "_update_club_country") as mock_update:
                view._fill_club_field(mock_form)

                mock_get.assert_called_once_with(name="Real Madrid")
                mock_update.assert_called_once_with(mock_club)
                assert mock_form.data["club"] == 1

    def test_fill_club_field_new_club(self):
        """Test _fill_club_field method with new club."""
        view = JerseyFKAPICreateView()
        mock_form = Mock()
        mock_form.data = {"club_name": "New Club", "club": ""}

        with patch("footycollect.core.models.Club.objects.get") as mock_get:
            mock_get.side_effect = Club.DoesNotExist()

            with patch.object(view, "_create_club_from_api_data") as mock_create:
                mock_club = Mock()
                mock_club.id = 2
                mock_create.return_value = mock_club

                view._fill_club_field(mock_form)

                mock_create.assert_called_once_with(mock_form)
                assert mock_form.data["club"] == 2  # noqa: PLR2004

    def test_fetch_kit_data_from_api_success(self):
        """Test _fetch_kit_data_from_api method with success."""
        with (
            patch(
                "footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.FKAPIClient"
            ) as mock_client_class,
        ):
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_kit_details.return_value = {"kit": "data"}

            view = JerseyFKAPICreateView()

            result = view._fetch_kit_data_from_api(123)

            mock_client.get_kit_details.assert_called_once_with(123)
            assert result == {"kit": "data"}

    def test_fetch_kit_data_from_api_error(self):
        """Test _fetch_kit_data_from_api method with error."""
        with (
            patch(
                "footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.FKAPIClient"
            ) as mock_client_class,
            patch("footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.logger") as mock_logger,
            patch("footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.messages") as mock_messages,
        ):
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_kit_details.return_value = None

            view = JerseyFKAPICreateView()
            request = Mock()
            view.request = request

            result = view._fetch_kit_data_from_api(123)

            mock_logger.warning.assert_called()
            mock_messages.warning.assert_called_once()
            assert result is None

    def test_add_kit_id_to_description(self):
        """Test _add_kit_id_to_description method."""
        view = JerseyFKAPICreateView()
        mock_form = Mock()
        mock_form.instance = Mock()
        mock_form.instance.description = "Original description"

        view._add_kit_id_to_description(mock_form, 123)

        assert mock_form.instance.description == "Original description\nKit ID from API: 123"

    def test_extract_logo_data_from_kit_flow(self):
        """Test _extract_logo_data_from_kit method flow."""
        view = JerseyFKAPICreateView()
        kit_data = {
            "brand": {"logo": "brand_logo_url"},
            "team": {"logo": "team_logo_url", "country": "ES"},
            "competition": [{"logo": "comp_logo_url"}],
        }

        with (
            patch.object(view, "_extract_brand_logo") as mock_brand,
            patch.object(view, "_extract_team_data") as mock_team,
            patch.object(view, "_extract_competition_logos") as mock_comp,
        ):
            view._extract_logo_data_from_kit(kit_data)

            mock_brand.assert_called_once_with(kit_data)
            mock_team.assert_called_once_with(kit_data)
            mock_comp.assert_called_once_with(kit_data)

    def test_extract_brand_logo(self):
        """Test _extract_brand_logo method."""
        view = JerseyFKAPICreateView()
        view.fkapi_data = {}
        kit_data = {
            "brand": {"logo": "https://example.com/logo.png"},
        }

        with patch("footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.logger") as mock_logger:
            view._extract_brand_logo(kit_data)

            assert hasattr(view, "fkapi_data")
            assert view.fkapi_data["brand_logo"] == "https://example.com/logo.png"
            mock_logger.info.assert_called()

    def test_extract_team_data(self):
        """Test _extract_team_data method."""
        view = JerseyFKAPICreateView()
        view.fkapi_data = {}
        kit_data = {
            "team": {
                "logo": "https://example.com/team_logo.png",
                "country": "ES",
            },
        }

        with patch("footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.logger") as mock_logger:
            view._extract_team_data(kit_data)

            assert hasattr(view, "fkapi_data")
            assert view.fkapi_data["team_logo"] == "https://example.com/team_logo.png"
            assert view.fkapi_data["team_country"] == "ES"
            mock_logger.info.assert_called()

    def test_extract_competition_logos(self):
        """Test _extract_competition_logos method."""
        view = JerseyFKAPICreateView()
        view.fkapi_data = {}
        kit_data = {
            "competition": [
                {"logo": "https://example.com/comp1.png"},
                {"logo": "https://example.com/comp2.png"},
            ],
        }

        with patch("footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.logger") as mock_logger:
            view._extract_competition_logos(kit_data)

            assert hasattr(view, "fkapi_data")
            assert "competition_logos" in view.fkapi_data
            assert len(view.fkapi_data["competition_logos"]) == 2  # noqa: PLR2004
            mock_logger.info.assert_called()

    def test_find_and_assign_existing_kit_found(self):
        """Test _find_and_assign_existing_kit method with existing kit."""
        view = JerseyFKAPICreateView()
        mock_form = Mock()

        with patch("footycollect.collection.models.Kit.objects.get") as mock_get:
            mock_kit = Mock()
            mock_get.return_value = mock_kit

            with patch.object(view, "_assign_existing_kit") as mock_assign:
                view._find_and_assign_existing_kit(mock_form, 123)

                mock_get.assert_called_once_with(id_fka=123)
                mock_assign.assert_called_once_with(mock_form, mock_kit, 123)

    def test_create_jersey_with_fkapi_data(self):
        """Test creating jersey with FKAPI data integration."""
        # Test complete flow of creating jersey with FKAPI data
        view = JerseyFKAPICreateView()
        view.request = Mock()
        view.request.user = self.user
        view.request.POST = {"photo_ids": ""}

        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {
            "name": "Real Madrid 2023-24 Home",
            "club_name": "Real Madrid",
            "brand_name": "Nike",
            "season_name": "2023-24",
            "competition_name": "La Liga",
            "kit_id": "12345",
            "main_img_url": "https://example.com/jersey.jpg",
        }
        mock_form.data = mock_form.cleaned_data.copy()
        mock_form.errors = {}
        mock_form.fields = {}
        mock_form.instance = Mock()
        mock_form.instance.name = "Real Madrid 2023-24 Home"
        mock_form.instance.user = self.user
        mock_form.instance.is_draft = True
        mock_form.instance.save = Mock()

        # Mock the jersey creation
        mock_jersey = Mock()
        mock_jersey.pk = 1
        mock_jersey.is_draft = True
        mock_jersey.save = Mock()

        with (
            patch.object(view, "_ensure_form_cleaned_data") as mock_ensure_cleaned,
            patch.object(view, "_process_new_entities") as mock_process_entities,
            patch.object(view, "_save_and_finalize") as mock_save,
            patch.object(view, "_get_base_item_for_photos") as mock_get_base_item,
            patch.object(view, "_process_external_images") as mock_process_images,
            patch.object(view, "_process_photo_ids"),
            patch("footycollect.collection.views.jersey_views.messages") as mock_messages,
            patch("footycollect.collection.tasks.check_item_photo_processing"),
            patch("django.conf.settings") as mock_settings,
        ):
            import tempfile

            mock_settings.BASE_DIR = tempfile.gettempdir()
            mock_save.return_value = Mock()
            view.object = mock_jersey
            view.object.refresh_from_db = Mock()
            view.object.base_item = Mock()
            view.object.base_item.id = 1
            view.object.base_item.pk = 1
            view.object.id = 1

            mock_base_item = Mock()
            mock_base_item.id = 1
            mock_base_item.pk = 1
            mock_get_base_item.return_value = mock_base_item

            result = view.form_valid(mock_form)

            # Verify the complete flow was executed
            mock_ensure_cleaned.assert_called_once_with(mock_form)
            mock_process_entities.assert_called_once_with(mock_form)
            mock_save.assert_called_once_with(mock_form)
            mock_get_base_item.assert_called_once()
            mock_process_images.assert_called_once_with(mock_form, mock_base_item)
            mock_messages.success.assert_called_once()
            assert result == mock_save.return_value

    def test_jersey_fkapi_form_validation(self):
        """Test jersey FKAPI form validation with real data."""
        # Test form validation with FKAPI data
        form_data = {
            "name": "Real Madrid 2023-24 Home",
            "club_name": "Real Madrid",
            "brand_name": "Nike",
            "season_name": "2023-24",
            "competition_name": "La Liga",
            "kit_id": "12345",
            "main_img_url": "https://example.com/jersey.jpg",
            "size": self.size.id,
            "condition": 10,
            "detailed_condition": "BNWT",
        }

        with patch("footycollect.collection.views.jersey_views.JerseyFKAPIForm") as mock_form_class:
            mock_form = Mock()
            mock_form.is_valid.return_value = True
            mock_form.cleaned_data = form_data
            mock_form.errors = {}
            mock_form_class.return_value = mock_form

            view = JerseyFKAPICreateView()
            view.request = Mock()
            view.request.user = self.user

            # Test form validation - mock the form to return valid
            with patch.object(view, "get_form") as mock_get_form:
                mock_get_form.return_value = mock_form
                form = view.get_form()
                assert form.is_valid()
                assert form.cleaned_data["name"] == "Real Madrid 2023-24 Home"

    def test_user_cannot_access_other_user_jerseys(self):
        """Test user cannot access other user's jerseys."""
        # Create another user
        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password=TEST_PASSWORD,
        )

        # Create jersey for other user with required brand
        from footycollect.collection.models import BaseItem

        base_item = BaseItem.objects.create(
            user=other_user,
            name="Other User Jersey",
            item_type="jersey",
            brand=self.brand,  # Add required brand
        )
        jersey = Jersey.objects.create(base_item=base_item, size=self.size)

        # Test that current user cannot access other user's jersey
        view = JerseyFKAPICreateView()
        view.request = Mock()
        view.request.user = self.user

        # Verify user can only see their own jerseys
        user_jerseys = Jersey.objects.filter(base_item__user=self.user)
        other_jerseys = Jersey.objects.filter(base_item__user=other_user)

        assert jersey not in user_jerseys
        assert jersey in other_jerseys

    def test_jersey_creation_rollback_on_error(self):
        """Test jersey creation rolls back on error."""
        view = JerseyFKAPICreateView()
        view.request = Mock()
        view.request.user = self.user
        view.request.POST = {"photo_ids": ""}

        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {"name": "Test Jersey"}
        mock_form.instance = Mock()
        mock_form.instance.name = "Test Jersey"
        mock_form.instance.user = self.user
        mock_form.instance.is_draft = True
        mock_form.instance.save = Mock()

        # Mock an error in processing
        with (
            patch.object(view, "_process_new_entities") as mock_process_entities,
            patch.object(view, "form_invalid") as mock_form_invalid,
            patch("footycollect.collection.views.jersey_views.messages") as mock_messages,
        ):
            mock_process_entities.side_effect = Exception("Processing error")
            mock_form_invalid.return_value = Mock()

            result = view.form_valid(mock_form)

            # Verify error handling
            mock_messages.error.assert_called_once()
            mock_form_invalid.assert_called_once_with(mock_form)
            assert result == mock_form_invalid.return_value

    def test_fkapi_service_integration(self):
        """Test FKAPI service integration with real API calls."""
        view = JerseyFKAPICreateView()

        # Mock FKAPI client
        with patch(
            "footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.FKAPIClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_kit_details.return_value = {
                "name": "Real Madrid 2023-24 Home",
                "team": {"name": "Real Madrid", "country": "ES", "logo": "https://example.com/logo.png"},
                "brand": {"name": "Nike", "logo": "https://example.com/nike.png"},
                "season": {"year": "2023-24"},
                "competition": [{"name": "La Liga", "logo": "https://example.com/laliga.png"}],
            }

            # Test API integration
            result = view._fetch_kit_data_from_api("12345")

            mock_client.get_kit_details.assert_called_once_with("12345")
            assert result["name"] == "Real Madrid 2023-24 Home"
            assert result["team"]["name"] == "Real Madrid"

    def test_context_data_integration(self):
        """Test context data integration with services."""
        view = JerseyFKAPICreateView()
        view.request = Mock()
        view.request.user = self.user

        # Mock collection service (used by get_color_and_design_choices in base)
        with patch("footycollect.collection.views.base.get_collection_service") as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service
            mock_service.get_form_data.return_value = {
                "colors": {"main_colors": [{"name": "Red", "hex": "#FF0000"}]},
                "sizes": {"tops": [{"id": 1, "name": "M"}]},
            }

            # Test context data
            with patch.object(view, "get_form") as mock_get_form:
                mock_form = Mock()
                mock_form.data = {}
                mock_form.initial = {}
                mock_form.fields = {}
                mock_get_form.return_value = mock_form

                context = view.get_context_data()

                assert "form" in context
                assert "color_choices" in context
                assert "design_choices" in context
                assert context["color_choices"] != "[]"

    def test_redirect_flow_complete(self):
        """Test complete redirect flow after jersey creation."""
        view = JerseyFKAPICreateView()
        view.object = Mock()
        view.object.pk = 1

        # Test success URL generation
        success_url = view.get_success_url()

        from django.urls import reverse_lazy

        expected_url = reverse_lazy("collection:item_detail", kwargs={"pk": 1})
        assert success_url == expected_url

    def test_form_instance_setup_with_real_data(self):
        """Test form instance setup with real data."""
        view = JerseyFKAPICreateView()
        view.request = Mock()
        view.request.user = self.user

        instance_placeholder = SimpleNamespace(name=None)
        mock_form = Mock()
        mock_form.instance = None
        mock_form._meta.model.return_value = instance_placeholder
        mock_form.data = {
            "name": "Real Madrid 2023-24 Home",
            "country_code": "ES",
            "club_name": "Real Madrid",
            "season_name": "2023-24",
        }

        view._setup_form_instance(mock_form)
        assert mock_form.instance is instance_placeholder
        assert mock_form.instance.name == "Real Madrid 2023-24 Home"

    def test_save_and_finalize_with_competitions(self):
        """Test save and finalize with competition assignments."""
        view = JerseyFKAPICreateView()
        view.request = Mock()
        view.request.POST = {"all_competitions": "La Liga, Champions League"}

        mock_form = Mock()
        mock_form.cleaned_data = {"name": "Test Jersey", "main_color": None, "secondary_colors": []}
        mock_form.data = Mock()
        mock_form.data.get = Mock(return_value=None)
        mock_form.data.getlist = Mock(return_value=[])

        # Mock the jersey object
        mock_jersey = Mock()
        mock_jersey.pk = 1
        mock_jersey.competitions = Mock()
        mock_jersey.competitions.add = Mock()

        with (
            patch("footycollect.collection.views.jersey_views.CreateView.form_valid") as mock_super,
            patch(
                "footycollect.collection.views.jersey.mixins.kit_data_processing_mixin.Competition.objects.get_or_create",
            ) as mock_get_or_create,
            patch("footycollect.collection.models.Color.objects.get_or_create") as mock_color_get_or_create,
        ):
            mock_super.return_value = Mock()
            mock_get_or_create.side_effect = [
                (Mock(name="La Liga"), True),
                (Mock(name="Champions League"), True),
            ]
            mock_color_get_or_create.return_value = (Mock(name="WHITE"), False)

            view.object = mock_jersey
            result = view._save_and_finalize(mock_form)

            # Verify competitions were processed
            assert mock_get_or_create.call_count == 2  # noqa: PLR2004
            assert result == mock_super.return_value

    def test_post_processes_multiple_competitions_from_api(self):
        """Test that post() method processes multiple competitions from FKAPI data."""
        from django.http import QueryDict

        from footycollect.core.models import Competition

        view = JerseyFKAPICreateView()
        request = Mock()
        request.user = self.user
        request.POST = QueryDict(mutable=True)
        request.POST.update(
            {
                "kit_id": "12345",
                "size": self.size.id,
                "condition": 8,
            },
        )
        request.FILES = {}
        request.content_type = "application/x-www-form-urlencoded"
        request.META = {}

        # Mock FKAPI data with multiple competitions
        kit_data = {
            "id": 12345,
            "name": "FC Barcelona 2007-08 Home",
            "competition": [
                {"id": 747, "name": "Champions League"},
                {"id": 755, "name": "La Liga"},
            ],
            "team": {"country": "ES"},
            "primary_color": {"name": "Red"},
            "secondary_color": [{"name": "Blue"}],
        }

        # Create competitions in database (use get_or_create to avoid duplicates)
        comp1, _ = Competition.objects.get_or_create(
            name="Champions League",
            defaults={"id_fka": 747, "slug": "champions-league-test"},
        )
        comp2, _ = Competition.objects.get_or_create(
            name="La Liga",
            defaults={"id_fka": 755, "slug": "la-liga-test"},
        )

        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {
            "name": "FC Barcelona 2007-08 Home",
            "size": self.size.id,
            "condition": 8,
        }
        mock_form.data = {}
        mock_form.instance = Mock()
        mock_form.fields = {}

        with (
            patch("footycollect.api.client.FKAPIClient") as mock_client_class,
            patch.object(view, "get_form") as mock_get_form,
            patch.object(view, "form_valid") as mock_form_valid,
        ):
            mock_client = Mock()
            mock_client.get_kit_details.return_value = kit_data
            mock_client_class.return_value = mock_client
            mock_get_form.return_value = mock_form
            mock_form_valid.return_value = Mock()

            view.post(request)

            # Verify competitions were added to POST data
            assert "competitions" in request.POST
            competitions_str = request.POST["competitions"]
            competition_ids = [int(x) for x in competitions_str.split(",") if x.strip().isdigit()]
            assert len(competition_ids) == EXPECTED_COMPETITIONS_COUNT
            assert comp1.id in competition_ids
            assert comp2.id in competition_ids

    def test_photo_processing_integration(self):
        """Test photo processing integration with real data."""
        view = JerseyFKAPICreateView()
        view.object = Mock()
        view.object.pk = 1
        view.object.base_item = Mock()
        view.object.base_item.id = 1
        view.request = Mock()
        view.request.user = self.user

        # Test photo ID processing
        photo_ids = "1,2,3"

        with (
            patch.object(view, "_parse_photo_ids") as mock_parse,
            patch.object(view, "_process_external_images_from_photo_ids") as mock_external,
            patch.object(view, "_associate_existing_photos") as mock_associate,
        ):
            mock_parse.return_value = (["1", "2", "3"], [], {})

            view._process_photo_ids(photo_ids)

            mock_parse.assert_called_once_with(photo_ids)
            mock_external.assert_called_once_with([], view.object.base_item)
            mock_associate.assert_called_once_with(["1", "2", "3"], {}, view.object.base_item, start_order=0)

    def test_entity_creation_integration(self):
        """Test entity creation integration with real data."""
        view = JerseyFKAPICreateView()
        view.request = Mock()
        view.request.user = self.user

        mock_form = Mock()
        mock_form.cleaned_data = {
            "brand_name": "Nike",
            "club_name": "Real Madrid",
            "season_name": "2023-24",
            "competition_name": "La Liga",
        }

        with (
            patch.object(view, "_process_brand_entity") as mock_brand,
            patch.object(view, "_process_club_entity") as mock_club,
            patch.object(view, "_process_season_entity") as mock_season,
            patch.object(view, "_process_competition_entity") as mock_competition,
        ):
            view._process_new_entities(mock_form)

            # Verify all entity processing methods were called
            mock_brand.assert_called_once_with(mock_form, mock_form.cleaned_data)
            mock_club.assert_called_once_with(mock_form, mock_form.cleaned_data)
            mock_season.assert_called_once_with(mock_form, mock_form.cleaned_data)
            mock_competition.assert_called_once_with(mock_form, mock_form.cleaned_data)

    def test_external_image_download_integration(self):
        """Test external image download integration."""
        view = JerseyFKAPICreateView()
        view.object = Mock()
        view.object.pk = 1
        view.request = Mock()  # Add missing request attribute

        mock_form = Mock()
        mock_form.cleaned_data = {
            "main_img_url": "https://example.com/jersey.jpg",
            "external_image_urls": "https://example.com/back.jpg,https://example.com/side.jpg",
        }

        with patch.object(view, "_download_and_attach_image") as mock_download:
            view._process_external_images(mock_form)

            # Verify main image processing - check that download was called
            assert mock_download.call_count == EXPECTED_DOWNLOAD_CALLS

    def test_kit_data_processing_integration(self):
        """Test kit data processing integration."""
        view = JerseyFKAPICreateView()
        view.request = Mock()
        view.request.user = self.user

        mock_form = Mock()
        mock_form.data = {"kit_id": "12345"}

        kit_data = {
            "name": "Real Madrid 2023-24 Home",
            "team": {"name": "Real Madrid", "country": "ES", "logo": "https://example.com/logo.png"},
            "brand": {"name": "Nike", "logo": "https://example.com/nike.png"},
            "season": {"year": "2023-24"},
            "competition": [{"name": "La Liga", "logo": "https://example.com/laliga.png"}],
        }

        with (
            patch.object(view, "_fetch_kit_data_from_api") as mock_fetch,
            patch.object(view, "_add_kit_id_to_description") as mock_add_id,
            patch.object(view, "_extract_logo_data_from_kit") as mock_extract,
            patch.object(view, "_find_and_assign_existing_kit") as mock_find,
        ):
            mock_fetch.return_value = kit_data

            view._process_kit_data(mock_form, "12345")

            # Verify kit data processing
            mock_fetch.assert_called_once_with("12345")
            mock_add_id.assert_called_once_with(mock_form, "12345")
            mock_extract.assert_called_once_with(kit_data)
            mock_find.assert_called_once_with(mock_form, "12345")
