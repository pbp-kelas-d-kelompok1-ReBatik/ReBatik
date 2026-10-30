"""URL routes for points overview and history pages."""

from django.urls import path

from . import views

app_name = "rewards"

urlpatterns = [
    path("", views.points_overview, name="overview"),
    path("history/", views.transaction_history, name="history"),
    path("catalog/", views.reward_catalog, name="catalog"),
    path("vouchers/", views.my_vouchers, name="vouchers"),
    path("admin/vouchers/", views.admin_vouchers, name="admin_vouchers"),
    path("catalog/<int:reward_id>/redeem/", views.redeem_reward_view, name="redeem"),
]
