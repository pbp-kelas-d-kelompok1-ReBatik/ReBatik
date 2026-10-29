import json
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from .forms import (
    FabricHandoffForm,
    ProductDeliveryForm,
    UpcyclingRequestForm,
    get_product_options_by_category,
)
from .models import (
    ArtisanProfile,
    NOTES_MAX_LENGTH,
    UpcyclingRateLimitBucket,
    UpcyclingRequest,
    UpcyclingStatusHistory,
    fabric_handoff_deadline,
)
from .security import consume_upcycling_rate_limit
from .services import assign_artisan_to_request, eligible_artisans_for_request

PENDING_REQUEST_LIMIT = 10
REQUESTS_PER_PAGE = 10
ACTION_RATE_LIMITS = {
    UpcyclingRateLimitBucket.Action.CREATE: (5, 60),
    UpcyclingRateLimitBucket.Action.UPDATE: (10, 60),
}
PENDING_LIMIT_MESSAGE = (
    "Anda sudah memiliki {limit} permintaan upcycling yang masih berjalan. "
    "Tunggu sampai ada request yang selesai sebelum mengajukan lagi."
)


def _parse_filter_date(value):
    """Parse a date-filter value, ignoring calendar-invalid input safely."""
    try:
        return parse_date(value)
    except ValueError:
        return None


def _htmx_location_or_redirect(request, route_name, **route_kwargs):
    """Navigate with an HTMX swap when requested; retain normal redirects otherwise."""
    destination = reverse(route_name, kwargs=route_kwargs or None)
    if request.headers.get("HX-Request") == "true":
        response = HttpResponse(status=204)
        response["HX-Location"] = json.dumps(
            {
                "path": destination,
                "target": "#upcycling-page-content",
                "select": "#upcycling-page-content",
                "swap": "outerHTML",
            }
        )
        return response
    return redirect(destination)


def _rate_limit_response(request, action):
    """Return a 429 response when this user has exhausted an action limit."""
    if request.method != "POST":
        return None

    limit, window_seconds = ACTION_RATE_LIMITS[action]
    allowed, retry_after = consume_upcycling_rate_limit(
        request.user,
        action,
        limit=limit,
        window_seconds=window_seconds,
    )
    if allowed:
        return None

    response = render(
        request,
        "upcycling/rate_limited.html",
        {
            "retry_after": retry_after,
            "action_label": UpcyclingRateLimitBucket.Action(action).label,
        },
        status=429,
    )
    response["Retry-After"] = str(retry_after)
    return response


def _get_artisan_profile(user):
    """Require the shared artisan role and an upcycling-specific profile."""
    if not user.groups.filter(name="Artisan").exists():
        raise PermissionDenied("Akun ini tidak memiliki peran artisan.")
    try:
        return user.artisan_profile
    except ArtisanProfile.DoesNotExist:
        raise PermissionDenied("Akun artisan ini belum memiliki profil Upcycling.") from None


