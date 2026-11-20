from rest_framework import serializers

from .forms import normalize_code_prefix
from .models import PointTransaction, Reward, RewardRedemption


class VoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = (
            "id", "name", "description", "reward_type", "points_required",
            "stock", "discount_value", "image",
        )
        read_only_fields = fields


class AdminVoucherSerializer(serializers.ModelSerializer):
    reward_type = serializers.ChoiceField(choices=[Reward.Type.VOUCHER], default=Reward.Type.VOUCHER)
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = Reward
        fields = (*VoucherSerializer.Meta.fields, "code_prefix", "is_active")

    def validate_code_prefix(self, value):
        return normalize_code_prefix(value)

    def validate(self, attrs):
        active = attrs.get("is_active", getattr(self.instance, "is_active", True))
        discount = attrs.get("discount_value", getattr(self.instance, "discount_value", None))
        if active and (discount is None or discount <= 0):
            raise serializers.ValidationError({
                "discount_value": "Voucher aktif harus memiliki nilai diskon lebih dari nol."
            })
        return attrs


class PointTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointTransaction
        fields = ("id", "kind", "points", "description", "weight_kg", "created_at", "reward_redemption")
        read_only_fields = fields


class RewardRedemptionSerializer(serializers.ModelSerializer):
    reward = VoucherSerializer(read_only=True)

    class Meta:
        model = RewardRedemption
        fields = (
            "id", "reward", "points_spent", "discount_value_snapshot", "status",
            "voucher_code", "voucher_status", "redeemed_at", "fulfilled_at",
        )
        read_only_fields = fields
