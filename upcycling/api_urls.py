from django.urls import path

from . import api_views

app_name = "upcycling_api"

urlpatterns = [
    path("requests/", api_views.my_request_list, name="request-list"),
    path("requests/<uuid:pk>/", api_views.my_request_detail, name="request-detail")
]