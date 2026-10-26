from django.urls import path
from . import views

app_name = "batik_custom"

urlpatterns = [
    path("", views.show_home,name="show_home"),
    path("fashion-preference/",views.fashion_preference, name="fashion_preference"),
    path("style-quiz/", views.style_quiz, name="style_quiz"),
    path("select-style/", views.select_style, name="select_style"),
    path("studio/", views.custom_studio, name="custom_studio"),
    path("explore_colors/",views.explore_colors, name="explore_colors"),
    path("select_style/",views.select_style,name="select_style")
]
