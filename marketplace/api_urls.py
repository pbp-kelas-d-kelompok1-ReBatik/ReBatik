from django.urls import path

from marketplace import api_views

app_name = "api_marketplace"

urlpatterns = [
    # Produk
    path("products/", api_views.product_list, name="product-list"),
    path("products/<int:pk>/", api_views.product_detail, name="product-detail"),
    path("products/<int:pk>/restore/", api_views.product_restore, name="product-restore"),
    path("categories/", api_views.category_list, name="category-list"),
    # Drop-off Point
    path("dropoff-points/", api_views.dropoff_point_list, name="dropoff-list"),
    path("dropoff-points/cities/", api_views.dropoff_city_list, name="dropoff-city-list"),
    path("dropoff-points/<int:pk>/", api_views.dropoff_point_detail, name="dropoff-detail"),
    # Pesanan (login)
    path("orders/", api_views.order_list, name="order-list"),
    path("orders/<uuid:pk>/", api_views.order_detail, name="order-detail"),
    path("orders/<uuid:pk>/cancel/", api_views.order_cancel, name="order-cancel"),
    path("vouchers/", api_views.voucher_list, name="voucher-list"),
]
