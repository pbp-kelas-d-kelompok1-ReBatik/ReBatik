from django.shortcuts import render

# Create your views here.

from django.shortcuts import render


def donasi_landing(request):
    return render(request, "donasi/donasi_landing.html")


def donasi_create(request):
    return render(request, "donasi/donasi_form.html")


def donasi_history(request):
    return render(request, "donasi/riwayat_donasi.html")
