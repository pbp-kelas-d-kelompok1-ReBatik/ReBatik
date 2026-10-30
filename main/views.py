from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import LoginForm, SignUpForm
from .models import Notification


def show_home(request):
    return render(request, "home.html")


def create_notification(user, title, message, notification_type="general", target_url=""):
    """Buat notifikasi selama preferensi pengguna mengizinkannya."""
    if not user or not user.is_authenticated:
        return None

    try:
        preferences = user.user_settings
    except Exception:
        preferences = None

    if preferences:
        if notification_type in {"order_created", "order_updated", "order_cancelled"} and not preferences.order_notifications:
            return None
        if notification_type in {"donation_updated", "upcycling_updated"} and not preferences.activity_notifications:
            return None
        if notification_type == "promo" and not preferences.promotional_notifications:
            return None

    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        target_url=target_url,
    )


def login_user(request):
    next_url = request.POST.get("next") or request.GET.get("next", "")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            create_notification(
                user,
                "Login berhasil",
                f"Kamu berhasil login pada {timezone.localtime().strftime('%d %B %Y pukul %H:%M WIB')}.",
                "login",
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
            create_notification(
                user,
                "Selamat datang di ReBatik!",
                "Akunmu berhasil dibuat. Selamat menjelajahi ReBatik.",
                "register",
            )
            return redirect("main:show_home")
    else:
        form = SignUpForm()

    return render(request, "signup.html", {"form": form})


@require_POST
def logout_user(request):
    user = request.user
    if user.is_authenticated:
        create_notification(
            user,
            "Logout berhasil",
            f"Kamu telah logout pada {timezone.localtime().strftime('%d %B %Y pukul %H:%M WIB')}.",
            "logout",
        )
    logout(request)
    return redirect("main:show_home")


def navbar_search(request):
    """HTMX live search: saran tampil saat pengguna mengetik."""
    from batik_story.models import BatikMotif
    from batik_custom.models import RecommendedMotif
    from marketplace.models import Product

    query = request.GET.get("q", "").strip()[:80]
    suggestions = []

    if query:
        story_items = BatikMotif.objects.filter(
            Q(nama__icontains=query) | Q(asal__icontains=query)
        ).order_by("nama")[:8]

        custom_items = RecommendedMotif.objects.filter(
            is_active=True, name__icontains=query
        ).order_by("name")[:8]

        product_items = Product.objects.filter(is_deleted=False).filter(
            Q(name__icontains=query)
            | Q(motif__icontains=query)
            | Q(category__icontains=query)
        ).order_by("-created_at")[:5]

        for item in story_items:
            suggestions.append({
                "label": item.nama,
                "kind": "Motif Batik",
                "url": f"/batik_story/?q={item.nama}",
            })
        for item in custom_items:
            suggestions.append({
                "label": item.name,
                "kind": "Custom Batik",
                "url": "/batik_custom/",
            })
        for item in product_items:
            suggestions.append({
                "label": item.name,
                "kind": "Marketplace",
                "url": f"/marketplace/?q={item.name}",
            })

        unique = {}
        for item in suggestions:
            unique.setdefault(item["label"].casefold(), item)
        suggestions = list(unique.values())[:7]

    recent_searches = request.session.get("reb_search_history", [])
    return render(request, "partials/navbar_search_results.html", {
        "query": query,
        "suggestions": suggestions,
        "recent_searches": recent_searches,
    })


def save_search(request):
    query = request.GET.get("q", "").strip()[:80]
    if query:
        history = request.session.get("reb_search_history", [])
        history = [item for item in history if item.casefold() != query.casefold()]
        request.session["reb_search_history"] = [query] + history[:4]
    return redirect(request.GET.get("next") or "main:show_home")


@login_required
def notification_list(request):
    notifications = request.user.notifications.all()[:30]
    unread_count = request.user.notifications.filter(is_read=False).count()
    context = {
        "notifications": notifications,
        "unread_count": unread_count,
    }
    if request.headers.get("HX-Request") == "true":
        return render(request, "partials/notification_panel.html", context)
    return render(request, "notifications.html", context)


@login_required
@require_POST
def notification_mark_read(request, pk):
    notification = get_object_or_404(request.user.notifications, pk=pk)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if request.headers.get("HX-Request") == "true":
        return notification_list(request)
    return redirect("main:show_home")


@login_required
@require_POST
def notification_mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    if request.headers.get("HX-Request") == "true":
        return notification_list(request)
    return redirect("main:show_home")


@require_POST
def clear_search_history(request):
    request.session["reb_search_history"] = []
    return render(request, "partials/navbar_search_results.html", {
        "query": "",
        "suggestions": [],
        "recent_searches": [],
    })
