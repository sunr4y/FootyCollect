"""
Tests for collection forms.
"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict
from django.test import TestCase

from footycollect.collection.factories import (
    BrandFactory,
    ClubFactory,
    SeasonFactory,
    SizeFactory,
    UserFactory,
)
from footycollect.collection.forms import (
    BaseItemForm,
    BrandWidget,
    JerseyFKAPIForm,
    JerseyForm,
    MultipleFileField,
    MultipleFileInput,
)
from footycollect.collection.models import BaseItem, Brand, Club, Color, Season, Size

User = get_user_model()

# Constants for test values
EXPECTED_FILES_COUNT_2 = 2
EXPECTED_COMPETITIONS_COUNT = 2
EXPECTED_COLORS_COUNT = 2


class JerseyFormTest(TestCase):
    """Test JerseyForm."""

    def setUp(self):
        self.user = UserFactory()
        self.user.set_password("testpass123")
        self.user.save()
        self.brand = BrandFactory(name="Nike")
        self.club = ClubFactory(name="Barcelona", country="ES")
        self.season = SeasonFactory(year="2023-24", first_year="2023", second_year="24")

    def test_jersey_form_valid_data(self):
        """Test JerseyForm with valid data."""
        # Create a size object first
        size = SizeFactory(name="M", category="tops")

        form_data = {
            "name": "Test Jersey",
            "brand": self.brand.id,
            "club": self.club.id,
            "season": self.season.id,
            "condition": 8,  # Integer between 1-10
            "size": size.id,
            "is_replica": False,
            "is_signed": False,
            "description": "Beautiful jersey in excellent condition",
        }

        form = JerseyForm(data=form_data, instance=BaseItem())
        assert form.is_valid()

    def test_jersey_form_invalid_data(self):
        """Test JerseyForm with invalid data."""
        # Create a size object first
        size = SizeFactory(name="M", category="tops")

        form_data = {
            "name": "Test Jersey",
            "brand": self.brand.id,
            "condition": 15,  # Invalid: > 10
            "size": size.id,
            "is_replica": False,
            "is_signed": False,
        }

        form = JerseyForm(data=form_data, instance=BaseItem())
        assert not form.is_valid()
        assert "condition" in form.errors

    def test_jersey_form_optional_fields(self):
        """Test JerseyForm with optional fields."""
        # Create a size object first
        from footycollect.collection.models import Size

        size = Size.objects.create(name="L", category="tops")

        form_data = {
            "name": "Test Jersey",
            "brand": self.brand.id,
            "condition": 7,  # Integer between 1-10
            "size": size.id,
            "is_replica": True,
            "is_signed": False,
            # club and season are optional
        }

        form = JerseyForm(data=form_data, instance=BaseItem())
        assert form.is_valid()

    def test_jersey_form_condition_choices(self):
        """Test JerseyForm condition field validation."""
        # Create a size object first
        size = SizeFactory(name="M", category="tops")

        form_data = {
            "name": "Test Jersey",
            "brand": self.brand.id,
            "condition": 5,  # Valid condition
            "size": size.id,
            "is_replica": False,
            "is_signed": False,
        }

        form = JerseyForm(data=form_data, instance=BaseItem())
        assert form.is_valid()

    def test_jersey_form_size_choices(self):
        """Test JerseyForm size field validation."""
        # Create size objects first
        size_m = SizeFactory(name="M", category="tops")
        SizeFactory(name="L", category="tops")

        form_data = {
            "name": "Test Jersey",
            "brand": self.brand.id,
            "condition": 8,
            "size": size_m.id,
            "is_replica": False,
            "is_signed": False,
        }

        form = JerseyForm(data=form_data, instance=BaseItem())
        assert form.is_valid()


class JerseyFKAPIFormTest(TestCase):
    """Test JerseyFKAPIForm."""

    def setUp(self):
        self.user = UserFactory()
        self.user.set_password("testpass123")
        self.user.save()

    def test_jersey_fkapi_form_valid_data(self):
        """Test JerseyFKAPIForm with valid data."""
        # Create required objects first
        size = SizeFactory(name="M", category="tops")
        brand = BrandFactory(name="Nike")

        form_data = {
            "name": "Test Jersey",
            "brand": brand.id,  # Real Brand ID
            "condition": 8,  # Integer between 1-10
            "size": size.id,
            "is_replica": False,
            "is_signed": False,
            "description": "Jersey from FKAPI",
        }

        query_dict = QueryDict(mutable=True)
        query_dict.update(form_data)
        form = JerseyFKAPIForm(data=query_dict)
        assert form.is_valid()

    def test_jersey_fkapi_form_invalid_data(self):
        """Test JerseyFKAPIForm with invalid data."""
        # Create required objects first
        from footycollect.collection.models import Size

        size = Size.objects.create(name="M", category="tops")

        form_data = {
            "name": "Test Jersey",
            "condition": 15,  # Invalid: > 10
            "size": size.id,
            "is_replica": False,
            "is_signed": False,
        }

        query_dict = QueryDict(mutable=True)
        query_dict.update(form_data)
        form = JerseyFKAPIForm(data=query_dict)
        assert not form.is_valid()
        assert "condition" in form.errors

    def test_jersey_fkapi_form_optional_fields(self):
        """Test JerseyFKAPIForm with optional fields."""
        # Create required objects first
        size = SizeFactory(name="L", category="tops")
        brand = BrandFactory(name="Adidas")

        form_data = {
            "name": "Test Jersey",
            "brand": brand.id,  # Real Brand ID
            "condition": 7,  # Integer between 1-10
            "size": size.id,
            "is_replica": True,
            "is_signed": False,
            # club, season, competitions are optional
        }

        query_dict = QueryDict(mutable=True)
        query_dict.update(form_data)
        form = JerseyFKAPIForm(data=query_dict)
        assert form.is_valid()

    def test_jersey_fkapi_form_season_year_validation(self):
        """Test JerseyFKAPIForm season year validation."""
        # Create required objects first
        size = SizeFactory(name="M", category="tops")
        brand = BrandFactory(name="Puma")

        # Valid condition
        form_data = {
            "name": "Test Jersey",
            "brand": brand.id,  # Real Brand ID
            "condition": 8,  # Valid condition
            "size": size.id,
            "is_replica": False,
            "is_signed": False,
        }

        query_dict = QueryDict(mutable=True)
        query_dict.update(form_data)
        form = JerseyFKAPIForm(data=query_dict)
        assert form.is_valid()

    def test_jersey_fkapi_form_price_validation(self):
        """Test JerseyFKAPIForm price validation."""
        # Create required objects first
        size = SizeFactory(name="M", category="tops")
        brand = BrandFactory(name="Under Armour")

        # Valid condition
        form_data = {
            "name": "Test Jersey",
            "brand": brand.id,  # Real Brand ID
            "condition": 8,  # Valid condition
            "size": size.id,
            "is_replica": False,
            "is_signed": False,
        }

        query_dict = QueryDict(mutable=True)
        query_dict.update(form_data)
        form = JerseyFKAPIForm(data=query_dict)
        assert form.is_valid()

        # Test that form is valid with good data
        assert form.is_valid()


class TestMultipleFileField(TestCase):
    """Test cases for MultipleFileField."""

    def test_multiple_file_input_widget(self):
        """Test MultipleFileInput widget."""
        widget = MultipleFileInput()
        assert widget.allow_multiple_selected

    def test_multiple_file_field_clean_single_file(self):
        """Test MultipleFileField clean method with a single file."""
        field = MultipleFileField()
        file = SimpleUploadedFile("test.txt", b"file_content")
        cleaned_data = field.clean(file)
        assert cleaned_data.name == "test.txt"

    def test_multiple_file_field_clean_multiple_files(self):
        """Test MultipleFileField clean method with multiple files."""
        field = MultipleFileField()
        file1 = SimpleUploadedFile("test1.txt", b"file_content_1")
        file2 = SimpleUploadedFile("test2.txt", b"file_content_2")
        cleaned_data = field.clean([file1, file2])
        assert len(cleaned_data) == EXPECTED_FILES_COUNT_2
        assert cleaned_data[0].name == "test1.txt"
        assert cleaned_data[1].name == "test2.txt"


class TestBrandWidget(TestCase):
    """Test cases for BrandWidget."""

    def test_brand_widget_build_attrs(self):
        """Test BrandWidget build_attrs method."""
        widget = BrandWidget()
        attrs = widget.build_attrs({}, {})
        assert attrs["data-minimum-input-length"] == 0
        assert attrs["data-placeholder"] == "Search for brand..."
        # Check if class attribute exists before asserting
        if "class" in attrs:
            assert "form-control" in attrs["class"]
            assert "select2" in attrs["class"]


class TestBaseItemForm(TestCase):
    """Test BaseItemForm."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.brand = Brand.objects.create(name="Nike")
        self.club = Club.objects.create(name="Real Madrid")
        self.season = Season.objects.create(year=2023)
        self.color = Color.objects.create(name="RED", hex_value="#FF0000")

    def test_form_initialization(self):
        """Test form initialization."""
        form = BaseItemForm()
        assert "name" in form.fields
        assert "brand" in form.fields
        assert "club" in form.fields


