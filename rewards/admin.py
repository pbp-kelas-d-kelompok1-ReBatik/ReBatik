from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import PointTransaction, Reward, RewardRedemption
from .services import cancel_physical_redemption


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


class RewardRedemptionAdminForm(forms.ModelForm):
    class Meta:
        model = RewardRedemption
        fields = "__all__"

    def clean(self):
        """Validate redemption status changes and physical cancellation reasons."""
        cleaned = super().clean()
        if self.instance.pk:
            old = RewardRedemption.objects.select_related("reward").get(pk=self.instance.pk)
            new_status = cleaned.get("status")
            if old.status != new_status and old.status != RewardRedemption.Status.PENDING:
                self.add_error("status", "Penukaran yang sudah selesai atau dibatalkan bersifat final.")
            if new_status not in {RewardRedemption.Status.PENDING, RewardRedemption.Status.FULFILLED, RewardRedemption.Status.CANCELLED}:
                self.add_error("status", "Status penukaran tidak valid.")
            if old.reward.reward_type == Reward.Type.VOUCHER and new_status == RewardRedemption.Status.CANCELLED:
                self.add_error("status", "Voucher yang sudah diterbitkan tidak dapat dibatalkan.")
            if old.status == RewardRedemption.Status.PENDING and cleaned.get("status") == RewardRedemption.Status.CANCELLED:
                if old.reward.reward_type != Reward.Type.PHYSICAL:
                    self.add_error("status", "Voucher yang sudah diterbitkan tidak dapat dibatalkan.")
                if not cleaned.get("cancellation_reason", "").strip():
                    self.add_error("cancellation_reason", "Alasan pembatalan wajib diisi.")
        return cleaned


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    form = RewardAdminForm
    list_display = ("name", "reward_type", "points_required", "stock", "is_active")
    list_filter = ("reward_type", "is_active")
    search_fields = ("name", "description")


@admin.register(RewardRedemption)
class RewardRedemptionAdmin(admin.ModelAdmin):
    form = RewardRedemptionAdminForm
    list_display = ("reward", "user", "points_spent", "status", "voucher_status", "redeemed_at")
    list_filter = ("status", "voucher_status", "reward__reward_type")
    search_fields = ("user__username", "user__email", "reward__name", "voucher_code")
    readonly_fields = ("user", "reward", "points_spent", "voucher_code", "redeemed_at", "cancelled_at")
    fields = (
        "user", "reward", "points_spent", "status", "voucher_code", "voucher_status",
        "shipping_address", "redeemed_at", "fulfilled_at", "cancelled_at",
        "cancellation_reason", "cancelled_by",
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        """Apply cancellation refunds or mark fulfillment when saving a redemption.

        Cancellation ValueErrors are converted to Django ValidationErrors.
        """
        old_status = None
        if change:
            old_status = RewardRedemption.objects.values_list("status", flat=True).get(pk=obj.pk)
        if old_status == RewardRedemption.Status.PENDING and obj.status == RewardRedemption.Status.CANCELLED:
            try:
                cancel_physical_redemption(
                    obj,
                    admin_user=request.user,
                    reason=obj.cancellation_reason,
                )
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
            obj.refresh_from_db()
            return
        if old_status == RewardRedemption.Status.PENDING and obj.status == RewardRedemption.Status.FULFILLED:
            obj.fulfilled_at = obj.fulfilled_at or timezone.now()
        super().save_model(request, obj, form, change)


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
