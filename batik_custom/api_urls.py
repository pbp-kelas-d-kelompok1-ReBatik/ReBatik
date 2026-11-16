from django.urls import path

from batik_custom import api_views

app_name = "api_custom"

urlpatterns = [
    # Katalog publik
    path("styles/", api_views.style_list, name="style-list"),
    path("palettes/", api_views.palette_list, name="palette-list"),
    path("motifs/", api_views.motif_list, name="motif-list"),
    path("motifs/<int:motif_id>/", api_views.motif_detail, name="motif-detail"),
    path("product-options/", api_views.product_option_list, name="product-option-list"),
    # Desain tersimpan (login)
    path("designs/", api_views.design_list, name="design-list"),
    path("designs/<int:design_id>/", api_views.design_detail, name="design-detail"),
    # Pesanan (login)
    path("orders/", api_views.order_list, name="order-list"),
    path("orders/<int:order_id>/", api_views.order_detail, name="order-detail"),
]
