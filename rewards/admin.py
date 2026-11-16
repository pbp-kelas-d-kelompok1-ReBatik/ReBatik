from django.contrib import admin
from django.utils.html import format_html

from .forms import RewardAdminForm
from .models import PointTransaction, Reward, RewardRedemption


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    form = RewardAdminForm
    fieldsets = (
        ("Informasi voucher", {"fields": ("name", "description", "reward_type", "code_prefix")}),
        ("Penukaran", {"fields": ("points_required", "discount_value", "stock", "is_active")}),
        ("Gambar katalog", {"fields": ("image",)}),
    )
    list_display = ("name", "image_preview", "points_required", "discount_value", "stock", "is_active")
    list_filter = ("reward_type", "is_active")
    search_fields = ("name", "description")
    list_per_page = 25

    @admin.display(description="Gambar")
    def image_preview(self, obj):
        if not obj.image:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="width: 48px; height: 48px; object-fit: cover; border-radius: 6px;">',
            obj.image.url,
        )


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
