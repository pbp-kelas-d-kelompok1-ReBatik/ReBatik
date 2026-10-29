from django.urls import path

from . import views

app_name = "marketplace"

urlpatterns = [
    path("", views.product_list, name="home"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    path("product/<int:pk>/checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<uuid:pk>/", views.order_detail, name="order_detail"),
    path("orders/<uuid:pk>/success/", views.order_success, name="order_success"),
    path("orders/<uuid:pk>/cancel/", views.order_cancel, name="order_cancel"),
    path("manage/", views.manage_product_list, name="manage_product_list"),
    path("manage/new/", views.manage_product_create, name="manage_product_create"),
    path(
        "manage/<int:pk>/edit/",
        views.manage_product_update,
        name="manage_product_update",
    ),
    path(
        "manage/<int:pk>/delete/",
        views.manage_product_delete,
        name="manage_product_delete",
    ),
    path(
        "manage/<int:pk>/restore/",
        views.manage_product_restore,
        name="manage_product_restore",
    ),
    path("drop-off/", views.dropoff_list, name="dropoff"),
    path("api/regions/", views.regions_api, name="regions_api"),
]
