"""Serializer DRF untuk API Marketplace & Drop-off Point (aplikasi Flutter).

Validasi input tulis (produk dan checkout) tetap memakai ``ProductForm`` dan
``CheckoutForm`` di ``api_views`` agar aturan web dan mobile selalu sama.
Serializer di sini hanya membentuk respons JSON.
"""
from rest_framework import serializers

from .models import (
    DropOffPoint,
    Order,
    OrderStatusHistory,
    Product,
)


class ProductSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "motif", "category", "category_display", "description",
            "badge_status", "material_source", "artisan_origin", "price", "stock",
            "is_in_stock", "image_url", "is_deleted", "created_at", "updated_at",
        ]
        read_only_fields = fields


class DropOffPointSerializer(serializers.ModelSerializer):
    accepted_items = serializers.ListField(
        source="accepted_items_list", child=serializers.CharField(), read_only=True,
    )
    whatsapp_url = serializers.CharField(read_only=True)
    maps_url = serializers.SerializerMethodField()

    class Meta:
        model = DropOffPoint
        fields = [
            "id", "code", "name", "address", "city", "province", "operating_hours",
            "latitude", "longitude", "phone", "accepted_items", "whatsapp_url",
            "maps_url",
        ]
        read_only_fields = fields

    def get_maps_url(self, obj):
        if obj.latitude is None or obj.longitude is None:
            return None
        return f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    from_status_display = serializers.CharField(source="get_from_status_display", read_only=True)
    to_status_display = serializers.CharField(source="get_to_status_display", read_only=True)

    class Meta:
        model = OrderStatusHistory
        fields = [
            "from_status", "from_status_display", "to_status", "to_status_display",
            "changed_at",
        ]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    reference_code = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    delivery_method_display = serializers.CharField(
        source="get_delivery_method_display", read_only=True,
    )
    subtotal_price = serializers.IntegerField(read_only=True)
    product_image_url = serializers.SerializerMethodField()
    voucher_code = serializers.SerializerMethodField()
    dropoff_point = DropOffPointSerializer(read_only=True)
    can_cancel = serializers.SerializerMethodField()
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "reference_code", "product", "product_name", "product_image_url",
            "unit_price", "quantity", "subtotal_price", "discount_amount",
            "total_price", "voucher_code", "delivery_method",
            "delivery_method_display", "dropoff_point", "address", "whatsapp",
            "notes", "status", "status_display", "can_cancel", "status_history",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_product_image_url(self, obj):
        return obj.product.image_url or ""

    def get_voucher_code(self, obj):
        if obj.reward_redemption_id is None:
            return None
        return obj.reward_redemption.voucher_code

    def get_can_cancel(self, obj):
        # Pembeli hanya boleh membatalkan pesanan yang masih menunggu konfirmasi,
        # sama seperti aturan cancel_order(require_owner=True).
        return obj.status == Order.Status.PENDING
