"""Endpoint autentikasi untuk aplikasi mobile (Flutter).

Aplikasi mobile memakai session Django yang sama dengan website, jadi seluruh
endpoint tulis tetap dilindungi CSRF (SessionAuthentication). Alurnya:
GET csrf/ -> POST login/ -> kirim cookie sessionid + header X-CSRFToken.
"""
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from main.forms import SignUpForm
from main.views import create_notification
from profiles.utils import get_user_role


def _user_payload(user):
    return {
        "id": user.pk,
        "username": user.username,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "role": get_user_role(user),
    }


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def csrf(request):
    """Membuat cookie csrftoken dan mengembalikan nilainya."""
    return Response({"csrfToken": get_token(request._request)})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login_api(request):
    username = str(request.data.get("username", "")).strip()
    password = str(request.data.get("password", ""))
    if not username or not password:
        return Response(
            {"detail": "Username dan password wajib diisi."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user = authenticate(request._request, username=username, password=password)
    if user is None or not user.is_active:
        return Response(
            {"detail": "Username atau password salah."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    login(request._request, user)
    create_notification(
        user, "Login berhasil",
        f"Kamu berhasil login pada {timezone.localtime().strftime('%d %B %Y pukul %H:%M WIB')}.",
        "login",
    )
    # login() merotasi token CSRF; kirim yang baru ke klien.
    return Response({"user": _user_payload(user), "csrfToken": get_token(request._request)})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def register_api(request):
    form = SignUpForm({
        "username": request.data.get("username", ""),
        "password1": request.data.get("password1", ""),
        "password2": request.data.get("password2", ""),
    })
    if not form.is_valid():
        errors = {
            field: [item["message"] for item in items]
            for field, items in form.errors.get_json_data().items()
        }
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    user = form.save()
    login(request._request, user)
    create_notification(
        user, "Selamat datang di ReBatik!",
        "Akunmu berhasil dibuat. Selamat menjelajahi ReBatik.", "register",
    )
    return Response(
        {"user": _user_payload(user), "csrfToken": get_token(request._request)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def logout_api(request):
    logout(request._request)
    return Response({"csrfToken": get_token(request._request)})


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def me(request):
    if not request.user.is_authenticated:
        return Response({"is_authenticated": False, "user": None})
    return Response({"is_authenticated": True, "user": _user_payload(request.user)})
