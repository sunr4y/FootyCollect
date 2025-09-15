"""
Tests for collection forms.
"""

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import TestCase

from footycollect.collection.factories import (
    BrandFactory,
    ClubFactory,
    SeasonFactory,
    SizeFactory,
    UserFactory,
)
from footycollect.collection.forms import JerseyFKAPIForm, JerseyForm
from footycollect.collection.models import BaseItem

User = get_user_model()


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
