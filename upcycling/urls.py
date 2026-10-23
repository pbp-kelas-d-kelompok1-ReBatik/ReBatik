from django.urls import path
from . import views

app_name = "upcycling"

urlpatterns = [
    path("", views.request_list, name="request_list"),
    path("new/", views.request_create, name="request_create"),
    path("<uuid:pk>/submitted/", views.request_success, name="request_success"),
    path("<uuid:pk>/", views.request_detail, name="request_detail"),
    path("<uuid:pk>/edit/", views.request_update, name="request_update"),
    path("<uuid:pk>/delete/", views.request_delete, name="request_delete"),
]