@login_required
def request_list(request):
    """Show the signed-in user's requests with validated search and filters."""
    requests = UpcyclingRequest.objects.filter(user=request.user).only(
        "id",
        "fabric_photo",
        "fabric",
        "category",
        "product",
        "custom_product",
        "status",
        "created_at",
        "quantity",
    )
    has_any_requests = requests.exists()

    selected_status = request.GET.get("status", "")
    selected_category = request.GET.get("category", "")
    selected_query = request.GET.get("q", "").strip()[:100]
    selected_order = request.GET.get("order", "newest")
    selected_from_raw = request.GET.get("from", "")
    selected_to_raw = request.GET.get("to", "")
    selected_from = _parse_filter_date(selected_from_raw)
    selected_to = _parse_filter_date(selected_to_raw)

    valid_statuses = dict(UpcyclingRequest.STATUS_CHOICES)
    valid_categories = dict(UpcyclingRequest.CATEGORY_CHOICES)

    if selected_status == "ONGOING":
        requests = requests.exclude(status__in=UpcyclingRequest.TERMINAL_STATUSES)
    elif selected_status in valid_statuses:
        requests = requests.filter(status=selected_status)
    else:
        selected_status = ""

    if selected_category in valid_categories:
        requests = requests.filter(category=selected_category)
    else:
        selected_category = ""

    if selected_query:
        normalized_query = " ".join(
            selected_query.casefold().replace("_", " ").split()
        )
        matching_products = [
            value
            for value, label in UpcyclingRequest.PRODUCT_CHOICES
            if normalized_query
            in " ".join(value.casefold().replace("_", " ").split())
            or normalized_query in label.casefold()
        ]
        matching_fabrics = [
            value
            for value, label in UpcyclingRequest.FABRIC_CHOICES
            if normalized_query
            in " ".join(value.casefold().replace("_", " ").split())
            or normalized_query in label.casefold()
        ]
        search_filter = (
            Q(custom_product__icontains=selected_query)
            | Q(notes__icontains=selected_query)
        )
        if matching_products:
            search_filter |= Q(product__in=matching_products)
        if matching_fabrics:
            search_filter |= Q(fabric__in=matching_fabrics)
        requests = requests.filter(search_filter)
    if selected_from:
        start_at = timezone.make_aware(
            datetime.combine(selected_from, time.min)
        )
        requests = requests.filter(created_at__gte=start_at)
    else:
        selected_from_raw = ""
    if selected_to:
        end_at = timezone.make_aware(
            datetime.combine(selected_to, time.max)
        )
        requests = requests.filter(created_at__lte=end_at)
    else:
        selected_to_raw = ""

    order_options = {
        "newest": ("-created_at", "pk"),
        "oldest": ("created_at", "pk"),
        "quantity": ("-quantity", "-created_at", "pk"),
    }
    if selected_order not in order_options:
        selected_order = "newest"
    requests = requests.order_by(*order_options[selected_order])

    page_obj = Paginator(requests, REQUESTS_PER_PAGE).get_page(
        request.GET.get("page")
    )

    context = {
        "requests": page_obj.object_list,
        "page_obj": page_obj,
        "status_options": UpcyclingRequest.STATUS_CHOICES,
        "category_options": UpcyclingRequest.CATEGORY_CHOICES,
        "selected_status": selected_status,
        "selected_category": selected_category,
        "selected_query": selected_query,
        "selected_order": selected_order,
        "selected_from": selected_from_raw,
        "selected_to": selected_to_raw,
        "order_options": (
            ("newest", "Terbaru"),
            ("oldest", "Terlama"),
            ("quantity", "Jumlah terbanyak"),
        ),
        "has_any_requests": has_any_requests,
    }
    return render(request, "upcycling/request_list.html", context)


@login_required
def request_create(request):
    """Validate and create a request within the user's pending-request limit."""
    if request.method == "POST":
        rate_limit_response = _rate_limit_response(
            request,
            UpcyclingRateLimitBucket.Action.CREATE,
        )
        if rate_limit_response:
            return rate_limit_response

        form = UpcyclingRequestForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                # Lock the user row so concurrent submissions cannot pass the
                # pending-request limit at the same time.
                user = get_user_model().objects.select_for_update().get(
                    pk=request.user.pk
                )
                pending_count = UpcyclingRequest.objects.filter(user=user).exclude(
                    status__in=UpcyclingRequest.TERMINAL_STATUSES
                ).count()

                if pending_count >= PENDING_REQUEST_LIMIT:
                    form.add_error(
                        None,
                        PENDING_LIMIT_MESSAGE.format(
                            limit=PENDING_REQUEST_LIMIT
                        ),
                    )
                else:
                    upcycling_request = form.save(commit=False)
                    upcycling_request.user = user
                    upcycling_request.status = UpcyclingRequest.Status.PENDING_ASSIGNMENT
                    upcycling_request.save()
                    UpcyclingStatusHistory.objects.create(
                        request=upcycling_request,
                        to_status=upcycling_request.status,
                        changed_by=user,
                    )
                    return _htmx_location_or_redirect(
                        request,
                        "upcycling:request_success",
                        pk=upcycling_request.pk,
                    )
    else:
        pending_count = UpcyclingRequest.objects.filter(user=request.user).exclude(
            status__in=UpcyclingRequest.TERMINAL_STATUSES
        ).count()
        if pending_count >= PENDING_REQUEST_LIMIT:
            messages.info(
                request,
                PENDING_LIMIT_MESSAGE.format(limit=PENDING_REQUEST_LIMIT),
            )
            return redirect("upcycling:request_list")

        form = UpcyclingRequestForm()

    return render(
        request,
        "upcycling/request_form.html",
        {
            "form": form,
            "product_options_by_category": get_product_options_by_category(),
        },
    )


