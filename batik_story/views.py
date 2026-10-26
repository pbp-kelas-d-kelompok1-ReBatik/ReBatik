from django.shortcuts import render,redirect,get_list_or_404
from .models import BatikMotif
from django.shortcuts import render, redirect
# Create your views here.

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
