from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.http import QueryDict

from footycollect.collection.factories import CompetitionFactory
from footycollect.collection.models import Competition
from footycollect.collection.views.jersey.mixins.fkapi_data_mixin import FKAPIDataMixin

COMP_ID_EXISTING = 10
COMP_ID_NEW = 20


def make_request(initial=None):
    qd = QueryDict("", mutable=True)
    if initial:
        for key, value in initial.items():
            if isinstance(value, list):
                qd.setlist(key, value)
            else:
                qd[key] = value
    return SimpleNamespace(POST=qd)


def test_make_post_mutable_on_querydict_preserves_data_and_allows_changes():
    mixin = FKAPIDataMixin()
    request = make_request({"kit_id": "123"})
    request.POST._mutable = False  # type: ignore[attr-defined]

    mixin._make_post_mutable(request)

    assert request.POST._mutable  # type: ignore[attr-defined]
    assert request.POST["kit_id"] == "123"
    request.POST["extra"] = "ok"
    assert request.POST["extra"] == "ok"


@pytest.mark.django_db
def test_process_competitions_from_api_creates_and_updates_competitions():
    mixin = FKAPIDataMixin()
    existing = CompetitionFactory(name="Existing Comp", id_fka=None)
    request = make_request()

    competitions = [
        {"id": COMP_ID_EXISTING, "name": existing.name},
        {"id": COMP_ID_NEW, "name": "New Competition"},
        {"id": None, "name": ""},  # ignored
        "not-a-dict",  # ignored
    ]

    mixin._process_competitions_from_api(competitions, request)

    assert "competitions" in request.POST
    stored_ids = {int(value) for value in request.POST["competitions"].split(",")}

    existing.refresh_from_db()
    assert existing.id_fka == COMP_ID_EXISTING
    assert existing.id in stored_ids

    assert Competition.objects.filter(name="New Competition", id_fka=COMP_ID_NEW).exists()


def test_extract_secondary_colors_supports_multiple_formats():
    mixin = FKAPIDataMixin()

    result_list = mixin._extract_secondary_colors({"secondary_color": [{"name": "RED"}, {"name": "BLUE"}]})
    assert result_list == ["RED", "BLUE"]

    result_single = mixin._extract_secondary_colors({"secondary_color": {"name": "YELLOW"}})
    assert result_single == ["YELLOW"]

    result_from_colors = mixin._extract_secondary_colors(
        {
            "colors": [
                {"name": "MAIN"},
                {"name": "ACCENT1"},
                {"name": "ACCENT2"},
            ],
        },
    )
    assert result_from_colors == ["ACCENT1", "ACCENT2"]

    assert mixin._extract_secondary_colors({}) == []


def test_merge_main_color_uses_primary_or_first_color_and_respects_existing_post():
    mixin = FKAPIDataMixin()

    request = make_request({"main_color": "KEEP"})
    mixin._merge_main_color({"primary_color": {"name": "IGNORED"}}, request)
    assert request.POST["main_color"] == "KEEP"

    request2 = make_request()
    mixin._merge_main_color({"primary_color": {"name": "RED"}}, request2)
    assert request2.POST["main_color"] == "RED"

    request3 = make_request()
    mixin._merge_main_color({"colors": [{"name": "BLUE"}]}, request3)
    assert request3.POST["main_color"] == "BLUE"


def test_merge_secondary_colors_uses_extracted_values_and_respects_existing_post():
    mixin = FKAPIDataMixin()

    request = make_request()
    request.POST.setlist("secondary_colors", ["EXISTING"])
    mixin._merge_secondary_colors({"secondary_color": [{"name": "GREEN"}]}, request)
    assert request.POST.getlist("secondary_colors") == ["EXISTING"]

    request2 = make_request()
    mixin._merge_secondary_colors({"secondary_color": [{"name": "GREEN"}, {"name": "WHITE"}]}, request2)
    assert request2.POST.getlist("secondary_colors") == ["GREEN", "WHITE"]


def test_merge_country_sets_country_code_when_missing_and_respects_existing():
    mixin = FKAPIDataMixin()

    request = make_request()
    mixin._merge_country({"team": {"country": "ES"}}, request)
    assert request.POST["country_code"] == "ES"

    request2 = make_request({"country_code": "PL"})
    mixin._merge_country({"team": {"country": "ES"}}, request2)
    assert request2.POST["country_code"] == "PL"


def test_merge_fkapi_data_to_post_sets_cached_data_attribute():
    mixin = FKAPIDataMixin()
    request = make_request()

    kit_data = {
        "primary_color": {"name": "RED"},
        "secondary_color": [{"name": "BLUE"}],
        "team": {"country": "ES"},
        "competition": [],
    }

    mixin._merge_fkapi_data_to_post(kit_data, request)

    assert request._fkapi_kit_data == kit_data  # type: ignore[attr-defined]


def test_fetch_and_merge_fkapi_data_skips_invalid_kit_id():
    mixin = FKAPIDataMixin()
    request = make_request({"kit_id": "not-an-int"})

    with patch("footycollect.api.client.FKAPIClient") as mock_client:
        client_instance = mock_client.return_value
        mixin._fetch_and_merge_fkapi_data(request)

    client_instance.get_kit_details.assert_not_called()
    assert not hasattr(request, "_fkapi_kit_data")


def test_fetch_and_merge_fkapi_data_merges_when_kit_id_valid():
    mixin = FKAPIDataMixin()
    request = make_request({"kit_id": "123"})

    kit_data = {
        "primary_color": {"name": "RED"},
        "secondary_color": [{"name": "BLUE"}],
        "team": {"country": "ES"},
        "competition": [],
    }

    with patch("footycollect.api.client.FKAPIClient") as mock_client:
        client_instance = mock_client.return_value
        client_instance.get_kit_details.return_value = kit_data

        mixin._fetch_and_merge_fkapi_data(request)

    assert request.POST["main_color"] == "RED"
    assert request.POST.getlist("secondary_colors") == ["BLUE"]
    assert request.POST["country_code"] == "ES"
    assert request._fkapi_kit_data == kit_data  # type: ignore[attr-defined]
