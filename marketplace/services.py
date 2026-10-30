from django.db import transaction
from django.db.models import F

from .models import (
    ALLOWED_ORDER_STATUS_TRANSITIONS,
    MAX_ORDER_QUANTITY,
    Order,
    OrderStatusHistory,
    Product,
)


class OutOfStock(Exception):
    """Raised when a product does not have enough stock for an order."""

    def __init__(self, available_stock):
        self.available_stock = available_stock
        super().__init__(f"Stok tersedia: {available_stock}")


class OrderTransitionNotAllowed(Exception):
    """Raised when an order status change violates workflow transition rules."""


@transaction.atomic
def place_order(
    user,
    product_id,
    *,
    quantity,
    delivery_method,
    dropoff_point=None,
    address="",
    whatsapp,
    notes="",
):
    """Atomically reserve product stock and create a buyer order with history."""
    if quantity < 1 or quantity > MAX_ORDER_QUANTITY:
        raise ValueError(f"Jumlah pesanan harus antara 1 dan {MAX_ORDER_QUANTITY}.")

    product = Product.objects.select_for_update().get(
        pk=product_id,
        is_deleted=False,
    )
    if product.stock < quantity:
        raise OutOfStock(product.stock)

    product.stock = F("stock") - quantity
    product.save(update_fields=["stock", "updated_at"])

    order = Order.objects.create(
        user=user,
        product=product,
        product_name=product.name,
        unit_price=product.price,
        quantity=quantity,
        total_price=product.price * quantity,
        delivery_method=delivery_method,
        dropoff_point=(
            dropoff_point
            if delivery_method == Order.DeliveryMethod.DROP_OFF
            else None
        ),
        address=(
            address.strip()
            if delivery_method == Order.DeliveryMethod.KURIR
            else ""
        ),
        whatsapp=whatsapp,
        notes=(notes or "").strip(),
        status=Order.Status.PENDING,
    )
    OrderStatusHistory.objects.create(
        order=order,
        to_status=order.status,
        changed_by=user,
    )
    return order


@transaction.atomic
def cancel_order(order_id, *, by_user, require_owner=True):
    """Cancel an order atomically, restore product stock, and record history."""
    filters = {"pk": order_id}
    if require_owner:
        filters["user"] = by_user

    order = Order.objects.select_for_update().get(**filters)
    previous_status = order.status

    if require_owner:
        can_cancel = previous_status == Order.Status.PENDING
    else:
        can_cancel = Order.Status.CANCELLED in ALLOWED_ORDER_STATUS_TRANSITIONS.get(
            previous_status,
            set(),
        )

    if not can_cancel:
        raise OrderTransitionNotAllowed(
            "Pesanan ini tidak dapat dibatalkan pada status saat ini."
        )

    Product.objects.select_for_update().filter(pk=order.product_id).update(
        stock=F("stock") + order.quantity
    )

    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order,
        from_status=previous_status,
        to_status=Order.Status.CANCELLED,
        changed_by=by_user,
    )
    return order

