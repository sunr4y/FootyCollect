import types

import pytest

from footycollect.collection.models import Color
from footycollect.collection.views.jersey.mixins.form_data_mixin import FormDataMixin

EXPECTED_SECONDARY_COLOR_COUNT = 2


class DummyForm:
    def __init__(self, data=None, initial=None):
        self.data = data or {}
        self.initial = initial or {}
        self.fields = {
            "main_color": types.SimpleNamespace(initial=None),
            "secondary_colors": types.SimpleNamespace(initial=None),
        }
        self.cleaned_data = {}
        self._meta = types.SimpleNamespace(model=types.SimpleNamespace())
        self.instance = types.SimpleNamespace(name=None)


@pytest.mark.django_db
def test_set_main_color_initial_from_name():
    color = Color.objects.create(name="Red", hex_value="#FF0000")
    form = DummyForm(data={"main_color": "Red"})
    mixin = FormDataMixin()

    mixin._set_main_color_initial(form)

    assert form.fields["main_color"].initial == color.id


def test_set_main_color_initial_numeric_value_passthrough():
    form = DummyForm(data={"main_color": "5"})
    mixin = FormDataMixin()

    mixin._set_main_color_initial(form)

    assert form.fields["main_color"].initial == "5"


@pytest.mark.django_db
def test_set_secondary_colors_initial_from_names_and_ids():
    red = Color.objects.create(name="Red", hex_value="#FF0000")
    blue = Color.objects.create(name="Blue", hex_value="#0000FF")
    form = DummyForm(data={"secondary_colors": ["Red", str(blue.id), "Unknown", ""]})
    mixin = FormDataMixin()

    mixin._set_secondary_colors_initial(form)

    initial_ids = form.fields["secondary_colors"].initial
    assert red.id in initial_ids
    assert blue.id in initial_ids
    assert len(initial_ids) == EXPECTED_SECONDARY_COLOR_COUNT


def test_ensure_country_code_in_cleaned_data_from_post():
    form = DummyForm(data={"country_code": "ES"})
    form.cleaned_data = {}
    mixin = FormDataMixin()

    mixin._ensure_country_code_in_cleaned_data(form)

    assert form.cleaned_data["country_code"] == "ES"


def test_ensure_country_code_in_cleaned_data_from_fkapi():
    form = DummyForm(data={})
    form.cleaned_data = {}
    mixin = FormDataMixin()
    mixin.fkapi_data = {"team_country": "BR"}

    mixin._ensure_country_code_in_cleaned_data(form)

    assert form.cleaned_data["country_code"] == "BR"


@pytest.mark.django_db
def test_ensure_main_color_in_cleaned_data_creates_color():
    form = DummyForm(data={"main_color": "green"})
    form.cleaned_data = {}
    mixin = FormDataMixin()

    mixin._ensure_main_color_in_cleaned_data(form)

    color = form.cleaned_data["main_color"]
    assert isinstance(color, Color)
    assert color.name == "GREEN"


@pytest.mark.django_db
def test_ensure_secondary_colors_in_cleaned_data_from_comma_string():
    form = DummyForm(data={"secondary_colors": "red, blue ,  "})
    form.cleaned_data = {}
    mixin = FormDataMixin()

    mixin._ensure_secondary_colors_in_cleaned_data(form)

    colors = form.cleaned_data["secondary_colors"]
    names = sorted(c.name for c in colors)
    assert names == ["BLUE", "RED"]


@pytest.mark.django_db
def test_ensure_form_cleaned_data_populates_all_fields():
    form = DummyForm(
        data={
            "country_code": "FR",
            "main_color": "navy",
            "secondary_colors": "white, red",
        },
    )
    form.cleaned_data = {}
    mixin = FormDataMixin()

    mixin._ensure_form_cleaned_data(form)

    assert form.cleaned_data["country_code"] == "FR"
    assert isinstance(form.cleaned_data["main_color"], Color)
    assert {c.name for c in form.cleaned_data["secondary_colors"]} == {"WHITE", "RED"}


def test_ensure_country_in_cleaned_data_priority_order():
    form = DummyForm(data={"country_code": "DE"})
    cleaned_data = {}
    mixin = FormDataMixin()
    mixin.fkapi_data = {"team_country": "IT"}

    mixin._ensure_country_in_cleaned_data(cleaned_data, "PL", form)

    assert cleaned_data["country_code"] == "PL"


def test_ensure_country_falls_back_to_form_data():
    form = DummyForm(data={"country_code": "ES"})
    mixin = FormDataMixin()

    cleaned_data_none = {}
    mixin._ensure_country_in_cleaned_data(cleaned_data_none, None, form)
    assert cleaned_data_none["country_code"] == "ES"

    cleaned_data_empty = {}
    mixin._ensure_country_in_cleaned_data(cleaned_data_empty, "", form)
    assert cleaned_data_empty["country_code"] == "ES"


def test_ensure_country_falls_back_to_fkapi_data():
    form = DummyForm(data={})
    cleaned_data = {}
    mixin = FormDataMixin()
    mixin.fkapi_data = {"team_country": "BR"}

    mixin._ensure_country_in_cleaned_data(cleaned_data, None, form)

    assert cleaned_data["country_code"] == "BR"


def test_ensure_country_no_value():
    form = DummyForm(data={})
    cleaned_data = {}
    mixin = FormDataMixin()

    mixin._ensure_country_in_cleaned_data(cleaned_data, None, form)

    assert "country_code" not in cleaned_data
