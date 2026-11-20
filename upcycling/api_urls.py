from django.urls import path

from . import api_views

app_name = "upcycling_api"

urlpatterns = [
    path("requests/", api_views.my_request_list, name="request-list"),
    path(
        "artisan/requests/",
        api_views.artisan_request_list_api,
        name="artisan-request-list",
    ),
    path(
        "admin/requests/",
        api_views.admin_request_list_api,
        name="admin-request-list",
    ),
    path("requests/<uuid:pk>/", api_views.my_request_detail, name="request-detail"),
    path(
        "requests/<uuid:pk>/artisan-action/",
        api_views.artisan_request_action_api,
        name="request-artisan-action",
    ),
    path(
        "admin/requests/<uuid:pk>/assign-artisan/",
        api_views.admin_assign_artisan_api,
        name="admin-assign-artisan",
    ),
    path(
        "requests/<uuid:pk>/fabric-handoff/",
        api_views.submit_fabric_handoff_api,
        name="request-fabric-handoff",
    ),
    path(
        "requests/<uuid:pk>/approve-quote/",
        api_views.approve_quote_api,
        name="request-approve-quote",
    ),
    path(
        "requests/<uuid:pk>/product-delivery/",
        api_views.submit_product_delivery_api,
        name="request-product-delivery",
    ),
    path(
        "requests/<uuid:pk>/confirm-completion/",
        api_views.confirm_completion_api,
        name="request-confirm-completion",
    ),
    path(
        "requests/<uuid:pk>/cancel/",
        api_views.cancel_request_api,
        name="request-cancel",
    ),
]
