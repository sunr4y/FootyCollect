from django.urls import path

from . import views

app_name = "footycollect_api"

urlpatterns = [
    path("clubs/search/", views.search_clubs, name="search_clubs"),
    path("kit/<int:kit_id>/", views.get_kit_details, name="kit_details"),
    path("kits/search/", views.search_kits, name="search_kits"),
    path("clubs/<int:club_id>/seasons/", views.get_club_seasons, name="club_seasons"),
    path(
        "clubs/<int:club_id>/seasons/<int:season_id>/kits/",
        views.get_club_kits,
        name="club_season_kits",
    ),
]
