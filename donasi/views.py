
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render

from .forms import DonasiKainForm
from .models import DonasiKain


def landing(request):
    return render(
        request,
        "donasi/donasi_landing.html",
    )


def create(request):
    if request.method == "POST":
        form = DonasiKainForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            donation = form.save(commit=False)
            if request.user.is_authenticated:
                donation.user = request.user
            donation.save()

            messages.success(
                request,
                "Donasi berhasil diajukan. Terima kasih sudah berbagi!",
            )

            return redirect("donasi:history")

    else:
        form = DonasiKainForm()

    return render(
        request,
        "donasi/donasi_form.html",
        {"form": form},
    )


def history(request):
    query = request.GET.get("q", "").strip()[:100]

    donations = DonasiKain.objects.all()

    if query:
        donations = donations.filter(
            Q(item_name__icontains=query)
            | Q(description__icontains=query)
            | Q(donation_type__icontains=query)
            | Q(clothing_category__icontains=query)
            | Q(city__icontains=query)
        )

    return render(
        request,
        "donasi/riwayat_donasi.html",
        {
            "donations": donations,
            "query": query,
        },
    )
