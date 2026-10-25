from django.urls import path
from . import views

app_name = "batik_story"

urlpatterns = [
    path("", views.show_home, name="show_home"),
    path("BatikMotif/", views.show_batik_story, name="show_batik_story"),
    path("add_batik/", views.add_batik, name="add_batik"),
    path("story/<uuid:id_story>/delete/", views.delete_story,name="delete_story")

]