@login_required
def request_success(request, pk):
    """Show the confirmation page for the signed-in user's new request."""
    upcycling_request = get_object_or_404(
        UpcyclingRequest,
        pk=pk,
        user=request.user,
    )

    return render(
        request,
        "upcycling/request_success.html",
        {
            "upcycling_request": upcycling_request,
            "reference_code": upcycling_request.reference_code,
        },
    )


@login_required
def request_detail(request, pk):
    """Show an owned request or a request assigned to the signed-in artisan."""
    artisan = None
    if request.user.groups.filter(name="Artisan").exists():
        artisan = ArtisanProfile.objects.filter(user=request.user).first()

    accessible_requests = UpcyclingRequest.objects.select_related("user", "artisan__user")
    if artisan:
        upcycling_request = get_object_or_404(
            accessible_requests.filter(Q(user=request.user) | Q(artisan=artisan)),
            pk=pk,
        )
    else:
        upcycling_request = get_object_or_404(
            accessible_requests,
            pk=pk,
            user=request.user,
        )
    is_assigned_artisan = bool(
        artisan
        and upcycling_request.artisan_id == artisan.pk
        and upcycling_request.user_id != request.user.pk
    )

    status = upcycling_request.status
    status_history = list(
        upcycling_request.status_history.select_related("changed_by")
    )
    status_dates = {
        item.to_status: item.changed_at
        for item in status_history
    }
    timeline_steps = [
        {
            "label": "Diajukan",
            "created_at": upcycling_request.created_at,
            "state": "done",
        },
    ]

    progression = [
        UpcyclingRequest.Status.PENDING_ASSIGNMENT,
        UpcyclingRequest.Status.PENDING_REVIEW,
        UpcyclingRequest.Status.AWAITING_FABRIC,
        UpcyclingRequest.Status.INSPECTION,
        UpcyclingRequest.Status.AWAITING_APPROVAL,
        UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS,
        UpcyclingRequest.Status.IN_PROGRESS,
        UpcyclingRequest.Status.READY,
        UpcyclingRequest.Status.COMPLETED,
    ]
    if status in progression:
        current_index = progression.index(status)
        for index, value in enumerate(progression):
            timeline_steps.append({
                "label": UpcyclingRequest.Status(value).label,
                "state": "done" if index < current_index else "current" if index == current_index else "upcoming",
                    "created_at": status_dates.get(value),
            })
    else:
        timeline_steps.append({"label": upcycling_request.get_status_display(), "state": "cancelled"})

    next_steps = {
        UpcyclingRequest.Status.PENDING_ASSIGNMENT: {
            "title": "Menunggu penugasan artisan",
            "description": "Admin sedang mencocokkan permintaan dengan keahlian dan kapasitas artisan.",
        },
        UpcyclingRequest.Status.PENDING_REVIEW: {
            "title": "Menunggu review awal",
            "description": "Artisan meninjau model produk dan informasi kain yang Anda kirim.",
        },
        UpcyclingRequest.Status.AWAITING_FABRIC: {
            "title": "Serahkan kain",
            "description": "Serahkan kain dengan metode yang dipilih sebelum tenggat agar request tidak kedaluwarsa.",
            "deadline": upcycling_request.fabric_deadline,
        },
        UpcyclingRequest.Status.INSPECTION: {
            "title": "Menunggu hasil inspeksi",
            "description": "Artisan sedang memeriksa kondisi fisik kain dan menyiapkan penawaran final.",
        },
        UpcyclingRequest.Status.AWAITING_APPROVAL: {
            "title": "Tinjau penawaran harga",
            "description": "Periksa harga dan catatan artisan. Anda dapat menyetujui atau menolak penawaran.",
        },
        UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS: {
            "title": "Atur penerimaan produk",
            "description": "Harga sudah disetujui. Isi metode dan alamat penerimaan sebelum produksi dimulai.",
        },
        UpcyclingRequest.Status.IN_PROGRESS: {
            "title": "Produk sedang dibuat",
            "description": "Artisan sedang mengerjakan produk. Tunggu pembaruan saat produk siap diserahkan.",
        },
        UpcyclingRequest.Status.READY: {
            "title": "Konfirmasi penerimaan produk",
            "description": "Setelah produk diterima, konfirmasikan penerimaannya untuk menyelesaikan request.",
        },
        UpcyclingRequest.Status.COMPLETED: {
            "title": "Request selesai",
            "description": "Produk telah diterima dan poin upcycling sudah tercatat.",
        },
        UpcyclingRequest.Status.REJECTED: {
            "title": "Request ditolak",
            "description": "Periksa alasan penolakan dan status pengembalian kain pada ringkasan request.",
        },
        UpcyclingRequest.Status.CANCELLED: {
            "title": "Request dibatalkan",
            "description": "Periksa status pengembalian kain pada ringkasan request jika kain sudah diterima.",
        },
        UpcyclingRequest.Status.EXPIRED: {
            "title": "Batas penyerahan kain terlewati",
            "description": "Request kedaluwarsa karena kain belum diserahkan sebelum tenggat.",
        },
    }
    next_step = next_steps[status]
    if is_assigned_artisan:
        if status == UpcyclingRequest.Status.AWAITING_APPROVAL:
            next_step = {
                "title": "Menunggu persetujuan user",
                "description": "Produksi hanya dapat dimulai setelah user menyetujui penawaran harga.",
            }
        elif status == UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS:
            next_step = {
                "title": "Menunggu detail penerimaan produk",
                "description": "User sedang melengkapi metode dan lokasi penerimaan sebelum produksi dimulai.",
            }
        elif status == UpcyclingRequest.Status.READY:
            next_step = {
                "title": "Menunggu konfirmasi user",
                "description": "User perlu mengonfirmasi penerimaan produk sebelum request selesai.",
            }
        elif status not in UpcyclingRequest.TERMINAL_STATUSES:
            next_step = {
                "title": "Tindakan Artisan",
                "description": "Gunakan panel tindakan di bawah untuk memproses request sesuai statusnya.",
            }

    return render(
        request,
        "upcycling/request_detail.html",
        {
            "upcycling_request": upcycling_request,
            "reference_code": upcycling_request.reference_code,
            "timeline_steps": timeline_steps,
            "status_history": status_history,
            "next_step": next_step,
            "is_assigned_artisan": is_assigned_artisan,
            "can_approve_quote": not is_assigned_artisan and status == UpcyclingRequest.Status.AWAITING_APPROVAL,
            "product_delivery_form": (
                ProductDeliveryForm(instance=upcycling_request)
                if not is_assigned_artisan and status == UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS
                else None
            ),
            "can_submit_product_delivery": not is_assigned_artisan and status == UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS,
            "can_confirm_receipt": not is_assigned_artisan and status == UpcyclingRequest.Status.READY,
            "can_cancel": not is_assigned_artisan and status in {
                UpcyclingRequest.Status.PENDING_ASSIGNMENT,
                UpcyclingRequest.Status.PENDING_REVIEW,
                UpcyclingRequest.Status.AWAITING_FABRIC,
                UpcyclingRequest.Status.INSPECTION,
                UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS,
            },
            "fabric_handoff_form": (
                FabricHandoffForm(instance=upcycling_request)
                if not is_assigned_artisan and status == UpcyclingRequest.Status.AWAITING_FABRIC
                else None
            ),
        },
    )


