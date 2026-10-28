from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from donasi.models import DonasiKain
from rewards.models import PointTransaction
from rewards.services import (
    get_available_points,
    get_lifetime_points,
)
from upcycling.models import UpcyclingRequest

from .forms import UserProfileForm
from .models import UserProfile


def is_htmx_request(request):
    return request.headers.get("HX-Request") == "true"


@login_required
def overview(request):
    profile = UserProfile.objects.filter(
        user=request.user
    ).first()

    # Semua data aktivitas dibatasi pada akun yang sedang login.
    donations = DonasiKain.objects.filter(
        user=request.user
    )

    upcycling_requests = UpcyclingRequest.objects.filter(
        user=request.user
    )

    transactions = PointTransaction.objects.filter(
        user=request.user
    )

    donation_transactions = transactions.filter(
        kind=PointTransaction.Kind.DONATION
    )

    saved_weight_kg = donation_transactions.aggregate(
        total=Sum("weight_kg")
    )["total"]

    if saved_weight_kg is None:
        saved_weight_kg = Decimal("0")

    context = {
        "profile": profile,
        "donation_count": donations.count(),
        "upcycling_count": upcycling_requests.count(),
        "completed_upcycling_count": upcycling_requests.filter(
            status=UpcyclingRequest.Status.COMPLETED
        ).count(),
        "available_points": get_available_points(request.user),
        "lifetime_points": get_lifetime_points(request.user),
        "saved_weight_kg": saved_weight_kg,
        "recent_donations": donations[:3],
        "recent_upcycling": upcycling_requests[:3],
        "recent_transactions": transactions[:5],
    }

    return render(
        request,
        "profiles/overview.html",
        context,
    )


@login_required
def create_profile(request):
    # Satu akun hanya boleh memiliki satu profil.
    if UserProfile.objects.filter(user=request.user).exists():
        return redirect("profiles:overview")

    if request.method == "POST":
        form = UserProfileForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            profile = form.save(commit=False)

            # Pemilik ditentukan dari session login,
            # bukan dari input pengguna.
            profile.user = request.user
            profile.save()

            messages.success(
                request,
                "Profil berhasil dibuat.",
            )

            return redirect("profiles:overview")

    else:
        form = UserProfileForm(
            initial={
                "display_name": request.user.username,
            }
        )

    return render(
        request,
        "profiles/create.html",
        {"form": form},
    )


@login_required
def edit_profile(request):
    profile = UserProfile.objects.filter(
        user=request.user
    ).first()

    if profile is None:
        return redirect("profiles:create")

    if request.method == "POST":
        form = UserProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Profil berhasil diperbarui.",
            )

            if is_htmx_request(request):
                return render(
                    request,
                    "profiles/partials/profile_card.html",
                    {"profile": profile},
                )

            return redirect("profiles:overview")

    else:
        form = UserProfileForm(instance=profile)

    if is_htmx_request(request):
        template_name = (
            "profiles/partials/profile_edit_form.html"
        )
    else:
        template_name = "profiles/edit.html"

    return render(
        request,
        template_name,
        {
            "form": form,
            "profile": profile,
        },
    )


@login_required
@require_POST
def delete_profile(request):
    profile = UserProfile.objects.filter(
        user=request.user
    ).first()

    if profile is not None:
        profile.delete()

        messages.success(
            request,
            "Data profil berhasil dihapus.",
        )

    return redirect("profiles:overview")


@login_required
def order_history(request):
    # Marketplace belum mempunyai model pesanan.
    # Jangan membuat data pesanan palsu.
    return render(
        request,
        "profiles/orders.html",
    )