"""Business rules for points, reward redemption, and balances."""

import uuid
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import PointTransaction, Reward, RewardRedemption


class InsufficientPoints(ValueError):
    pass


class RewardUnavailable(ValueError):
    pass


def calculate_donation_points(weight_kg):
    try:
        weight = Decimal(str(weight_kg))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Donation weight must be a positive number.") from None
    if not weight.is_finite() or weight <= 0:
        raise ValueError("Donation weight must be a positive number.")
    if weight < Decimal("0.5"):
        return 50
    if weight <= Decimal("2"):
        return 100
    if weight <= Decimal("5"):
        return 200
    return 300


def _existing_or_create(
    user,
    *,
    kind,
    reference,
    points,
    description,
    weight_kg=None,
    upcycling_request=None,
    donation=None,
    reward_redemption=None,
):
    source_count = sum(source is not None for source in (upcycling_request, donation, reward_redemption))
    if source_count > 1:
        raise ValueError("A point transaction can only reference one source.")
    if upcycling_request and upcycling_request.user_id != user.pk:
        raise ValueError("The upcycling request belongs to another user.")
    if donation and donation.user_id != user.pk:
        raise ValueError("The donation belongs to another user.")
    if reward_redemption and reward_redemption.user_id != user.pk:
        raise ValueError("The redemption belongs to another user.")
    if upcycling_request and kind != PointTransaction.Kind.UPCYCLING_COMPLETED:
        raise ValueError("Transaction type does not match its upcycling source.")
    if donation and kind not in {
        PointTransaction.Kind.DONATION,
        PointTransaction.Kind.MONTHLY_DONATION_BONUS,
    }:
        raise ValueError("Transaction type does not match its donation source.")
    if reward_redemption and kind not in {
        PointTransaction.Kind.REDEMPTION,
        PointTransaction.Kind.REWARD_REFUNDED,
    }:
        raise ValueError("Transaction type does not match its reward redemption source.")
    defaults = {
        "points": points,
        "description": description,
        "weight_kg": weight_kg,
        "upcycling_request": upcycling_request,
        "donation": donation,
        "reward_redemption": reward_redemption,
    }
    record, created = PointTransaction.objects.get_or_create(
        user=user,
        kind=kind,
        source_reference=str(reference),
        defaults=defaults,
    )
    if not created and (
        record.points != points
        or record.description != description
        or (upcycling_request and record.upcycling_request_id != upcycling_request.pk)
        or (
            donation
            and kind != PointTransaction.Kind.MONTHLY_DONATION_BONUS
            and record.donation_id != donation.pk
        )
        or (reward_redemption and record.reward_redemption_id != reward_redemption.pk)
    ):
        raise ValueError("This source reference was already used for different data.")
    if weight_kg is not None and record.weight_kg != weight_kg:
        if record.weight_kg is None:
            record.weight_kg = weight_kg
            record.save(update_fields=("weight_kg",))
        else:
            raise ValueError("This source reference was already used for different data.")
    return record, created


@transaction.atomic
def award_verified_donation(user, *, donation_reference, weight_kg, verified_at=None, donation=None):
    if not donation_reference:
        raise ValueError("A donation reference is required.")
    points = calculate_donation_points(weight_kg)
    weight = Decimal(str(weight_kg)).quantize(Decimal("0.000001"))
    if weight <= 0:
        raise ValueError("Donation weight must be at least 0.000001 kg.")
    verified_at = verified_at or timezone.now()
    local_month = timezone.localtime(verified_at).strftime("%Y-%m")
    donation_transaction, created = _existing_or_create(
        user,
        kind=PointTransaction.Kind.DONATION,
        reference=donation_reference,
        points=points,
        description=f"Donasi terverifikasi ({Decimal(str(weight_kg)):g} kg)",
        weight_kg=weight,
        donation=donation,
    )
    if not created:
        return donation_transaction, None
    bonus, bonus_created = _existing_or_create(
        user,
        kind=PointTransaction.Kind.MONTHLY_DONATION_BONUS,
        reference=local_month,
        points=25,
        description=f"Bonus donasi pertama bulan {local_month}",
        donation=donation,
    )
    return donation_transaction, bonus if bonus_created else None


@transaction.atomic
def award_upcycling_completion(user, *, request_reference, upcycling_request=None):
    if not request_reference:
        raise ValueError("A request reference is required.")
    record, _ = _existing_or_create(
        user,
        kind=PointTransaction.Kind.UPCYCLING_COMPLETED,
        reference=request_reference,
        points=150,
        description="Upcycling selesai",
        upcycling_request=upcycling_request,
    )
    return record


def get_available_points(user):
    return PointTransaction.objects.filter(user=user).aggregate(total=Sum("points"))["total"] or 0


