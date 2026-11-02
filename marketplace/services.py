from django.db import transaction
from django.db.models import F

from .models import (
    ALLOWED_ORDER_STATUS_TRANSITIONS,
    MAX_ORDER_QUANTITY,
    Order,
    OrderStatusHistory,
    Product,
)
from rewards.models import Reward, RewardRedemption


class OutOfStock(Exception):
    """Raised when a product does not have enough stock for an order."""

    def __init__(self, available_stock):
        self.available_stock = available_stock
        super().__init__(f"Stok tersedia: {available_stock}")


class OrderTransitionNotAllowed(Exception):
    """Raised when an order status change violates workflow transition rules."""


class VoucherUnavailable(Exception):
    """Raised when a voucher cannot be applied to an order."""


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
    voucher_code="",
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

    redemption = None
    discount_amount = 0
    subtotal = product.price * quantity
    if voucher_code:
        redemption = (
            RewardRedemption.objects.select_for_update()
            .select_related("reward")
            .filter(
                user=user,
                voucher_code__iexact=voucher_code.strip(),
                reward__reward_type=Reward.Type.VOUCHER,
                status=RewardRedemption.Status.FULFILLED,
                voucher_status=RewardRedemption.VoucherStatus.AVAILABLE,
            )
            .first()
        )
        if redemption is None:
            raise VoucherUnavailable("Kode voucher tidak valid atau sudah digunakan.")
        voucher_value = redemption.discount_value_snapshot or redemption.reward.discount_value
        if voucher_value is None or voucher_value <= 0:
            raise VoucherUnavailable("Voucher belum dikonfigurasi dengan benar.")
        discount_amount = min(int(voucher_value), subtotal)

    product.stock = F("stock") - quantity
    product.save(update_fields=["stock", "updated_at"])

    order = Order.objects.create(
        user=user,
        product=product,
        product_name=product.name,
        unit_price=product.price,
        quantity=quantity,
        total_price=subtotal - discount_amount,
        reward_redemption=redemption,
        discount_amount=discount_amount,
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
    if redemption is not None:
        redemption.voucher_status = RewardRedemption.VoucherStatus.USED
        redemption.save(update_fields=("voucher_status",))
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

    if order.reward_redemption_id:
        redemption = RewardRedemption.objects.select_for_update().get(
            pk=order.reward_redemption_id
        )
        redemption.voucher_status = RewardRedemption.VoucherStatus.AVAILABLE
        redemption.save(update_fields=("voucher_status",))

    OrderStatusHistory.objects.create(
        order=order,
        from_status=previous_status,
        to_status=Order.Status.CANCELLED,
        changed_by=by_user,
    )
    return order

