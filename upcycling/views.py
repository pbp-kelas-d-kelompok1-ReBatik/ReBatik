from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import UpcyclingRequestForm, get_product_options_by_category
from .models import UpcyclingRequest

PENDING_REQUEST_LIMIT = 10
REQUESTS_PER_PAGE = 10
PENDING_LIMIT_MESSAGE = (
    "Anda sudah memiliki {limit} permintaan yang menunggu tinjauan. "
    "Tunggu sampai permintaan diproses sebelum mengajukan lagi."
)


@login_required
def request_list(request):
    requests = UpcyclingRequest.objects.filter(user=request.user)
    has_any_requests = requests.exists()

    selected_status = request.GET.get("status", "")
    selected_category = request.GET.get("category", "")

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
        "has_any_requests": has_any_requests,
    }
    return render(request, "upcycling/request_list.html", context)


@login_required
def request_create(request):
    if request.method == "POST":
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
                    return redirect(
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
                {"label": "Menunggu tinjauan", "state": "current"},
                {"label": "Diproses", "state": "upcoming"},
                {"label": "Selesai · estimasi 2 minggu", "state": "upcoming"},
            ]
        )
    elif status == UpcyclingRequest.Status.PROCESSING:
        timeline_steps.extend(
            [
                {"label": "Ditinjau", "state": "done"},
                {"label": "Diproses · sedang berjalan", "state": "current"},
                {"label": "Selesai · estimasi 2 minggu", "state": "upcoming"},
            ]
        )
    elif status == UpcyclingRequest.Status.COMPLETED:
        timeline_steps.extend(
            [
                {"label": "Ditinjau", "state": "done"},
                {"label": "Diproses", "state": "done"},
                {"label": "Selesai", "state": "done"},
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
        },
    )


@login_required
def request_update(request, pk):
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
        return redirect("upcycling:request_detail", pk=upcycling_request.pk)

    if request.method == "POST":
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
                    return redirect(
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
            return redirect(
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
        return redirect("upcycling:request_detail", pk=upcycling_request.pk)

    if request.method == "POST":
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
            return redirect("upcycling:request_list")

        messages.success(request, "Permintaan berhasil dihapus.")
        return redirect("upcycling:request_list")

    return render(
        request,
        "upcycling/request_confirm_delete.html",
        {"upcycling_request": upcycling_request},
    )
