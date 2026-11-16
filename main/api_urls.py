from django.urls import path

from main import api_views

app_name = "api_auth"

urlpatterns = [
    path("csrf/", api_views.csrf, name="csrf"),
    path("login/", api_views.login_api, name="login"),
    path("register/", api_views.register_api, name="register"),
    path("logout/", api_views.logout_api, name="logout"),
    path("me/", api_views.me, name="me"),
    # Notifikasi (login)
    path("notifications/", api_views.notification_list, name="notification-list"),
    path("notifications/read-all/", api_views.notification_read_all, name="notification-read-all"),
    path("notifications/<int:pk>/read/", api_views.notification_read, name="notification-read"),
]