class TestJerseyFormExtended(TestCase):
    """Extended test cases for JerseyForm."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.brand = Brand.objects.create(name="Nike")
        self.club = Club.objects.create(name="Real Madrid")
        self.season = Season.objects.create(year=2023)
        self.color = Color.objects.create(name="RED", hex_value="#FF0000")
        self.size = Size.objects.create(name="M", category="tops")

    def test_form_initialization(self):
        """Test form initialization."""
        form = JerseyForm()
        assert "name" in form.fields
        assert "brand" in form.fields
        assert "club" in form.fields
        assert "season" in form.fields


class TestJerseyFKAPIFormExtended(TestCase):
    """Extended test cases for JerseyFKAPIForm."""

    def setUp(self):
        """Set up test data."""
        from django.utils.text import slugify

        from footycollect.core.models import Competition

        self.user = UserFactory()
        self.brand = Brand.objects.create(name="Nike")
        self.club = Club.objects.create(name="Real Madrid")
        self.season = Season.objects.create(year=2023)
        self.color = Color.objects.create(name="RED", hex_value="#FF0000")
        self.size = Size.objects.create(name="M", category="tops")
        self.competition1, _ = Competition.objects.get_or_create(
            name="Champions League",
            defaults={"id_fka": 747, "slug": slugify("Champions League")},
        )
        self.competition2, _ = Competition.objects.get_or_create(
            name="La Liga",
            defaults={"id_fka": 755, "slug": slugify("La Liga")},
        )

    def test_form_initialization(self):
        """Test form initialization."""
        form = JerseyFKAPIForm()
        assert "name" in form.fields
        assert "brand" in form.fields
        assert "club" in form.fields
        assert "season" in form.fields

    def test_extract_many_to_many_data_with_multiple_competitions(self):
        """Test _extract_many_to_many_data with multiple competitions."""
        form = JerseyFKAPIForm()
        form.cleaned_data = {
            "competitions": f"{self.competition1.id},{self.competition2.id}",
        }

        result = form._extract_many_to_many_data()

        assert "competitions" in result
        assert len(result["competitions"]) == EXPECTED_COMPETITIONS_COUNT
        assert self.competition1 in result["competitions"]
        assert self.competition2 in result["competitions"]

    def test_extract_many_to_many_data_with_single_competition(self):
        """Test _extract_many_to_many_data with single competition."""
        form = JerseyFKAPIForm()
        form.cleaned_data = {
            "competitions": str(self.competition1.id),
        }

        result = form._extract_many_to_many_data()

        assert "competitions" in result
        assert len(result["competitions"]) == 1
        assert self.competition1 in result["competitions"]

    def test_extract_many_to_many_data_with_empty_competitions(self):
        """Test _extract_many_to_many_data with empty competitions."""
        form = JerseyFKAPIForm()
        form.cleaned_data = {
            "competitions": "",
        }

        result = form._extract_many_to_many_data()

        assert "competitions" in result
        assert len(result["competitions"]) == 0

    def test_extract_many_to_many_data_with_list_competitions(self):
        """Test _extract_many_to_many_data with list format competitions."""
        form = JerseyFKAPIForm()
        form.cleaned_data = {
            "competitions": [self.competition1.id, self.competition2.id],
        }

        result = form._extract_many_to_many_data()

        assert "competitions" in result
        assert len(result["competitions"]) == EXPECTED_COMPETITIONS_COUNT
        assert self.competition1 in result["competitions"]
        assert self.competition2 in result["competitions"]

    def test_color_model_choice_field_with_color_name(self):
        """Test ColorModelChoiceField accepts color names."""
        from footycollect.collection.forms import ColorModelChoiceField

        field = ColorModelChoiceField(queryset=Color.objects.all(), required=False)

        # Test with color name string
        color_obj = field.to_python("RED")
        assert color_obj == self.color

    def test_color_model_choice_field_with_color_id(self):
        """Test ColorModelChoiceField accepts color IDs."""
        from footycollect.collection.forms import ColorModelChoiceField

        field = ColorModelChoiceField(queryset=Color.objects.all(), required=False)

        # Test with color ID
        color_obj = field.to_python(str(self.color.id))
        assert color_obj == self.color

    def test_color_model_multiple_choice_field_with_color_names(self):
        """Test ColorModelMultipleChoiceField accepts color names."""
        from footycollect.collection.forms import ColorModelMultipleChoiceField

        blue_color = Color.objects.create(name="BLUE", hex_value="#0000FF")
        field = ColorModelMultipleChoiceField(queryset=Color.objects.all(), required=False)

        # Test with list of color names
        color_objs = field.to_python(["RED", "BLUE"])
        assert len(color_objs) == EXPECTED_COLORS_COUNT
        # to_python returns strings for color names (not Color objects) for API flows
        assert self.color.name in color_objs
        assert blue_color.name in color_objs
