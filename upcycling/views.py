import json
from datetime import datetime, time

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from .forms import UpcyclingRequestForm, get_product_options_by_category
from .models import (
    UpcyclingRateLimitBucket,
    UpcyclingRequest,
    UpcyclingStatusHistory,
)
from .security import consume_upcycling_rate_limit

PENDING_REQUEST_LIMIT = 10
REQUESTS_PER_PAGE = 10
ACTION_RATE_LIMITS = {
    UpcyclingRateLimitBucket.Action.CREATE: (5, 60),
    UpcyclingRateLimitBucket.Action.UPDATE: (10, 60),
    UpcyclingRateLimitBucket.Action.DELETE: (10, 60),
}
PENDING_LIMIT_MESSAGE = (
    "Anda sudah memiliki {limit} permintaan yang menunggu tinjauan. "
    "Tunggu sampai permintaan diproses sebelum mengajukan lagi."
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


@login_required
def request_list(request):
    """Show the signed-in user's requests with validated search and filters."""
    requests = UpcyclingRequest.objects.filter(user=request.user).only(
        "id",
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
        requests = requests.filter(
            status__in=[
                UpcyclingRequest.Status.PENDING,
                UpcyclingRequest.Status.PROCESSING,
            ]
        )
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

        form = UpcyclingRequestForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Lock the user row so concurrent submissions cannot pass the
                # pending-request limit at the same time.
                user = get_user_model().objects.select_for_update().get(
                    pk=request.user.pk
                )
                pending_count = UpcyclingRequest.objects.filter(
                    user=user,
                    status=UpcyclingRequest.Status.PENDING,
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
        pending_count = UpcyclingRequest.objects.filter(
            user=request.user,
            status=UpcyclingRequest.Status.PENDING,
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
    """Show one owned request with its progress timeline and status history."""
    upcycling_request = get_object_or_404(
        UpcyclingRequest,
        pk=pk,
        user=request.user,
    )

    status = upcycling_request.status
    timeline_steps = [
        {
            "label": "Diajukan",
            "created_at": upcycling_request.created_at,
            "state": "done",
        },
    ]

    if status == UpcyclingRequest.Status.PENDING:
        timeline_steps.extend(
            [
                {"label": "Menunggu Tinjauan", "state": "current"},
                {"label": "Diproses", "state": "upcoming"},
                {"label": "Selesai", "state": "upcoming"},
            ]
        )
    elif status == UpcyclingRequest.Status.PROCESSING:
        timeline_steps.extend(
            [
                {"label": "Menunggu Tinjauan", "state": "done"},
                {"label": "Diproses · sedang berjalan", "state": "current"},
                {"label": "Selesai", "state": "upcoming"},
            ]
        )
    elif status == UpcyclingRequest.Status.COMPLETED:
        timeline_steps.extend(
            [
                {"label": "Menunggu Tinjauan", "state": "done"},
                {"label": "Diproses", "state": "done"},
                {"label": "Selesai · produk diterima", "state": "done"},
            ]
        )
    else:
        timeline_steps.append({"label": "Dibatalkan", "state": "cancelled"})

    return render(
        request,
        "upcycling/request_detail.html",
        {
            "upcycling_request": upcycling_request,
            "reference_code": upcycling_request.reference_code,
            "timeline_steps": timeline_steps,
            "status_history": upcycling_request.status_history.select_related(
                "changed_by"
            ),
        },
    )


@login_required
def request_update(request, pk):
    """Update an owned request while it is still awaiting review."""
    upcycling_request = get_object_or_404(
        UpcyclingRequest,
        pk=pk,
        user=request.user,
    )

    if upcycling_request.status != UpcyclingRequest.Status.PENDING:
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
                if current_request.status != UpcyclingRequest.Status.PENDING:
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
    """Delete an owned pending request after an authenticated POST."""
    upcycling_request = get_object_or_404(
        UpcyclingRequest,
        pk=pk,
        user=request.user,
    )

    if upcycling_request.status != UpcyclingRequest.Status.PENDING:
        messages.info(
            request,
            "Permintaan hanya bisa dihapus saat masih menunggu tinjauan.",
        )
        return _htmx_location_or_redirect(
            request,
            "upcycling:request_detail",
            pk=upcycling_request.pk,
        )

    if request.method == "POST":
        rate_limit_response = _rate_limit_response(
            request,
            UpcyclingRateLimitBucket.Action.DELETE,
        )
        if rate_limit_response:
            return rate_limit_response

        deleted_count, _ = UpcyclingRequest.objects.filter(
            pk=pk,
            user=request.user,
            status=UpcyclingRequest.Status.PENDING,
        ).delete()

        if not deleted_count:
            messages.info(
                request,
                "Permintaan tidak dapat dihapus karena statusnya sudah berubah.",
            )
            return _htmx_location_or_redirect(request, "upcycling:request_list")

        messages.success(request, "Permintaan berhasil dihapus.")
        if request.headers.get("HX-Request") == "true":
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse("upcycling:request_list")
            return response
        return _htmx_location_or_redirect(request, "upcycling:request_list")

    return render(
        request,
        "upcycling/request_confirm_delete.html",
        {"upcycling_request": upcycling_request},
    )
