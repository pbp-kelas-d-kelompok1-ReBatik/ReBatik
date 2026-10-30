from django.urls import path

from . import views

app_name = "profiles"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("create/", views.create_profile, name="create"),
    path("edit/", views.edit_profile, name="edit"),
    path("delete/", views.delete_profile, name="delete"),
]