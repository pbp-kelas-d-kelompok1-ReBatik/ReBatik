from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import UpcyclingRequestForm, get_product_options_by_category
from .models import UpcyclingRequest

PENDING_REQUEST_LIMIT = 10


@login_required
def request_list(request):
    requests = UpcyclingRequest.objects.filter(user=request.user)
    has_any_requests = requests.exists()

    selected_status = request.GET.get("status", "")
    selected_category = request.GET.get("category", "")

    valid_statuses = dict(UpcyclingRequest.STATUS_CHOICES)
    valid_categories = dict(UpcyclingRequest.CATEGORY_CHOICES)

    if selected_status == "ONGOING":
        requests = requests.filter(status__in=["PENDING", "PROCESSING"])
    elif selected_status in valid_statuses:
        requests = requests.filter(status=selected_status)
    else:
        selected_status = ""

    if selected_category in valid_categories:
        requests = requests.filter(category=selected_category)
    else:
        selected_category = ""

    context = {
        "requests": requests,
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
                    status="PENDING",
                ).count()

                if pending_count >= PENDING_REQUEST_LIMIT:
                    form.add_error(
                        None,
                        "Anda sudah memiliki 10 permintaan yang menunggu tinjauan. "
                        "Tunggu sampai permintaan diproses sebelum mengajukan lagi.",
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
            "reference_code": f"RB-{str(upcycling_request.pk).split('-')[0].upper()}",
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
    submitted_date = timezone.localtime(
        upcycling_request.created_at
    ).strftime("%d/%m/%Y")
    timeline_steps = [
        {"label": f"Diajukan · {submitted_date}", "state": "done"},
    ]

    if status == "PENDING":
        timeline_steps.extend(
            [
                {"label": "Menunggu tinjauan", "state": "current"},
                {"label": "Diproses", "state": "upcoming"},
                {"label": "Selesai · estimasi 2 minggu", "state": "upcoming"},
            ]
        )
    elif status == "PROCESSING":
        timeline_steps.extend(
            [
                {"label": "Ditinjau", "state": "done"},
                {"label": "Diproses · sedang berjalan", "state": "current"},
                {"label": "Selesai · estimasi 2 minggu", "state": "upcoming"},
            ]
        )
    elif status == "COMPLETED":
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
            "reference_code": f"RB-{str(upcycling_request.pk).split('-')[0].upper()}",
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

    if upcycling_request.status != "PENDING":
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
                if current_request.status != "PENDING":
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

    if upcycling_request.status != "PENDING":
        messages.info(
            request,
            "Permintaan hanya bisa dihapus saat masih menunggu tinjauan.",
        )
        return redirect("upcycling:request_detail", pk=upcycling_request.pk)

    if request.method == "POST":
        with transaction.atomic():
            deleted_count, _ = UpcyclingRequest.objects.filter(
                pk=pk,
                user=request.user,
                status="PENDING",
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