@login_required
def submit_fabric_handoff(request, pk):
    """Save fabric delivery details after the artisan's preliminary approval."""
    if request.method != "POST":
        return redirect("upcycling:request_detail", pk=pk)

    with transaction.atomic():
        upcycling_request = get_object_or_404(
            UpcyclingRequest.objects.select_for_update(),
            pk=pk,
            user=request.user,
        )
        if upcycling_request.status != UpcyclingRequest.Status.AWAITING_FABRIC:
            messages.error(
                request,
                "Rencana penyerahan kain hanya dapat diisi setelah review awal disetujui.",
            )
        elif (
            upcycling_request.fabric_deadline
            and upcycling_request.fabric_deadline < timezone.now()
        ):
            messages.error(request, "Tenggat penyerahan kain sudah lewat.")
        else:
            form = FabricHandoffForm(request.POST, instance=upcycling_request)
            if form.is_valid():
                form.save()
                messages.success(request, "Rencana penyerahan kain berhasil disimpan.")
            else:
                messages.error(request, "Isi cara dan lokasi penyerahan kain dengan benar.")

    return redirect("upcycling:request_detail", pk=pk)


@login_required
def request_update(request, pk):
    """Update an owned request while it is still awaiting review."""
    upcycling_request = get_object_or_404(
        UpcyclingRequest,
        pk=pk,
        user=request.user,
    )

    if upcycling_request.status != UpcyclingRequest.Status.PENDING_ASSIGNMENT:
        messages.info(
            request,
            "Permintaan hanya bisa diedit saat masih menunggu tinjauan.",
        )
        return _htmx_location_or_redirect(
            request,
            "upcycling:request_detail",
            pk=upcycling_request.pk,
        )

    if request.method == "POST":
        rate_limit_response = _rate_limit_response(
            request,
            UpcyclingRateLimitBucket.Action.UPDATE,
        )
        if rate_limit_response:
            return rate_limit_response

        form = UpcyclingRequestForm(
            request.POST,
            request.FILES,
            instance=upcycling_request,
        )
        if form.is_valid():
            validated_request = form.save(commit=False)
            with transaction.atomic():
                current_request = get_object_or_404(
                    UpcyclingRequest.objects.select_for_update(),
                    pk=pk,
                    user=request.user,
                )
                if current_request.status != UpcyclingRequest.Status.PENDING_ASSIGNMENT:
                    messages.info(
                        request,
                        "Permintaan hanya bisa diedit saat masih menunggu tinjauan.",
                    )
                    return _htmx_location_or_redirect(
                        request,
                        "upcycling:request_detail",
                        pk=current_request.pk,
                    )

                # Copy only fields exposed by the form. This keeps status and
                # owner values from the freshly locked database row.
                for field_name in form.Meta.fields:
                    setattr(
                        current_request,
                        field_name,
                        getattr(validated_request, field_name),
                    )
                current_request.save(
                    update_fields=[*form.Meta.fields, "updated_at"]
                )

            messages.success(request, "Permintaan berhasil diperbarui.")
            return _htmx_location_or_redirect(
                request,
                "upcycling:request_detail",
                pk=upcycling_request.pk,
            )
    else:
        form = UpcyclingRequestForm(instance=upcycling_request)

    return render(
        request,
        "upcycling/request_form.html",
        {
            "form": form,
            "is_update": True,
            "product_options_by_category": get_product_options_by_category(),
        },
    )


