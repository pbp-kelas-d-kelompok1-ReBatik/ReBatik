from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .utils import get_user_role
from donasi.models import DonasiKain
from rewards.models import PointTransaction
from rewards.services import (get_available_points, get_lifetime_points,)
from upcycling.models import UpcyclingRequest

from .forms import UserProfileForm
from .models import UserProfile


def is_htmx_request(request):
    return request.headers.get("HX-Request") == "true"


@login_required
@login_required
def overview(request):
    role = get_user_role(request.user)
    profile = UserProfile.objects.filter(user=request.user).first()

    common_context = {
        "role": role,
        "profile": profile,
    }

    # ADMIN
    if role == "admin":
        return render(request, "profiles/roles/admin_overview.html", common_context,)

    # ARTISAN
    if role == "artisan":
        return render(request,"profiles/roles/artisan_overview.html", common_context,)

    # ECO-MEMBER
    donations = DonasiKain.objects.filter(user=request.user)

    upcycling_requests = UpcyclingRequest.objects.filter(user=request.user)

    transactions = PointTransaction.objects.filter(user=request.user)

    donation_transactions = transactions.filter(kind=PointTransaction.Kind.DONATION)

    saved_weight_kg = donation_transactions.aggregate(total=Sum("weight_kg"))["total"] or Decimal("0")

    # orders = (
    #     BatikOrder.objects
    #     .filter(user=request.user)
    #     .select_related(
    #         "motif",
    #         "palette",
    #         "design_option",
    #     )
    # )

    context = {
        **common_context,
        "donation_count": donations.count(),
        "recent_donations": donations.order_by("-created_at")[:3],
        "upcycling_count": upcycling_requests.count(),
        "completed_upcycling_count": (upcycling_requests.filter(status=UpcyclingRequest.Status.COMPLETED).count()),
        "available_points": get_available_points(request.user),
        "lifetime_points": get_lifetime_points(request.user),
        "saved_weight_kg": saved_weight_kg,
        "recent_upcycling": upcycling_requests[:3],
        "recent_transactions": transactions[:5],
        # "order_count": orders.count(),
        # "recent_orders": orders[:3],
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