"""Business rules for awarding, redeeming, and summarizing reward points."""

from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import PointTransaction


class InsufficientPoints(ValueError):
    """Raised when a user tries to redeem more points than they have."""


def calculate_donation_points(weight_kg):
    """Return the Figma donation tier for a strictly positive kilogram weight."""
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


def _existing_or_create(user, *, kind, reference, points, description):
    """Create one transaction per source event and reject conflicting retries."""
    transaction_record, created = PointTransaction.objects.get_or_create(
        user=user,
        kind=kind,
        source_reference=reference,
        defaults={"points": points, "description": description},
    )
    if not created and (
        transaction_record.points != points
        or transaction_record.description != description
    ):
        raise ValueError("This source reference was already used for different data.")
    return transaction_record, created


@transaction.atomic
def award_verified_donation(user, *, donation_reference, weight_kg, verified_at=None):
    """Credit verified donation points and at most one monthly bonus per user."""
    if not donation_reference:
        raise ValueError("A donation reference is required.")
    points = calculate_donation_points(weight_kg)
    verified_at = verified_at or timezone.now()
    local_month = timezone.localtime(verified_at).strftime("%Y-%m")

    donation, created = _existing_or_create(
        user,
        kind=PointTransaction.Kind.DONATION,
        reference=str(donation_reference),
        points=points,
        description=f"Donasi terverifikasi ({Decimal(str(weight_kg)):g} kg)",
    )
    if not created:
        return donation, None

    bonus, bonus_created = _existing_or_create(
        user,
        kind=PointTransaction.Kind.MONTHLY_DONATION_BONUS,
        reference=local_month,
        points=25,
        description=f"Bonus donasi pertama bulan {local_month}",
    )
    return donation, bonus if bonus_created else None


@transaction.atomic
def award_upcycling_completion(user, *, request_reference):
    """Credit 150 points once when an upcycling request is completed."""
    if not request_reference:
        raise ValueError("A request reference is required.")
    record, _ = _existing_or_create(
        user,
        kind=PointTransaction.Kind.UPCYCLING_COMPLETED,
        reference=str(request_reference),
        points=150,
        description="Upcycling selesai",
    )
    return record


@transaction.atomic
def redeem_points(user, *, redemption_reference, reward_name, points_cost):
    """Debit points atomically while rejecting overdrafts and duplicate retries."""
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


def get_available_points(user):
    """Return the spendable balance, including all credits and debits."""
    return (
        PointTransaction.objects.filter(user=user).aggregate(total=Sum("points"))["total"]
        or 0
    )


def get_lifetime_points(user):
    """Return gross points earned; redemptions do not lower this total."""
    return (
        PointTransaction.objects.filter(user=user, points__gt=0).aggregate(
            total=Sum("points")
        )["total"]
        or 0
    )