@login_required
def request_delete(request, pk):
    """Keep submitted requests auditable and direct users to cancellation."""
    upcycling_request = get_object_or_404(
        UpcyclingRequest,
        pk=pk,
        user=request.user,
    )
    messages.info(
        request,
        "Permintaan yang sudah diajukan tidak dapat dihapus. Gunakan tombol Batalkan permintaan untuk menghentikan proses.",
    )
    return _htmx_location_or_redirect(
        request,
        "upcycling:request_detail",
        pk=upcycling_request.pk,
    )


def _record_user_status_change(upcycling_request, user, old_status):
    UpcyclingStatusHistory.objects.create(
        request=upcycling_request,
        from_status=old_status,
        to_status=upcycling_request.status,
        changed_by=user,
    )


@login_required
def approve_quote(request, pk):
    if request.method != "POST":
        return redirect("upcycling:request_detail", pk=pk)
    with transaction.atomic():
        upcycling_request = get_object_or_404(
            UpcyclingRequest.objects.select_for_update(), pk=pk, user=request.user
        )
        if upcycling_request.status != UpcyclingRequest.Status.AWAITING_APPROVAL or upcycling_request.quoted_price is None:
            messages.error(request, "Penawaran belum tersedia untuk disetujui.")
        else:
            old_status = upcycling_request.status
            upcycling_request.approved_at = timezone.now()
            upcycling_request.status = UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS
            upcycling_request.save(update_fields=("approved_at", "status", "updated_at"))
            _record_user_status_change(upcycling_request, request.user, old_status)
            messages.success(request, "Harga disetujui. Lengkapi metode dan lokasi penerimaan produk sebelum produksi.")
    return redirect("upcycling:request_detail", pk=pk)


