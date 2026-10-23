from django.shortcuts import render,redirect,get_list_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from .forms import LoginForm, SignUpForm
# Create your views here.

def show_home(request):
    return render(request, "home.html")

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


def login_user(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("main:show_home")
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})


def register(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("main:show_home")
    else:
        form = SignUpForm()

    return render(request, "signup.html", {"form": form})


@require_POST
def logout_user(request):
    logout(request)
    return redirect("main:show_home")
