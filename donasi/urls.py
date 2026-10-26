
from django.urls import path
from . import views

app_name = "donasi"

urlpatterns = [
    path("", views.donasi_landing, name="landing"),
    path("form/", views.donasi_create, name="create"),
    path("riwayat/", views.donasi_history, name="history"),
]
