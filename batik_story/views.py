from django.shortcuts import render,redirect,get_list_or_404
from .models import BatikMotif
from django.shortcuts import render, redirect
# Create your views here.

from django.contrib import messages
from django.db.models import Q

from .forms import DonasiKainForm
from .models import DonasiKain

def show_home(request):
    return render(request, "home.html")
def show_batik_story(request):
    context={
        "judul":"Batik Story",
        "ket1": "Jelajahi kisah di balik batik Indonesia. Kenali sejarah, filosofi, dan makna dari berbagai motif batik Nusantara. ",
        "batiks":BatikMotif.objects.all()
    }
    return render(request, "batik_story.html",context)

def show_batik_custom(request):
    return render(request, "batik_custom.html")


def donasi_landing(request):
    return render(request, "donasi_landing.html")


def donasi_create(request):
    if request.method == "POST":
        form = DonasiKainForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Donasi berhasil diajukan. Terima kasih sudah berbagi!"
            )
            return redirect("main:donasi_history")
    else:
        form = DonasiKainForm()

    return render(
        request,
        "donasi_form.html",
        {"form": form},
    )


def donasi_history(request):
    query = request.GET.get("q", "").strip()[:100]

    donations = DonasiKain.objects.all()

    if query:
        donations = donations.filter(
            Q(item_name__icontains=query)
            | Q(description__icontains=query)
            | Q(city__icontains=query)
        )

    return render(
        request,
        "riwayat_donasi.html",
        {
            "donations": donations,
            "query": query,
        },
    )

