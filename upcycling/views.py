from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.utils import timezone

from .forms import UpcyclingRequestForm
from .models import UpcyclingRequest


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
            upcycling_request = form.save(commit=False)
            upcycling_request.user = request.user
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
        {"form": form},
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
            form.save()
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
        {"form": form, "is_update": True},
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
        upcycling_request.delete()
        messages.success(request, "Permintaan berhasil dihapus.")
        return redirect("upcycling:request_list")

    return render(
        request,
        "upcycling/request_confirm_delete.html",
        {"upcycling_request": upcycling_request},
    )

@login_required
def product_options(request, category):
    products_by_category = {
        "TAS": ["TOTE_BAG", "SLING_BAG", "LAINNYA"],
        "POUCH": ["POUCH", "LAINNYA"],
        "PAKAIAN": ["KEMEJA", "LAINNYA"],
        "AKSESORIS": ["AKSESORIS", "LAINNYA"],
        "LAINNYA": ["LAINNYA"],
    }

    allowed_values = products_by_category.get(category, [])
    product_labels = dict(UpcyclingRequest.PRODUCT_CHOICES)

    data = [
        {"value": value, "label": product_labels[value]}
        for value in allowed_values
    ]

    return JsonResponse(data, safe=False)
