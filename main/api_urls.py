from django.urls import path

from main import api_views

app_name = "api_auth"

urlpatterns = [
    path("csrf/", api_views.csrf, name="csrf"),
    path("login/", api_views.login_api, name="login"),
    path("register/", api_views.register_api, name="register"),
    path("logout/", api_views.logout_api, name="logout"),
    path("me/", api_views.me, name="me"),
]
