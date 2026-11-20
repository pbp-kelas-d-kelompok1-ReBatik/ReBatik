from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    parser_classes,
    permission_classes,
)
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import (
    UpcyclingRateLimitBucket,
    UpcyclingRequest,
    UpcyclingStatusHistory,
    fabric_handoff_deadline,
)
from .security import consume_upcycling_rate_limit
from .serializers import (
    CancelUpcyclingRequestSerializer,
    AdminQueueRowSerializer,
    ArtisanAssignmentSerializer,
    ArtisanRequestActionSerializer,
    ArtisanUpcyclingRequestSerializer,
    FabricHandoffSerializer,
    ProductDeliverySerializer,
    UpcyclingRequestCreateSerializer,
    UpcyclingRequestDetailSerializer,
    UpcyclingRequestListSerializer,
    UpcyclingRequestUpdateSerializer,
)
from .views import (
    ACTION_RATE_LIMITS,
    PENDING_LIMIT_MESSAGE,
    PENDING_REQUEST_LIMIT,
    _get_artisan_profile,
)
from .services import assign_artisan_to_request

@api_view(["GET", "POST"])
@parser_classes([JSONParser, MultiPartParser, FormParser])
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

@api_view(["GET", "PATCH"])
@parser_classes([JSONParser, MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def my_request_detail(request, pk):
    if request.method == "PATCH":
        return _update_upcycling_request(request, pk)

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


def _update_upcycling_request(request, pk):
    upcycling_request = get_object_or_404(
        UpcyclingRequest.objects.filter(user=request.user),
        pk=pk,
    )
    if upcycling_request.status != UpcyclingRequest.Status.PENDING_ASSIGNMENT:
        return _status_conflict(
            "Permintaan hanya bisa diedit saat masih menunggu penugasan artisan."
        )

    action = UpcyclingRateLimitBucket.Action.UPDATE
    limit, window_seconds = ACTION_RATE_LIMITS[action]
    allowed, retry_after = consume_upcycling_rate_limit(
        request.user,
        action,
        limit=limit,
        window_seconds=window_seconds,
    )
    if not allowed:
        response = Response(
            {"detail": "Terlalu banyak perubahan. Coba lagi nanti."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
        response["Retry-After"] = str(retry_after)
        return response

    with transaction.atomic():
        upcycling_request = _owned_locked_request(request.user, pk)
        if upcycling_request.status != UpcyclingRequest.Status.PENDING_ASSIGNMENT:
            return _status_conflict(
                "Permintaan hanya bisa diedit saat masih menunggu penugasan artisan."
            )

        serializer = UpcyclingRequestUpdateSerializer(
            upcycling_request,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        upcycling_request = serializer.save()

    return _owned_request_detail_response(upcycling_request, request)


def _owned_request_detail_response(upcycling_request, request):
    serializer = UpcyclingRequestDetailSerializer(
        upcycling_request,
        context={"request": request},
    )
    return Response(serializer.data)


def _record_api_status_change(upcycling_request, user, old_status):
    UpcyclingStatusHistory.objects.create(
        request=upcycling_request,
        from_status=old_status,
        to_status=upcycling_request.status,
        changed_by=user,
    )


def _owned_locked_request(user, pk):
    return get_object_or_404(
        UpcyclingRequest.objects.select_for_update().filter(user=user),
        pk=pk,
    )


def _status_conflict(message):
    return Response({"detail": message}, status=status.HTTP_409_CONFLICT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_fabric_handoff_api(request, pk):
    with transaction.atomic():
        upcycling_request = _owned_locked_request(request.user, pk)
        if upcycling_request.status != UpcyclingRequest.Status.AWAITING_FABRIC:
            return _status_conflict(
                "Rencana penyerahan kain belum dapat diisi pada status ini."
            )
        if (
            upcycling_request.fabric_deadline
            and upcycling_request.fabric_deadline < timezone.now()
        ):
            return _status_conflict("Tenggat penyerahan kain sudah lewat.")

        serializer = FabricHandoffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(upcycling_request, field, value)
        upcycling_request.save(
            update_fields=(
                "fabric_delivery_method",
                "fabric_delivery_location",
                "updated_at",
            )
        )

    return _owned_request_detail_response(upcycling_request, request)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approve_quote_api(request, pk):
    with transaction.atomic():
        upcycling_request = _owned_locked_request(request.user, pk)
        if (
            upcycling_request.status != UpcyclingRequest.Status.AWAITING_APPROVAL
            or upcycling_request.quoted_price is None
        ):
            return _status_conflict("Penawaran belum tersedia untuk disetujui.")

        old_status = upcycling_request.status
        upcycling_request.approved_at = timezone.now()
        upcycling_request.status = UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS
        upcycling_request.save(
            update_fields=("approved_at", "status", "updated_at")
        )
        _record_api_status_change(upcycling_request, request.user, old_status)

    return _owned_request_detail_response(upcycling_request, request)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_product_delivery_api(request, pk):
    with transaction.atomic():
        upcycling_request = _owned_locked_request(request.user, pk)
        if (
            upcycling_request.status
            != UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS
        ):
            return _status_conflict(
                "Detail penerimaan produk belum dapat diisi pada status ini."
            )

        serializer = ProductDeliverySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_status = upcycling_request.status
        for field, value in serializer.validated_data.items():
            setattr(upcycling_request, field, value)
        upcycling_request.status = UpcyclingRequest.Status.IN_PROGRESS
        upcycling_request.save(
            update_fields=(
                "delivery_method",
                "address",
                "status",
                "updated_at",
            )
        )
        _record_api_status_change(upcycling_request, request.user, old_status)

    return _owned_request_detail_response(upcycling_request, request)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_completion_api(request, pk):
    with transaction.atomic():
        upcycling_request = _owned_locked_request(request.user, pk)
        if upcycling_request.status != UpcyclingRequest.Status.READY:
            return _status_conflict("Request belum siap dikonfirmasi selesai.")

        old_status = upcycling_request.status
        upcycling_request.status = UpcyclingRequest.Status.COMPLETED
        upcycling_request.completed_by = request.user
        upcycling_request.completed_at = timezone.now()
        upcycling_request.save(
            update_fields=(
                "status",
                "completed_by",
                "completed_at",
                "updated_at",
            )
        )
        _record_api_status_change(upcycling_request, request.user, old_status)

        from rewards.services import award_upcycling_completion

        award_upcycling_completion(
            request.user,
            request_reference=str(upcycling_request.pk),
            upcycling_request=upcycling_request,
        )

    return _owned_request_detail_response(upcycling_request, request)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_request_api(request, pk):
    with transaction.atomic():
        upcycling_request = _owned_locked_request(request.user, pk)
        serializer = CancelUpcyclingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reject_quote = serializer.validated_data["action"] == "reject_quote"

        cancellable_statuses = {
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
            UpcyclingRequest.Status.PENDING_REVIEW,
            UpcyclingRequest.Status.AWAITING_FABRIC,
            UpcyclingRequest.Status.INSPECTION,
        }
        can_reject_quote = (
            reject_quote
            and upcycling_request.status == UpcyclingRequest.Status.AWAITING_APPROVAL
        )
        if reject_quote and not can_reject_quote:
            return _status_conflict("Penawaran tidak dapat ditolak pada status ini.")
        if not reject_quote and upcycling_request.status not in cancellable_statuses:
            if upcycling_request.approved_at:
                return _status_conflict(
                    "Harga sudah disetujui. Permintaan tidak dapat dibatalkan mandiri."
                )
            return _status_conflict(
                "Request ini tidak dapat dibatalkan mandiri. Hubungi admin untuk bantuan."
            )

        old_status = upcycling_request.status
        upcycling_request.status = UpcyclingRequest.Status.CANCELLED
        upcycling_request.cancellation_reason = (
            "Penawaran harga ditolak oleh user."
            if can_reject_quote
            else "Dibatalkan oleh user."
        )
        update_fields = ["status", "cancellation_reason", "updated_at"]
        if upcycling_request.fabric_received_at:
            upcycling_request.return_status = (
                UpcyclingRequest.ReturnStatus.PENDING_RETURN
            )
            update_fields.append("return_status")
        upcycling_request.save(update_fields=update_fields)
        _record_api_status_change(upcycling_request, request.user, old_status)

    return _owned_request_detail_response(upcycling_request, request)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def artisan_request_list_api(request):
    try:
        artisan = _get_artisan_profile(request.user)
    except PermissionDenied as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

    requests = (
        UpcyclingRequest.objects.filter(artisan=artisan)
        .select_related("user", "artisan__user")
        .prefetch_related(
            "additional_fabric_photos",
            "reference_photos",
            "status_history",
        )
        .order_by("-created_at")
    )
    serializer = ArtisanUpcyclingRequestSerializer(
        requests,
        many=True,
        context={"request": request},
    )
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def artisan_request_action_api(request, pk):
    try:
        artisan = _get_artisan_profile(request.user)
    except PermissionDenied as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

    with transaction.atomic():
        upcycling_request = get_object_or_404(
            UpcyclingRequest.objects.select_for_update().filter(artisan=artisan),
            pk=pk,
        )
        serializer = ArtisanRequestActionSerializer(
            data=request.data,
            context={"upcycling_request": upcycling_request},
        )
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]
        note = serializer.validated_data.get("notes", "")
        old_status = upcycling_request.status
        now = timezone.now()

        if action == "review_accept":
            if old_status != UpcyclingRequest.Status.PENDING_REVIEW:
                return _status_conflict("Request ini tidak sedang menunggu review artisan.")
            upcycling_request.review_notes = note
            upcycling_request.review_approved_at = now
            upcycling_request.fabric_deadline = fabric_handoff_deadline(now)
            upcycling_request.status = UpcyclingRequest.Status.AWAITING_FABRIC
        elif action == "review_reject":
            if old_status != UpcyclingRequest.Status.PENDING_REVIEW:
                return _status_conflict("Request ini tidak sedang menunggu review artisan.")
            upcycling_request.rejection_stage = "PRELIMINARY_REVIEW"
            upcycling_request.rejection_reason = note
            upcycling_request.status = UpcyclingRequest.Status.REJECTED
        elif action == "receive_fabric":
            if old_status != UpcyclingRequest.Status.AWAITING_FABRIC:
                return _status_conflict("Kain belum dapat diterima pada status ini.")
            if (
                upcycling_request.fabric_deadline
                and upcycling_request.fabric_deadline < now
            ):
                return _status_conflict("Tenggat penyerahan kain sudah lewat.")
            upcycling_request.fabric_received_at = now
            upcycling_request.fabric_received_by = request.user
            upcycling_request.fabric_receipt_notes = note
            upcycling_request.status = UpcyclingRequest.Status.INSPECTION
        elif action in {"inspection_pass", "inspection_reject"}:
            if old_status != UpcyclingRequest.Status.INSPECTION:
                return _status_conflict("Request ini tidak sedang dalam pemeriksaan kain.")
            if action == "inspection_pass":
                upcycling_request.work_price = serializer.validated_data["work_price"]
                upcycling_request.batik_material_price = serializer.validated_data[
                    "batik_material_price"
                ]
                upcycling_request.additional_fee_type = serializer.validated_data[
                    "additional_fee_type"
                ]
                upcycling_request.additional_fee_amount = serializer.validated_data[
                    "additional_fee_amount"
                ]
                upcycling_request.quoted_price = serializer.validated_data[
                    "quoted_price"
                ]
                upcycling_request.quoted_at = now
                upcycling_request.quotation_notes = note
                upcycling_request.inspection_notes = note
                upcycling_request.status = UpcyclingRequest.Status.AWAITING_APPROVAL
            else:
                upcycling_request.inspection_notes = note
                upcycling_request.rejection_stage = "PHYSICAL_INSPECTION"
                upcycling_request.rejection_reason = note
                upcycling_request.return_status = (
                    UpcyclingRequest.ReturnStatus.PENDING_RETURN
                )
                upcycling_request.status = UpcyclingRequest.Status.REJECTED
        elif action == "mark_ready":
            if old_status != UpcyclingRequest.Status.IN_PROGRESS:
                return _status_conflict("Request ini belum dapat ditandai siap.")
            upcycling_request.ready_at = now
            upcycling_request.status = UpcyclingRequest.Status.READY

        upcycling_request.save()
        _record_api_status_change(upcycling_request, request.user, old_status)

    return Response(
        ArtisanUpcyclingRequestSerializer(
            upcycling_request,
            context={"request": request},
        ).data
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_request_list_api(request):
    allowed_statuses = (
        UpcyclingRequest.Status.PENDING_ASSIGNMENT,
        UpcyclingRequest.Status.PENDING_REVIEW,
        UpcyclingRequest.Status.IN_PROGRESS,
    )
    selected_status = request.query_params.get(
        "status",
        UpcyclingRequest.Status.PENDING_ASSIGNMENT,
    )
    if selected_status not in allowed_statuses:
        return Response(
            {"status": ["Status antrean admin tidak valid."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    requests = UpcyclingRequest.objects.filter(status=selected_status)
    if selected_status == UpcyclingRequest.Status.PENDING_ASSIGNMENT:
        requests = requests.filter(artisan__isnull=True)
    requests = (
        requests.select_related("user", "artisan__user")
        .prefetch_related(
            "additional_fabric_photos",
            "reference_photos",
            "status_history",
        )
        .order_by("created_at")
    )
    serializer = AdminQueueRowSerializer(
        requests,
        many=True,
        context={"request": request},
    )
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def admin_assign_artisan_api(request, pk):
    serializer = ArtisanAssignmentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        upcycling_request = assign_artisan_to_request(
            pk,
            serializer.validated_data["artisan_id"],
            assigned_by=request.user,
        )
    except ValidationError as exc:
        return Response(
            {"detail": exc.messages},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        ArtisanUpcyclingRequestSerializer(
            upcycling_request,
            context={"request": request},
        ).data
    )
