
from django.urls import path
from . import views

app_name = "donasi"

#mencegah proyek dgn banyak namespace tabrakan
urlpatterns = [
    path("", views.landing, name="landing"),
    path("form/", views.create, name="create"),
    path("riwayat/", views.history, name="history"),
]
