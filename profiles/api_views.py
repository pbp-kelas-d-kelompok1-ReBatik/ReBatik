from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from profiles.models import UserProfile, UserSettings
from profiles.serializers import (
    UserProfileSerializer,
    UserSettingsSerializer,
)


# ==========================================
# PROFILE API
# ==========================================

@api_view(["GET", "POST", "PATCH"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def profile(request):

    user_profile = UserProfile.objects.filter(
        user=request.user
    ).first()

    # GET: View profile
    if request.method == "GET":

        if user_profile is None:
            return Response(
                {"detail": "Profil belum dibuat."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UserProfileSerializer(
            user_profile,
            context={"request": request},
        )

        return Response(serializer.data)

    # POST: Create profile
    if request.method == "POST":

        if user_profile is not None:
            return Response(
                {"detail": "Profil sudah tersedia."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UserProfileSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    # PATCH: Edit profile
    if request.method == "PATCH":

        if user_profile is None:
            return Response(
                {"detail": "Profil belum dibuat."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UserProfileSerializer(
            user_profile,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


# ==========================================
# PROFILE SETTINGS API
# ==========================================

@api_view(["GET", "PATCH"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def profile_settings(request):

    preferences, _ = UserSettings.objects.get_or_create(
        user=request.user
    )

    # GET: View settings
    if request.method == "GET":

        serializer = UserSettingsSerializer(
            preferences
        )

        return Response(serializer.data)

    # PATCH: Edit settings
    if request.method == "PATCH":

        serializer = UserSettingsSerializer(
            preferences,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)