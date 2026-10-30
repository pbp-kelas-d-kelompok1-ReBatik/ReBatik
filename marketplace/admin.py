from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import router, transaction
from django.db.models import F
from rewards.models import RewardRedemption

from .models import (
    ALLOWED_ORDER_STATUS_TRANSITIONS,
    DropOffPoint,
    Order,
    OrderStatusHistory,
    Product,
)


@admin.action(description="Sembunyikan produk terpilih dari katalog")
def hide_selected_products(modeladmin, request, queryset):
    queryset.update(is_deleted=True)


@admin.action(description="Tampilkan kembali produk terpilih di katalog")
def restore_selected_products(modeladmin, request, queryset):
    queryset.update(is_deleted=False)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "motif",
        "category",
        "price",
        "stock",
        "artisan_origin",
        "is_deleted",
        "created_at",
    )
    list_filter = ("category", "is_deleted")
    list_editable = ("stock",)
    search_fields = ("name", "motif", "material_source", "artisan_origin")
    readonly_fields = ("created_at", "updated_at")
    actions = (hide_selected_products, restore_selected_products)


@admin.register(DropOffPoint)
class DropOffPointAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "operating_hours", "latitude", "longitude")
    list_filter = ("city",)
    search_fields = ("name", "address", "city")


class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = "__all__"

    def clean_status(self):
        """Validate that the requested status follows allowed order transitions."""
        new_status = self.cleaned_data["status"]
        if self.instance._state.adding or new_status == self.instance.status:
            return new_status

        if new_status not in ALLOWED_ORDER_STATUS_TRANSITIONS.get(
            self.instance.status,
            set(),
        ):
            raise ValidationError(
                "Perubahan status pesanan tersebut tidak diizinkan."
            )
        return new_status


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    fields = ("from_status", "to_status", "changed_by", "changed_at")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        """Keep status history entries read-only in the admin interface."""
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    inlines = (OrderStatusHistoryInline,)
    list_display = (
        "reference_code",
        "product_name",
        "quantity",
        "total_price",
        "reward_redemption",
        "discount_amount",
        "user",
        "delivery_method",
        "status",
        "created_at",
    )
    list_filter = ("status", "delivery_method")
    search_fields = (
        "user__username",
        "user__email",
        "product_name",
        "whatsapp",
        "address",
    )
    readonly_fields = (
        "user",
        "product",
        "product_name",
        "unit_price",
        "quantity",
        "total_price",
        "reward_redemption",
        "discount_amount",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        """Orders are created through checkout so stock is reserved atomically."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Keep order records immutable in admin; use CANCELLED instead."""
        return False

    def changeform_view(
        self,
        request,
        object_id=None,
        form_url="",
        extra_context=None,
    ):
        """Lock an edited order while its status, stock, and history are saved."""
        if request.method != "POST" or object_id is None:
            return super().changeform_view(
                request,
                object_id,
                form_url,
                extra_context,
            )

        using = router.db_for_write(self.model)
        with transaction.atomic(using=using):
            existing_order = self.get_object(request, object_id)
            if existing_order is not None:
                try:
                    self.get_queryset(request).using(using).select_for_update().get(
                        pk=existing_order.pk
                    )
                except self.model.DoesNotExist:
                    pass
            return super().changeform_view(
                request,
                object_id,
                form_url,
                extra_context,
            )

    def save_model(self, request, obj, form, change):
        """Record status history and restore product stock when an admin cancels an order."""
        previous_status = None
        if change:
            previous_status = Order.objects.values_list(
                "status",
                flat=True,
            ).get(pk=obj.pk)

        super().save_model(request, obj, form, change)

        if previous_status != obj.status:
            if (
                obj.status == Order.Status.CANCELLED
                and previous_status != Order.Status.CANCELLED
            ):
                Product.objects.select_for_update().filter(pk=obj.product_id).update(
                    stock=F("stock") + obj.quantity
                )
                if obj.reward_redemption_id:
                    redemption = RewardRedemption.objects.select_for_update().get(
                        pk=obj.reward_redemption_id
                    )
                    redemption.voucher_status = RewardRedemption.VoucherStatus.AVAILABLE
                    redemption.save(update_fields=("voucher_status",))
            OrderStatusHistory.objects.create(
                order=obj,
                from_status=previous_status or "",
                to_status=obj.status,
                changed_by=request.user,
            )
