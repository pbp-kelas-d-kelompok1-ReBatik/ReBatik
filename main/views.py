from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from .forms import LoginForm, SignUpForm
from .models import Notification
from django.utils import timezone


def show_home(request):
    return render(request, "home.html")


def login_user(request):
    next_url = request.POST.get("next") or request.GET.get("next", "")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            login(request, form.get_user())
            Notification.objects.create(
                user=form.get_user(),
                title="Login berhasil",
                message=f"Kamu berhasil login pada {timezone.localtime().strftime('%d %B %Y pukul %H:%M WIB')}.",
                notification_type="login",
            )
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


def navbar_search(request):
    """HTMX dropdown pencarian yang tampil langsung di bawah search navbar."""
    from django.db.models import Q
    from batik_story.models import BatikMotif
    from batik_custom.models import RecommendedMotif
    from marketplace.models import Product

    query = request.GET.get("q", "").strip()[:80]
    stories, customs, products, suggestions = [], [], [], []

    if query:
        stories = list(
            BatikMotif.objects.filter(
                Q(nama__icontains=query) | Q(asal__icontains=query)
            ).order_by("nama")[:8]
        )
        customs = list(
            RecommendedMotif.objects.filter(
                is_active=True, name__icontains=query
            ).order_by("name")[:8]
        )
        matching_products = Product.objects.filter(is_deleted=False).filter(
            Q(name__icontains=query)
            | Q(motif__icontains=query)
            | Q(category__icontains=query)
        ).order_by("-created_at")
        products = list(matching_products[:3])

        # Satukan saran dari Batik Story, Custom Batik, dan Marketplace.
        seen = set()
        for label, kind, url_name in (
            [(item.nama, "Motif Batik", "story") for item in stories]
            + [(item.name, "Motif Custom", "custom") for item in customs]
            + [(item.name, "Marketplace", "product") for item in products]
        ):
            key = label.casefold()
            if key not in seen:
                seen.add(key)
                suggestions.append({"label": label, "kind": kind, "source": url_name})
            if len(suggestions) >= 6:
                break

    recent_searches = request.session.get("reb_search_history", [])
    return render(request, "partials/navbar_search_results.html", {
        "query": query,
        "suggestions": suggestions,
        "products": products,
        "recent_searches": recent_searches,
    })


def save_search(request):
    from django.shortcuts import redirect
    query = request.GET.get("q", "").strip()[:80]
    if query:
        history = request.session.get("reb_search_history", [])
        history = [item for item in history if item.casefold() != query.casefold()]
        request.session["reb_search_history"] = [query] + history[:4]
    return redirect(request.GET.get("next") or "main:show_home")


@login_required
def notification_list(request):
    notifications = request.user.notifications.all()[:30]
    return render(request, "partials/notification_panel.html", {
        "notifications": notifications,
        "unread_count": request.user.notifications.filter(is_read=False).count(),
    })


@login_required
@require_POST
def notification_mark_read(request, pk):
    from django.shortcuts import get_object_or_404
    notification = get_object_or_404(request.user.notifications, pk=pk)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return redirect(notification.target_url or "main:notifications")


def clear_search_history(request):
    request.session["reb_search_history"] = []
    return render(request, "partials/navbar_search_results.html", {
        "query": "", "stories": [], "customs": [], "products": [], "recent_searches": [],
    })
