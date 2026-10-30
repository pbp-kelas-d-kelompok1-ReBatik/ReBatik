"""Authenticated views for the user's points overview and activity history."""

from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Sum
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import PointTransaction, Reward, RewardRedemption
from .forms import RewardAdminForm
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
    featured_vouchers = Reward.objects.filter(
        reward_type=Reward.Type.VOUCHER,
        is_active=True,
        stock__gt=0,
    )[:5]
    context = {
        "available_points": get_available_points(request.user),
        "lifetime_points": lifetime_points,
        "upcycling_count": upcycling_count,
        "donated_count": donated_count,
        "saved_weight_kg": saved_weight_kg,
        "saved_weight_unknown_count": donations.filter(weight_kg__isnull=True).count(),
        "recent_transactions": recent_transactions,
        "featured_vouchers": featured_vouchers,
        "voucher_success_message": request.session.pop("voucher_success_message", ""),
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
    """Show active vouchers and a short preview of the user's recent redemptions."""
    context = _voucher_catalog_context(request.user)
    context["voucher_success_message"] = request.session.pop("voucher_success_message", "")
    return render(request, "rewards/catalog.html", context)


def _voucher_catalog_context(user):
    voucher_redemptions = RewardRedemption.objects.filter(
        user=user,
        reward__reward_type=Reward.Type.VOUCHER,
        voucher_code__isnull=False,
    ).select_related("reward")[:5]
    return {
        "rewards": Reward.objects.filter(
            reward_type=Reward.Type.VOUCHER,
            is_active=True,
            stock__gt=0,
        ),
        "available_points": get_available_points(user),
        "recent_redemptions": voucher_redemptions,
    }


@login_required
def my_vouchers(request):
    """Show every voucher redemption belonging to the authenticated user."""
    vouchers = (
        RewardRedemption.objects.filter(
            user=request.user,
            reward__reward_type=Reward.Type.VOUCHER,
            voucher_code__isnull=False,
        )
        .select_related("reward")
        .order_by("-redeemed_at", "-pk")
    )
    return render(request, "rewards/vouchers.html", {"vouchers": vouchers})


def _redemption_return_page(request):
    return "rewards:overview" if request.POST.get("return_to") == "overview" else "rewards:catalog"


@login_required
def redeem_reward_view(request, reward_id):
    """Confirm a voucher redemption, then atomically debit points and quota."""
    if request.method != "POST":
        return redirect("rewards:catalog")

    if request.POST.get("confirm") != "yes":
        try:
            reward = Reward.objects.get(
                pk=reward_id,
                reward_type=Reward.Type.VOUCHER,
                is_active=True,
            )
        except Reward.DoesNotExist:
            messages.error(request, "Voucher tidak tersedia.")
            return redirect(_redemption_return_page(request))

        available_points = get_available_points(request.user)
        if reward.stock < 1:
            messages.error(request, "Voucher sedang habis.")
            return redirect(_redemption_return_page(request))
        if reward.discount_value is None or reward.discount_value <= 0:
            messages.error(request, "Voucher belum dikonfigurasi dengan benar.")
            return redirect(_redemption_return_page(request))
        if available_points < reward.points_required:
            messages.error(request, "Poin Anda belum mencukupi.")
            return redirect(_redemption_return_page(request))

        context = _voucher_catalog_context(request.user)
        context.update(
            {
                "confirm_reward": reward,
                "remaining_points": available_points - reward.points_required,
                "return_to": "overview" if request.POST.get("return_to") == "overview" else "catalog",
            }
        )
        return render(request, "rewards/catalog.html", context)

    try:
        redemption = redeem_reward(request.user, reward_id)
    except Reward.DoesNotExist:
        messages.error(request, "Voucher tidak tersedia.")
    except (InsufficientPoints, RewardUnavailable, ValueError) as exc:
        messages.error(request, str(exc))
    else:
        request.session["voucher_success_message"] = (
            f"Voucher berhasil ditukar. Kode: {redemption.voucher_code}"
        )
        return redirect(_redemption_return_page(request))
    return redirect(_redemption_return_page(request))


@staff_member_required
def admin_vouchers(request):
    """Manage voucher catalog items from ReBatik's regular dashboard UI."""
    can_view = request.user.has_perm("rewards.view_reward")
    can_add = request.user.has_perm("rewards.add_reward")
    can_change = request.user.has_perm("rewards.change_reward")
    if not can_view and not can_add:
        return HttpResponseForbidden("Anda tidak memiliki izin untuk mengelola katalog voucher.")

    if request.method == "POST":
        if not can_add:
            return HttpResponseForbidden("Anda tidak memiliki izin untuk menambah voucher.")
        form = RewardAdminForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Voucher berhasil ditambahkan ke katalog.")
            return redirect("rewards:admin_vouchers")
    else:
        form = RewardAdminForm() if can_add else None

    if form:
        for field in form.fields.values():
            field.widget.attrs["class"] = "voucher-admin-input"

    vouchers = Reward.objects.filter(reward_type=Reward.Type.VOUCHER).order_by("-pk")
    return render(
        request,
        "rewards/admin_vouchers.html",
        {
            "form": form,
            "vouchers": vouchers,
            "can_add": can_add,
            "can_change": can_change,
        },
    )


@staff_member_required
def admin_voucher_edit(request, voucher_id):
    if not request.user.has_perm("rewards.change_reward"):
        return HttpResponseForbidden("Anda tidak memiliki izin untuk mengubah voucher.")

    voucher = get_object_or_404(
        Reward,
        pk=voucher_id,
        reward_type=Reward.Type.VOUCHER,
    )
    if request.method == "POST":
        form = RewardAdminForm(request.POST, request.FILES, instance=voucher)
        if form.is_valid():
            form.save()
            messages.success(request, "Perubahan voucher berhasil disimpan.")
            return redirect("rewards:admin_vouchers")
    else:
        form = RewardAdminForm(instance=voucher)

    for field in form.fields.values():
        field.widget.attrs["class"] = "voucher-admin-input"

    return render(
        request,
        "rewards/admin_vouchers.html",
        {
            "form": form,
            "vouchers": Reward.objects.filter(
                reward_type=Reward.Type.VOUCHER
            ).order_by("-pk"),
            "can_add": request.user.has_perm("rewards.add_reward"),
            "can_change": True,
            "editing_voucher": voucher,
        },
    )


@staff_member_required
@require_POST
def admin_voucher_deactivate(request, voucher_id):
    if not request.user.has_perm("rewards.change_reward"):
        return HttpResponseForbidden("Anda tidak memiliki izin untuk menonaktifkan voucher.")

    voucher = get_object_or_404(
        Reward,
        pk=voucher_id,
        reward_type=Reward.Type.VOUCHER,
    )
    if voucher.is_active:
        voucher.is_active = False
        voucher.save(update_fields=["is_active"])
        messages.success(request, "Voucher berhasil dinonaktifkan.")
    return redirect("rewards:admin_vouchers")
