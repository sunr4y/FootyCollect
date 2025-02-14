from django.urls import path
from . import autocomplete
import logging

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
    # path(
    #     "club-autocomplete/",
    #     autocomplete.ClubAutocomplete.as_view(),
    #     name="club-autocomplete",
    # ),
]

logger.info(f"URLs registered: {[url.pattern for url in urlpatterns]}") 