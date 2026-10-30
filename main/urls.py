from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
    path("", views.show_home, name="show_home"),

    path("login/", views.login_user, name="login"),
    path("signup/", views.register, name="signup"),
    path("logout/", views.logout_user, name="logout"),
    path("search/suggestions/", views.navbar_search, name="navbar_search"),
    path("search/save/", views.save_search, name="save_search"),
    path("search/clear/", views.clear_search_history, name="clear_search_history"),
    path("notifications/", views.notification_list, name="notifications"),
    path("notifications/<int:pk>/read/", views.notification_mark_read, name="notification_mark_read"),
    path("notifications/read-all/", views.notification_mark_all_read, name="notification_mark_all_read"),

]