@login_required
def submit_product_delivery(request, pk):
    if request.method != "POST":
        return redirect("upcycling:request_detail", pk=pk)
    with transaction.atomic():
        upcycling_request = get_object_or_404(
            UpcyclingRequest.objects.select_for_update(), pk=pk, user=request.user
        )
        if upcycling_request.status != UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS:
            messages.error(request, "Detail penerimaan produk belum dapat diisi pada tahap ini.")
        else:
            form = ProductDeliveryForm(request.POST, instance=upcycling_request)
            if not form.is_valid():
                messages.error(request, "Pilih metode penerimaan produk dan isi alamat atau lokasi penerimaan.")
                return redirect("upcycling:request_detail", pk=pk)
            old_status = upcycling_request.status
            form.save()
            upcycling_request.status = UpcyclingRequest.Status.IN_PROGRESS
            upcycling_request.save(update_fields=("status", "updated_at", "delivery_method", "address"))
            _record_user_status_change(upcycling_request, request.user, old_status)
            messages.success(request, "Detail penerimaan tersimpan. Request mulai diproduksi.")
    return redirect("upcycling:request_detail", pk=pk)


@login_required
def confirm_completion(request, pk):
    if request.method != "POST":
        return redirect("upcycling:request_detail", pk=pk)
    with transaction.atomic():
        upcycling_request = get_object_or_404(
            UpcyclingRequest.objects.select_for_update(), pk=pk, user=request.user
        )
        if (
            upcycling_request.status != UpcyclingRequest.Status.READY
        ):
            messages.error(request, "Request belum siap dikonfirmasi selesai.")
        else:
            old_status = upcycling_request.status
            upcycling_request.status = UpcyclingRequest.Status.COMPLETED
            upcycling_request.completed_by = request.user
            upcycling_request.completed_at = timezone.now()
            upcycling_request.save(update_fields=("status", "completed_by", "completed_at", "updated_at"))
            _record_user_status_change(upcycling_request, request.user, old_status)
            from rewards.services import award_upcycling_completion

            award_upcycling_completion(
                request.user,
                request_reference=str(upcycling_request.pk),
                upcycling_request=upcycling_request,
            )
            messages.success(request, "Penerimaan dikonfirmasi. Poin upcycling sudah ditambahkan.")
    return redirect("upcycling:request_detail", pk=pk)


