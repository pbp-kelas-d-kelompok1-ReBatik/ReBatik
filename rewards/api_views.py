from django.db import transaction
from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, Throttled, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Reward
from .serializers import (
    AdminVoucherSerializer, PointTransactionSerializer, RewardRedemptionSerializer, VoucherSerializer,
)
from .services import (
    InsufficientPoints, RewardUnavailable, available_vouchers, consume_redemption_attempt, get_available_points,
    point_history, points_overview_data, redeem_reward, user_vouchers,
)


class RewardsSessionMixin:
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]


class PointsOverview(RewardsSessionMixin, APIView):
    def get(self, request):
        data = points_overview_data(request.user)
        context = {"request": request}
        data["recent_transactions"] = PointTransactionSerializer(data["recent_transactions"], many=True).data
        data["featured_vouchers"] = VoucherSerializer(data["featured_vouchers"], many=True, context=context).data
        return Response(data)


class HistoryPagination(PageNumberPagination):
    page_size = 6


class PointHistory(RewardsSessionMixin, generics.ListAPIView):
    serializer_class = PointTransactionSerializer
    pagination_class = HistoryPagination

    def get_queryset(self):
        direction = self.request.query_params.get("type", "all")
        if direction not in {"all", "in", "out"}:
            raise ValidationError({"type": "Gunakan all, in, atau out."})
        return point_history(self.request.user, direction)


class VoucherCatalog(RewardsSessionMixin, generics.ListAPIView):
    serializer_class = VoucherSerializer

    def get_queryset(self):
        return available_vouchers()


class MyVouchers(RewardsSessionMixin, generics.ListAPIView):
    serializer_class = RewardRedemptionSerializer

    def get_queryset(self):
        return user_vouchers(self.request.user)


class RedeemVoucher(RewardsSessionMixin, APIView):
    def post(self, request, reward_id):
        allowed, retry_after = consume_redemption_attempt(request.user)
        if not allowed:
            raise Throttled(wait=retry_after)

        try:
            redemption = redeem_reward(request.user, reward_id)
        except Reward.DoesNotExist:
            raise NotFound("Voucher tidak tersedia.") from None
        except (InsufficientPoints, RewardUnavailable) as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response({
            "redemption": RewardRedemptionSerializer(redemption, context={"request": request}).data,
            "available_points": get_available_points(request.user),
        }, status=status.HTTP_201_CREATED)


class VoucherManagementPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return any(request.user.has_perm(perm) for perm in view.read_permissions)
        if request.method == "POST":
            return request.user.has_perm("rewards.add_reward")
        return request.user.has_perm("rewards.change_reward")


class AdminVoucherAPI(RewardsSessionMixin):
    permission_classes = [IsAdminUser, VoucherManagementPermission]
    read_permissions = ("rewards.view_reward", "rewards.add_reward")
    serializer_class = AdminVoucherSerializer
    queryset = Reward.objects.filter(reward_type=Reward.Type.VOUCHER).order_by("-pk")


class AdminVoucherList(AdminVoucherAPI, generics.ListCreateAPIView):
    pass


class AdminVoucherDetail(AdminVoucherAPI, generics.RetrieveUpdateAPIView):
    read_permissions = (*AdminVoucherAPI.read_permissions, "rewards.change_reward")
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.method == "PATCH":
            return queryset.select_for_update()
        return queryset

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
