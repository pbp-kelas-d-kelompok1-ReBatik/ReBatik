"""Authenticated views for the user's points overview and activity history."""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import PointTransaction
from .services import get_available_points, get_lifetime_points


def _level_progress(lifetime_points):
    """Return the current lifetime-points tier and progress toward the next."""
    if lifetime_points < 2000:
        current_level = "Penenun Pemula"
        next_level = "Penenun Mahir"
        lower_bound, upper_bound = 0, 2000
    elif lifetime_points < 5000:
        current_level = "Penenun Mahir"
        next_level = "Pengrajin"
        lower_bound, upper_bound = 2000, 5000
    else:
        current_level = "Pengrajin"
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
    recent_transactions = user_transactions[:5]
    context = {
        "available_points": get_available_points(request.user),
        "lifetime_points": lifetime_points,
        "upcycling_count": upcycling_count,
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
    return render(request, "rewards/history.html", context)