@login_required
def cancel_request(request, pk):
    if request.method != "POST":
        return redirect("upcycling:request_detail", pk=pk)
    with transaction.atomic():
        upcycling_request = get_object_or_404(
            UpcyclingRequest.objects.select_for_update(), pk=pk, user=request.user
        )
        reject_quote = request.POST.get("action") == "reject_quote"
        cancellable_statuses = {
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
            UpcyclingRequest.Status.PENDING_REVIEW,
            UpcyclingRequest.Status.AWAITING_FABRIC,
            UpcyclingRequest.Status.INSPECTION,
            UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS,
        }
        can_reject_quote = (
            reject_quote
            and upcycling_request.status == UpcyclingRequest.Status.AWAITING_APPROVAL
        )
        invalid_quote_rejection = reject_quote and not can_reject_quote
        if invalid_quote_rejection or (
            not reject_quote and upcycling_request.status not in cancellable_statuses
        ):
            messages.error(request, "Request ini tidak dapat dibatalkan mandiri. Hubungi admin untuk bantuan.")
        else:
            old_status = upcycling_request.status
            upcycling_request.status = UpcyclingRequest.Status.CANCELLED
            if can_reject_quote:
                upcycling_request.cancellation_reason = "Penawaran harga ditolak oleh user."
            else:
                upcycling_request.cancellation_reason = "Dibatalkan oleh user."
            if upcycling_request.fabric_received_at:
                upcycling_request.return_status = UpcyclingRequest.ReturnStatus.PENDING_RETURN
            upcycling_request.save(update_fields=("status", "cancellation_reason", "return_status", "updated_at"))
            _record_user_status_change(upcycling_request, request.user, old_status)
            if can_reject_quote:
                messages.success(request, "Penawaran ditolak. Kain akan dikembalikan.")
            else:
                messages.success(request, "Request dibatalkan.")
    return redirect("upcycling:request_detail", pk=pk)


@login_required
def artisan_dashboard(request):
    artisan = _get_artisan_profile(request.user)
    assigned_requests = UpcyclingRequest.objects.filter(artisan=artisan).select_related("user")
    return render(
        request,
        "upcycling/artisan_dashboard.html",
        {"artisan": artisan, "requests": assigned_requests},
    )


@staff_member_required(login_url="/admin/login/")
def admin_dashboard(request):
    pending_requests = (
        UpcyclingRequest.objects.filter(
            status=UpcyclingRequest.Status.PENDING_ASSIGNMENT,
            artisan__isnull=True,
        )
        .select_related("user")
        .order_by("created_at")
    )
    request_rows = [
        {
            "request": upcycling_request,
            "candidates": eligible_artisans_for_request(upcycling_request),
        }
        for upcycling_request in pending_requests
    ]
    return render(
        request,
        "upcycling/admin_dashboard.html",
        {
            "request_rows": request_rows,
            "pending_assignment_count": pending_requests.count(),
            "pending_review_count": UpcyclingRequest.objects.filter(
                status=UpcyclingRequest.Status.PENDING_REVIEW
            ).count(),
            "in_progress_count": UpcyclingRequest.objects.filter(
                status=UpcyclingRequest.Status.IN_PROGRESS
            ).count(),
        },
    )


@staff_member_required(login_url="/admin/login/")
def admin_assign_artisan(request, pk):
    if request.method != "POST":
        return redirect("upcycling:admin_dashboard")

    artisan_id = request.POST.get("artisan", "").strip()
    try:
        if not artisan_id.isdecimal():
            raise ValidationError("Pilih artisan yang valid.")
        assign_artisan_to_request(
            pk,
            int(artisan_id),
            assigned_by=request.user,
        )
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, "Artisan berhasil ditugaskan. Request menunggu review artisan.")
    return redirect("upcycling:admin_dashboard")


