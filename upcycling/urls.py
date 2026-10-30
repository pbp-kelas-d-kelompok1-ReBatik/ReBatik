from django.urls import path
from . import views

app_name = "upcycling"

urlpatterns = [
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/assign/<uuid:pk>/", views.admin_assign_artisan, name="admin_assign_artisan"),
    path("artisan/", views.artisan_dashboard, name="artisan_dashboard"),
    path("artisan/<uuid:pk>/update/", views.artisan_update_request, name="artisan_update_request"),
    path("", views.request_list, name="request_list"),
    path("new/", views.request_create, name="request_create"),
    path("<uuid:pk>/submitted/", views.request_success, name="request_success"),
    path("<uuid:pk>/", views.request_detail, name="request_detail"),
    path("<uuid:pk>/edit/", views.request_update, name="request_update"),
    path("<uuid:pk>/delete/", views.request_delete, name="request_delete"),
    path("<uuid:pk>/approve-quote/", views.approve_quote, name="approve_quote"),
    path("<uuid:pk>/product-delivery/", views.submit_product_delivery, name="submit_product_delivery"),
    path(
        "<uuid:pk>/fabric-handoff/",
        views.submit_fabric_handoff,
        name="submit_fabric_handoff",
    ),
    path("<uuid:pk>/confirm-completion/", views.confirm_completion, name="confirm_completion"),
    path("<uuid:pk>/cancel/", views.cancel_request, name="cancel_request"),
]
