"""URL routes for points overview and history pages."""

from django.urls import path

from . import views

app_name = "rewards"

urlpatterns = [
    path("", views.points_overview, name="overview"),
    path("history/", views.transaction_history, name="history"),
]