@login_required
def artisan_update_request(request, pk):
    if request.method != "POST":
        return redirect("upcycling:artisan_dashboard")
    artisan = _get_artisan_profile(request.user)
    action = request.POST.get("action", "")
    with transaction.atomic():
        upcycling_request = get_object_or_404(
            UpcyclingRequest.objects.select_for_update(), pk=pk, artisan=artisan
        )
        old_status = upcycling_request.status
        now = timezone.now()
        note = request.POST.get("notes", "").strip()[:NOTES_MAX_LENGTH]
        try:
            if action == "review_accept" and old_status == UpcyclingRequest.Status.PENDING_REVIEW:
                upcycling_request.review_notes = note
                upcycling_request.review_approved_at = now
                upcycling_request.fabric_deadline = fabric_handoff_deadline(now)
                upcycling_request.status = UpcyclingRequest.Status.AWAITING_FABRIC
            elif action == "review_reject" and old_status == UpcyclingRequest.Status.PENDING_REVIEW:
                if not note:
                    raise ValueError("Masukkan alasan penolakan.")
                upcycling_request.rejection_stage = "PRELIMINARY_REVIEW"
                upcycling_request.rejection_reason = note
                upcycling_request.status = UpcyclingRequest.Status.REJECTED
            elif action == "receive_fabric" and old_status == UpcyclingRequest.Status.AWAITING_FABRIC:
                if upcycling_request.fabric_deadline and upcycling_request.fabric_deadline < now:
                    raise ValueError("Tenggat penyerahan kain sudah lewat.")
                upcycling_request.fabric_received_at = now
                upcycling_request.fabric_received_by = request.user
                upcycling_request.fabric_receipt_notes = note
                upcycling_request.status = UpcyclingRequest.Status.INSPECTION
            elif action in {"inspection_pass", "inspection_reject"} and old_status == UpcyclingRequest.Status.INSPECTION:
                if action == "inspection_pass":
                    try:
                        price = Decimal(request.POST.get("quoted_price", ""))
                    except (InvalidOperation, TypeError, ValueError):
                        raise ValueError("Masukkan harga final yang valid.") from None
                    if not price.is_finite() or price <= 0:
                        raise ValueError("Harga final harus lebih dari nol.")
                    if price != price.to_integral_value():
                        raise ValueError("Harga final harus menggunakan nominal rupiah tanpa pecahan.")
                    if price > Decimal("99999999"):
                        raise ValueError("Harga final tidak boleh melebihi Rp99.999.999.")
                    upcycling_request.quoted_price = price
                    upcycling_request.quoted_at = now
                    upcycling_request.quotation_notes = note
                    upcycling_request.inspection_notes = note
                    upcycling_request.status = UpcyclingRequest.Status.AWAITING_APPROVAL
                else:
                    if not note:
                        raise ValueError("Masukkan alasan kain tidak layak.")
                    upcycling_request.inspection_notes = note
                    upcycling_request.rejection_stage = "PHYSICAL_INSPECTION"
                    upcycling_request.rejection_reason = note
                    upcycling_request.return_status = UpcyclingRequest.ReturnStatus.PENDING_RETURN
                    upcycling_request.status = UpcyclingRequest.Status.REJECTED
            elif action == "mark_ready" and old_status == UpcyclingRequest.Status.IN_PROGRESS:
                upcycling_request.ready_at = now
                upcycling_request.status = UpcyclingRequest.Status.READY
            else:
                raise ValueError("Aksi ini tidak berlaku untuk status request sekarang.")
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            upcycling_request.save()
            _record_user_status_change(upcycling_request, request.user, old_status)
            messages.success(request, "Status request berhasil diperbarui.")
    return redirect("upcycling:artisan_dashboard")
