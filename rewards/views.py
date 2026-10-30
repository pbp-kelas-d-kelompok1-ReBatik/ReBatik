"""Authenticated views for the user's points overview and activity history."""

from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Sum
from django.shortcuts import render

from .models import PointTransaction, Reward, RewardRedemption
from .services import (
    InsufficientPoints,
    RewardUnavailable,
    get_available_points,
    get_lifetime_points,
    redeem_reward,
)


def _level_progress(lifetime_points):
    """Return the current lifetime-points tier and progress toward the next."""
    if lifetime_points < 2000:
        current_level = "Penenun Pemula"
        next_level = "Penenun Mahir"
        lower_bound, upper_bound = 0, 2000
    elif lifetime_points < 5000:
        current_level = "Penenun Mahir"
        next_level = "Penenun Ahli"
        lower_bound, upper_bound = 2000, 5000
    else:
        current_level = "Penenun Ahli"
        next_level = None
        lower_bound = upper_bound = 5000

    earned_in_level = max(0, lifetime_points - lower_bound)
    required_in_level = upper_bound - lower_bound
    progress_percent = (
        min(100, round(earned_in_level * 100 / required_in_level))
        if required_in_level
        else 100
    )
    return {
        "current_level": current_level,
        "next_level": next_level,
        "level_progress": earned_in_level,
        "level_target": required_in_level,
        "level_progress_percent": progress_percent,
    }


@login_required
def points_overview(request):
    """Render balance, lifetime progress, and the five newest transactions."""
    user_transactions = PointTransaction.objects.filter(user=request.user)
    lifetime_points = get_lifetime_points(request.user)
    upcycling_count = user_transactions.filter(
        kind=PointTransaction.Kind.UPCYCLING_COMPLETED
    ).count()
    donations = user_transactions.filter(kind=PointTransaction.Kind.DONATION)
    donated_count = donations.count()
    saved_weight_kg = donations.aggregate(total=Sum("weight_kg"))["total"]
    if saved_weight_kg is None:
        saved_weight_kg = Decimal("0")
    recent_transactions = user_transactions[:5]
    context = {
        "available_points": get_available_points(request.user),
        "lifetime_points": lifetime_points,
        "upcycling_count": upcycling_count,
        "donated_count": donated_count,
        "saved_weight_kg": saved_weight_kg,
        "saved_weight_unknown_count": donations.filter(weight_kg__isnull=True).count(),
        "recent_transactions": recent_transactions,
        **_level_progress(lifetime_points),
    }
    return render(request, "rewards/overview.html", context)


@login_required
def transaction_history(request):
    """Render a paginated, owner-scoped history with income/expense filters."""
    active_filter = request.GET.get("type", "all")
    if active_filter not in {"all", "in", "out"}:
        active_filter = "all"

    transactions = PointTransaction.objects.filter(user=request.user)
    if active_filter == "in":
        transactions = transactions.filter(points__gt=0)
    elif active_filter == "out":
        transactions = transactions.filter(points__lt=0)

    transaction_page = Paginator(transactions, 6).get_page(request.GET.get("page"))
    context = {
        "transaction_page": transaction_page,
        "active_filter": active_filter,
    }
    template_name = (
        "rewards/_history_content.html"
        if request.headers.get("HX-Request") == "true"
        else "rewards/history.html"
    )
    return render(request, template_name, context)


@login_required
def reward_catalog(request):
    """Show active, in-stock rewards, the user's balance, and five recent redemptions."""
    redemptions = RewardRedemption.objects.filter(user=request.user).select_related("reward")[:5]
    return render(
        request,
        "rewards/catalog.html",
        {
            "rewards": Reward.objects.filter(is_active=True, stock__gt=0),
            "available_points": get_available_points(request.user),
            "recent_redemptions": redemptions,
        },
    )


@login_required
def redeem_reward_view(request, reward_id):
    """Redeem a reward on POST and redirect to the catalog with a result message.

    Missing rewards and redemption ValueErrors are presented as error messages.
    """
    if request.method != "POST":
        return redirect("rewards:catalog")
    shipping_address = request.POST.get("shipping_address", "")
    try:
        redemption = redeem_reward(
            request.user,
            reward_id,
            shipping_address=shipping_address,
        )
    except Reward.DoesNotExist:
        messages.error(request, "Reward tidak tersedia.")
    except (InsufficientPoints, RewardUnavailable, ValueError) as exc:
        messages.error(request, str(exc))
    else:
        if redemption.voucher_code:
            messages.success(request, f"Penukaran berhasil. Kode voucher Anda: {redemption.voucher_code}")
        else:
            messages.success(request, "Penukaran berhasil. Reward fisik menunggu diproses admin.")
    return redirect("rewards:catalog")
