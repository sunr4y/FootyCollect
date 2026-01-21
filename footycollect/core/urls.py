import logging

from django.urls import path

from . import autocomplete

logger = logging.getLogger(__name__)

logger.info("Loading core URLs")

app_name = "core"
urlpatterns = [
    path(
        "brand-autocomplete/",
        autocomplete.BrandAutocomplete.as_view(),
        name="brand-autocomplete",
    ),
    path(
        "country-autocomplete/",
        autocomplete.CountryAutocomplete.as_view(),
        name="country-autocomplete",
    ),
    path(
        "club-autocomplete/",
        autocomplete.ClubAutocomplete.as_view(),
        name="club-autocomplete",
    ),
    path(
        "season-autocomplete/",
        autocomplete.SeasonAutocomplete.as_view(),
        name="season-autocomplete",
    ),
    path(
        "competition-autocomplete/",
        autocomplete.CompetitionAutocomplete.as_view(),
        name="competition-autocomplete",
    ),
]

logger.info("URLs registered: %s", [url.pattern for url in urlpatterns])
