from django.urls import path

from footycollect.users.views import (
    user_detail_view,
    user_item_list_view,
    user_redirect_view,
    user_update_view,
)

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<str:username>/items/", view=user_item_list_view, name="user_items"),
    path("<str:username>/", view=user_detail_view, name="detail"),
]
