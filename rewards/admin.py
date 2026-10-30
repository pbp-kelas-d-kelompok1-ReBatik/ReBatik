from django.contrib import admin
from django import forms

from .models import PointTransaction, Reward, RewardRedemption


class RewardAdminForm(forms.ModelForm):
    class Meta:
        model = Reward
        fields = "__all__"

    def clean_reward_type(self):
        """Prevent changing the type of a reward that has been redeemed."""
        reward_type = self.cleaned_data["reward_type"]
        if self.instance.pk and self.instance.redemptions.exists() and reward_type != self.instance.reward_type:
            raise forms.ValidationError("Jenis reward tidak dapat diubah setelah pernah ditukar.")
        return reward_type

    def clean(self):
        cleaned = super().clean()
        reward_type = cleaned.get("reward_type")
        is_active = cleaned.get("is_active")
        discount_value = cleaned.get("discount_value")

        if reward_type == Reward.Type.PHYSICAL:
            if not self.instance.pk:
                self.add_error("reward_type", "Reward baru hanya dapat berupa voucher.")
            elif is_active:
                self.add_error(
                    "is_active",
                    "Reward fisik lama harus dinonaktifkan dan tidak dapat ditawarkan lagi.",
                )
        elif reward_type == Reward.Type.VOUCHER and is_active:
            if discount_value is None or discount_value <= 0:
                self.add_error(
                    "discount_value",
                    "Voucher aktif harus memiliki nilai diskon lebih dari nol.",
                )
        return cleaned


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    form = RewardAdminForm
    list_display = ("name", "reward_type", "points_required", "stock", "is_active")
    list_filter = ("reward_type", "is_active")
    search_fields = ("name", "description")


@admin.register(RewardRedemption)
class RewardRedemptionAdmin(admin.ModelAdmin):
    list_display = ("reward", "user", "points_spent", "status", "voucher_status", "redeemed_at")
    list_filter = ("status", "voucher_status", "reward__reward_type")
    search_fields = ("user__username", "user__email", "reward__name", "voucher_code")
    readonly_fields = (
        "user",
        "reward",
        "points_spent",
        "discount_value_snapshot",
        "status",
        "voucher_code",
        "voucher_status",
        "redeemed_at",
        "fulfilled_at",
    )
    fields = readonly_fields

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "points", "source_reference", "created_at")
    list_filter = ("kind", "created_at")
    search_fields = ("user__username", "source_reference", "description")
    readonly_fields = tuple(field.name for field in PointTransaction._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
