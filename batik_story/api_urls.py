from django.urls import path

from batik_story import api_views

app_name = "api_story"

urlpatterns = [
    path("motifs/", api_views.motif_list, name="motif-list"),
    path("motifs/<uuid:motif_id>/", api_views.motif_detail, name="motif-detail"),
    path("motifs/<uuid:motif_id>/favorite/", api_views.motif_favorite, name="motif-favorite"),
    path("origins/", api_views.origin_list, name="origin-list"),
]
