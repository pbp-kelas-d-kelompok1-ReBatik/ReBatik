from django.urls import path

from . import api_views

app_name = "api_rewards"

urlpatterns = [
    path("overview/", api_views.PointsOverview.as_view(), name="overview"),
    path("history/", api_views.PointHistory.as_view(), name="history"),
    path("catalog/", api_views.VoucherCatalog.as_view(), name="catalog"),
    path("catalog/<int:reward_id>/redeem/", api_views.RedeemVoucher.as_view(), name="redeem"),
    path("vouchers/", api_views.MyVouchers.as_view(), name="my-vouchers"),
    path("admin/vouchers/", api_views.AdminVoucherList.as_view(), name="admin-vouchers"),
    path("admin/vouchers/<int:pk>/", api_views.AdminVoucherDetail.as_view(), name="admin-voucher-detail"),
]
