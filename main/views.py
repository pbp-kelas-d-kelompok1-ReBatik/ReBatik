from django.shortcuts import render,redirect,get_list_or_404
from main.models import BatikMotif
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
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

def login_user(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("main:show_home")
    else:
        form = AuthenticationForm()

    return render(request, "login.html", {
        "form": form
    })


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("main:show_home")
    else:
        form = UserCreationForm()

    return render(request, "signup.html", {
        "form": form
    })


def logout_user(request):
    logout(request)
    return redirect("main:show_home")
