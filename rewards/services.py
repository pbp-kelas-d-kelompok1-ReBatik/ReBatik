"""Business rules for points, reward redemption, and balances."""

import secrets
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
    """Return points for a positive, finite donation weight in kilograms.

    Weights below 0.5 kg earn 50 points; 0.5 through 2 earn 100,
    over 2 through 5 earn 200, and over 5 earn 300. Raise ValueError
    for a nonnumeric, non-finite, or nonpositive weight.
    """
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
    """Return the ledger entry and whether it was created for this source.

    A reference is scoped to the user and kind. At most one source may be
    supplied, and it must belong to the user and match the transaction kind.
    Raise ValueError for an invalid source or conflicting existing data.
    An existing entry with no weight is updated when a weight is supplied.
    """
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
    """Award donation points and, once per local month, a 25-point bonus.

    Weight is in kilograms and is stored to six decimal places. The month
    comes from verified_at in the current time zone, or from the current time
    when omitted. Return (donation transaction, new bonus or None); a retry
    returns the existing donation transaction and no bonus. Raise ValueError
    for a missing reference, invalid weight, or conflicting source data.
    Decimal quantization errors and a naive verified_at can also propagate.
    """
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
    """Award 150 points once per user and request reference.

    Return the existing or newly created transaction. Raise ValueError if the
    reference is missing or the supplied source conflicts with ledger data.
    """
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
    """Return the sum of the user's ledger entries, or zero if there are none."""
    return PointTransaction.objects.filter(user=user).aggregate(total=Sum("points"))["total"] or 0


def get_lifetime_points(user):
    """Return positive points earned, excluding reward refunds."""
    return (
        PointTransaction.objects.filter(user=user, points__gt=0)
        .exclude(kind=PointTransaction.Kind.REWARD_REFUNDED)
        .aggregate(total=Sum("points"))["total"]
        or 0
    )


@transaction.atomic
def redeem_reward(user, reward_id):
    """Redeem an active, configured voucher and record its value at issuance."""
    get_user_model().objects.select_for_update().get(pk=user.pk)
    reward = Reward.objects.select_for_update().get(pk=reward_id, is_active=True)
    if reward.reward_type != Reward.Type.VOUCHER:
        raise RewardUnavailable("Reward tidak tersedia.")
    if reward.stock < 1:
        raise RewardUnavailable("Reward sedang habis.")
    if reward.discount_value is None or reward.discount_value <= 0:
        raise RewardUnavailable("Voucher belum dikonfigurasi dengan benar.")
    if get_available_points(user) < reward.points_required:
        raise InsufficientPoints("Poin Anda belum mencukupi.")

    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    prefix = reward.code_prefix.strip().upper() or "RB"
    while True:
        suffix = "".join(secrets.choice(alphabet) for _ in range(6))
        voucher_code = f"{prefix}-{suffix}"
        if not RewardRedemption.objects.filter(voucher_code=voucher_code).exists():
            break

    redemption = RewardRedemption.objects.create(
        user=user,
        reward=reward,
        points_spent=reward.points_required,
        discount_value_snapshot=reward.discount_value,
        status=RewardRedemption.Status.FULFILLED,
        voucher_code=voucher_code,
        voucher_status=RewardRedemption.VoucherStatus.AVAILABLE,
        fulfilled_at=timezone.now(),
    )
    reward.stock -= 1
    reward.save(update_fields=("stock",))
    _existing_or_create(
        user,
        kind=PointTransaction.Kind.REDEMPTION,
        reference=f"redemption:{redemption.pk}:spend",
        points=-redemption.points_spent,
        description=f"Tukar voucher: {reward.name}",
        reward_redemption=redemption,
    )
    return redemption


@transaction.atomic
def redeem_points(user, *, redemption_reference, reward_name, points_cost):
    """Keep the earlier ledger-only API available for existing integrations.

    Return the existing or new debit for redemption_reference. A retry must
    use the same reward name and positive integer cost. Raise ValueError for
    invalid or conflicting inputs and InsufficientPoints for a new debit
    exceeding the balance. Database lookup errors for the user can propagate.
    """
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
