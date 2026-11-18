from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    parser_classes,
    permission_classes,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    UpcyclingRateLimitBucket,
    UpcyclingRequest,
)
from .security import consume_upcycling_rate_limit
from .serializers import (
    UpcyclingRequestCreateSerializer,
    UpcyclingRequestDetailSerializer,
    UpcyclingRequestListSerializer,
)
from .views import (
    ACTION_RATE_LIMITS,
    PENDING_LIMIT_MESSAGE,
    PENDING_REQUEST_LIMIT,
)

@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def my_request_list(request):
    if request.method == "GET":
        upcycling_requests = UpcyclingRequest.objects.filter(
            user=request.user
        ).order_by("-created_at")

        serializer = UpcyclingRequestListSerializer(
            upcycling_requests,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)

    return _create_upcycling_request(request)


def _create_upcycling_request(request):
    action = UpcyclingRateLimitBucket.Action.CREATE
    limit, window_seconds = ACTION_RATE_LIMITS[action]

    allowed, retry_after = consume_upcycling_rate_limit(
        request.user,
        action,
        limit=limit,
        window_seconds=window_seconds,
    )

    if not allowed:
        response = Response(
            {"detail": "Terlalu banyak pengajuan. Coba lagi nanti."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
        response["Retry-After"] = str(retry_after)
        return response

    create_serializer = UpcyclingRequestCreateSerializer(
        data=request.data,
        context={"request": request},
    )

    if not create_serializer.is_valid():
        return Response(
            create_serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        user = get_user_model().objects.select_for_update().get(
            pk=request.user.pk
        )

        pending_count = UpcyclingRequest.objects.filter(
            user=user
        ).exclude(
            status__in=UpcyclingRequest.TERMINAL_STATUSES
        ).count()

        if pending_count >= PENDING_REQUEST_LIMIT:
            message = PENDING_LIMIT_MESSAGE.format(
                limit=PENDING_REQUEST_LIMIT
            )
            return Response(
                {"detail": message},
                status=status.HTTP_409_CONFLICT,
            )

        upcycling_request = create_serializer.save(user=user)

    serializer = UpcyclingRequestDetailSerializer(
        upcycling_request,
        context={"request": request},
    )
    return Response(
        serializer.data,
        status=status.HTTP_201_CREATED,
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_request_detail(request, pk):
    upcycling_request = get_object_or_404(
        UpcyclingRequest.objects.filter(user=request.user).prefetch_related(
            "additional_fabric_photos",
            "reference_photos",
            "status_history",
        ),
        pk=pk,
    )

    serializer = UpcyclingRequestDetailSerializer(
        upcycling_request,
        context={"request": request},
    )
    return Response(serializer.data)
