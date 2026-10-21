from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
    path("", views.show_home, name="show_home"),

    path("login/", views.login_user, name="login"),
    path("signup/", views.register, name="signup"),
    path("logout/", views.logout_user, name="logout"),

]
