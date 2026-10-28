
from django.urls import path
from . import views

app_name = "impact_tracker"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
