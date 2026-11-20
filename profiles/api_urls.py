from django.urls import path

from profiles import api_views


app_name = "profile_api"

urlpatterns = [
    path(
        "",
        api_views.profile,
        name="profile",
    ),

    path(
        "settings/",
        api_views.profile_settings,
        name="profile-settings",
    ),
]