def get_lifetime_points(user):
    return (
        PointTransaction.objects.filter(user=user, points__gt=0)
        .exclude(kind=PointTransaction.Kind.REWARD_REFUNDED)
        .aggregate(total=Sum("points"))["total"]
        or 0
    )


@transaction.atomic
def redeem_reward(user, reward_id, *, shipping_address=""):
    get_user_model().objects.select_for_update().get(pk=user.pk)
    reward = Reward.objects.select_for_update().get(pk=reward_id, is_active=True)
    if reward.stock < 1:
        raise RewardUnavailable("Reward sedang habis.")
    if get_available_points(user) < reward.points_required:
        raise InsufficientPoints("Poin Anda belum mencukupi.")
    if reward.reward_type == Reward.Type.PHYSICAL and not shipping_address.strip():
        raise ValueError("Alamat pengiriman wajib diisi untuk barang fisik.")

    redemption = RewardRedemption.objects.create(
        user=user,
        reward=reward,
        points_spent=reward.points_required,
        status=(
            RewardRedemption.Status.FULFILLED
            if reward.reward_type == Reward.Type.VOUCHER
            else RewardRedemption.Status.PENDING
        ),
        voucher_code=uuid.uuid4().hex[:16].upper() if reward.reward_type == Reward.Type.VOUCHER else None,
        voucher_status=(
            RewardRedemption.VoucherStatus.AVAILABLE
            if reward.reward_type == Reward.Type.VOUCHER
            else None
        ),
        shipping_address=shipping_address.strip(),
        fulfilled_at=timezone.now() if reward.reward_type == Reward.Type.VOUCHER else None,
    )
    reward.stock -= 1
    reward.save(update_fields=("stock",))
    _existing_or_create(
        user,
        kind=PointTransaction.Kind.REDEMPTION,
        reference=f"redemption:{redemption.pk}:spend",
        points=-redemption.points_spent,
        description=f"Penukaran reward: {reward.name}",
        reward_redemption=redemption,
    )
    return redemption


@transaction.atomic
def redeem_points(user, *, redemption_reference, reward_name, points_cost):
    """Keep the earlier ledger-only API available for existing integrations."""
    if not redemption_reference or not reward_name:
        raise ValueError("A redemption reference and reward name are required.")
    try:
        cost = int(points_cost)
    except (TypeError, ValueError):
        raise ValueError("Point cost must be a positive integer.") from None
    if cost <= 0 or str(points_cost).strip() not in (str(cost), f"+{cost}"):
        raise ValueError("Point cost must be a positive integer.")
    get_user_model().objects.select_for_update().get(pk=user.pk)
    reference = str(redemption_reference)
    existing = PointTransaction.objects.filter(
        user=user,
        kind=PointTransaction.Kind.REDEMPTION,
        source_reference=reference,
    ).first()
    if existing:
        if existing.points != -cost or existing.description != reward_name:
            raise ValueError("This redemption reference was already used for different data.")
        return existing
    if get_available_points(user) < cost:
        raise InsufficientPoints("Not enough points for this redemption.")
    record, _ = _existing_or_create(
        user,
        kind=PointTransaction.Kind.REDEMPTION,
        reference=reference,
        points=-cost,
        description=reward_name,
    )
    return record


@transaction.atomic
def cancel_physical_redemption(redemption, *, admin_user, reason):
    redemption = RewardRedemption.objects.select_for_update().select_related("reward", "user").get(pk=redemption.pk)
    if redemption.status != RewardRedemption.Status.PENDING:
        raise ValueError("Hanya penukaran barang fisik yang masih menunggu dapat dibatalkan.")
    if redemption.reward.reward_type != Reward.Type.PHYSICAL:
        raise ValueError("Voucher yang sudah diterbitkan tidak dapat dibatalkan.")
    if not reason.strip():
        raise ValueError("Alasan pembatalan wajib diisi.")
    redemption.status = RewardRedemption.Status.CANCELLED
    redemption.cancelled_at = timezone.now()
    redemption.cancelled_by = admin_user
    redemption.cancellation_reason = reason.strip()
    redemption.save(update_fields=("status", "cancelled_at", "cancelled_by", "cancellation_reason"))
    reward = Reward.objects.select_for_update().get(pk=redemption.reward_id)
    reward.stock += 1
    reward.save(update_fields=("stock",))
    _existing_or_create(
        redemption.user,
        kind=PointTransaction.Kind.REWARD_REFUNDED,
        reference=f"redemption:{redemption.pk}:refund",
        points=redemption.points_spent,
        description=f"Pengembalian poin: {reward.name}",
        reward_redemption=redemption,
    )
    return redemption
