from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import LoginForm, SignUpForm


def show_home(request):
    return render(request, "home.html")


def login_user(request):
    next_url = request.POST.get("next") or request.GET.get("next", "")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            login(request, form.get_user())
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("main:show_home")
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form, "next": next_url})


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
