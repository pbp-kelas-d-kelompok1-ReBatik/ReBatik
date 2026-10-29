from functools import wraps
import json
import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import CheckoutForm, ProductForm
from .models import (
    MAX_ORDER_QUANTITY,
    DropOffPoint,
    Order,
    Product,
)
from .services import OrderTransitionNotAllowed, OutOfStock, cancel_order, place_order

PRODUCTS_PER_PAGE = 12
ORDERS_PER_PAGE = 10
MANAGE_PRODUCTS_PER_PAGE = 15


def staff_required(view_func):
    """Require an authenticated staff user; redirect guests and return styled 403 for non-staff."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_staff:
            return render(
                request,
                "marketplace/forbidden.html",
                {
                    "message": (
                        "Halaman ini hanya untuk tim pengelola (Staff) ReBatik. "
                        "Anda tidak memiliki izin untuk memanipulasi data katalog."
                    ),
                },
                status=403,
            )
        return view_func(request, *args, **kwargs)

    return _wrapped


def rate_limit_post(action_key, action_label, *, limit=8, window_seconds=60):
    """Protect sensitive POST endpoints against rapid automated submissions (HTTP 429)."""

    def _decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.method != "POST" or not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)

            cache_key = f"mp_rl:{action_key}:{request.user.pk}"
            now = int(time.time())
            entry = cache.get(cache_key)
            if not entry or now >= entry["reset_at"]:
                entry = {"count": 0, "reset_at": now + window_seconds}

            if entry["count"] >= limit:
                retry_after = max(1, entry["reset_at"] - now)
                response = render(
                    request,
                    "marketplace/rate_limited.html",
                    {
                        "action_label": action_label,
                        "retry_after": retry_after,
                    },
                    status=429,
                )
                response["Retry-After"] = str(retry_after)
                return response

            entry["count"] += 1
            cache.set(cache_key, entry, timeout=window_seconds)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return _decorator


def _htmx_location_or_redirect(request, route_name, **route_kwargs):
    """Navigate with an HTMX swap when requested; retain normal redirects otherwise."""
    destination = reverse(route_name, kwargs=route_kwargs or None)
    if request.headers.get("HX-Request") == "true":
        response = HttpResponse(status=204)
        response["HX-Location"] = json.dumps(
            {
                "path": destination,
                "target": "#marketplace-page-content",
                "select": "#marketplace-page-content",
                "swap": "outerHTML",
            }
        )
        return response
    return redirect(destination)


def product_list(request):
    """Display the public upcycled product catalogue with server-side filters."""
    base_qs = Product.objects.available()
    has_any_products = base_qs.exists()
    products = base_qs

    selected_category = request.GET.get("category", "").strip().upper()
    selected_query = request.GET.get("q", "").strip()[:100]
    selected_sort = request.GET.get("sort", "newest").strip()

    valid_categories = dict(Product.CATEGORY_CHOICES)
    if selected_category in valid_categories:
        products = products.filter(category=selected_category)
    else:
        selected_category = ""

    if selected_query:
        products = products.filter(
            Q(name__icontains=selected_query)
            | Q(motif__icontains=selected_query)
            | Q(material_source__icontains=selected_query)
            | Q(artisan_origin__icontains=selected_query)
            | Q(description__icontains=selected_query)
        )

    sort_map = {
        "newest": ("-created_at", "-pk"),
        "price_asc": ("price", "-created_at", "-pk"),
        "price_desc": ("-price", "-created_at", "-pk"),
    }
    if selected_sort not in sort_map:
        selected_sort = "newest"
    products = products.order_by(*sort_map[selected_sort])

    paginator = Paginator(products, PRODUCTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "products": page_obj.object_list,
        "page_obj": page_obj,
        "total_matching": paginator.count,
        "category_options": Product.CATEGORY_CHOICES,
        "sort_options": (
            ("newest", "Terbaru"),
            ("price_asc", "Harga Terendah"),
            ("price_desc", "Harga Tertinggi"),
        ),
        "selected_category": selected_category,
        "selected_query": selected_query,
        "selected_sort": selected_sort,
        "has_any_products": has_any_products,
    }
    return render(request, "marketplace/index.html", context)


marketplace_home = product_list


def product_detail(request, pk):
    """Display a single available product with its story and artisan specifications."""
    product = get_object_or_404(Product.objects.available(), pk=pk)
    related_products = (
        Product.objects.available()
        .filter(category=product.category)
        .exclude(pk=product.pk)[:3]
    )
    max_order_qty = min(MAX_ORDER_QUANTITY, max(product.stock, 1))
    return render(
        request,
        "marketplace/product_detail.html",
        {
            "product": product,
            "related_products": related_products,
            "max_order_qty": max_order_qty,
        },
    )


@login_required
@rate_limit_post("checkout", "pemesanan produk", limit=6, window_seconds=60)
def checkout(request, pk):
    """Validate and place an order while atomically reserving product stock."""
    product = get_object_or_404(Product.objects.available(), pk=pk)

    if request.method == "POST":
        form = CheckoutForm(request.POST, product=product)
        if form.is_valid():
            try:
                order = place_order(
                    request.user,
                    product.pk,
                    quantity=form.cleaned_data["quantity"],
                    delivery_method=form.cleaned_data["delivery_method"],
                    dropoff_point=form.cleaned_data.get("dropoff_point"),
                    address=form.cleaned_data.get("address", ""),
                    whatsapp=form.cleaned_data["whatsapp"],
                    notes=form.cleaned_data.get("notes", ""),
                )
            except OutOfStock as exc:
                product.refresh_from_db()
                if exc.available_stock <= 0:
                    form.add_error(
                        "quantity",
                        "Maaf, stok produk ini baru saja habis.",
                    )
                else:
                    form.add_error(
                        "quantity",
                        f"Stok tersisa tinggal {exc.available_stock} produk.",
                    )
            except Product.DoesNotExist:
                raise get_object_or_404(Product.objects.available(), pk=pk)
            else:
                return _htmx_location_or_redirect(
                    request,
                    "marketplace:order_success",
                    pk=order.pk,
                )
    else:
        initial = {
            "quantity": 1,
            "delivery_method": Order.DeliveryMethod.DROP_OFF,
        }
        raw_qty = request.GET.get("qty", "")
        if raw_qty.isdigit() and product.stock > 0:
            initial["quantity"] = max(
                1,
                min(int(raw_qty), MAX_ORDER_QUANTITY, product.stock),
            )
        form = CheckoutForm(product=product, initial=initial)

    return render(
        request,
        "marketplace/checkout_form.html",
        {
            "product": product,
            "form": form,
            "max_order_qty": min(MAX_ORDER_QUANTITY, max(product.stock, 1)),
        },
    )


@login_required
def order_success(request, pk):
    """Display confirmation details for a newly placed order."""
    order = get_object_or_404(
        Order.objects.select_related("product", "dropoff_point"),
        pk=pk,
        user=request.user,
    )
    return render(
        request,
        "marketplace/order_success.html",
        {
            "order": order,
            "reference_code": order.reference_code,
        },
    )


@login_required
def order_list(request):
    """List the signed-in buyer's marketplace orders with status filtering."""
    orders = Order.objects.filter(user=request.user).select_related(
        "product",
        "dropoff_point",
    )
    has_any_orders = orders.exists()

    selected_status = request.GET.get("status", "").strip().upper()
    valid_statuses = dict(Order.STATUS_CHOICES)

    if selected_status == "ONGOING":
        orders = orders.filter(
            status__in=[
                Order.Status.PENDING,
                Order.Status.PROCESSING,
                Order.Status.READY,
            ]
        )
    elif selected_status in valid_statuses:
        orders = orders.filter(status=selected_status)
    else:
        selected_status = ""

    page_obj = Paginator(orders, ORDERS_PER_PAGE).get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "marketplace/order_list.html",
        {
            "orders": page_obj.object_list,
            "page_obj": page_obj,
            "selected_status": selected_status,
            "status_options": Order.STATUS_CHOICES,
            "has_any_orders": has_any_orders,
        },
    )


def _build_order_timeline(order):
    """Return progress timeline steps matching the order's current status."""
    status = order.status
    steps = [
        {
            "label": "Pesanan Dibuat",
            "created_at": order.created_at,
            "state": "done",
        },
    ]

    if status == Order.Status.PENDING:
        steps.extend(
            [
                {"label": "Menunggu Konfirmasi Admin", "state": "current"},
                {"label": "Diproses Pengrajin", "state": "upcoming"},
                {"label": "Dikirim / Siap Diambil", "state": "upcoming"},
                {"label": "Selesai", "state": "upcoming"},
            ]
        )
    elif status == Order.Status.PROCESSING:
        steps.extend(
            [
                {"label": "Menunggu Konfirmasi Admin", "state": "done"},
                {"label": "Diproses Pengrajin · sedang berjalan", "state": "current"},
                {"label": "Dikirim / Siap Diambil", "state": "upcoming"},
                {"label": "Selesai", "state": "upcoming"},
            ]
        )
    elif status == Order.Status.READY:
        steps.extend(
            [
                {"label": "Menunggu Konfirmasi Admin", "state": "done"},
                {"label": "Diproses Pengrajin", "state": "done"},
                {"label": "Dikirim / Siap Diambil", "state": "current"},
                {"label": "Selesai", "state": "upcoming"},
            ]
        )
    elif status == Order.Status.COMPLETED:
        steps.extend(
            [
                {"label": "Menunggu Konfirmasi Admin", "state": "done"},
                {"label": "Diproses Pengrajin", "state": "done"},
                {"label": "Dikirim / Siap Diambil", "state": "done"},
                {"label": "Selesai · karya diterima", "state": "done"},
            ]
        )
    else:
        steps.append({"label": "Dibatalkan", "state": "cancelled"})

    return steps


@login_required
def order_detail(request, pk):
    """Display one owned order with its progress timeline and status history."""
    order = get_object_or_404(
        Order.objects.select_related("product", "dropoff_point"),
        pk=pk,
        user=request.user,
    )
    return render(
        request,
        "marketplace/order_detail.html",
        {
            "order": order,
            "reference_code": order.reference_code,
            "timeline_steps": _build_order_timeline(order),
            "status_history": order.status_history.select_related("changed_by"),
        },
    )


@login_required
@rate_limit_post("order_cancel", "pembatalan pesanan", limit=10, window_seconds=60)
def order_cancel(request, pk):
    """Cancel an owned pending order and restore product stock."""
    order = get_object_or_404(
        Order.objects.select_related("product", "dropoff_point"),
        pk=pk,
        user=request.user,
    )

    if request.method != "POST":
        if order.status != Order.Status.PENDING:
            messages.info(
                request,
                "Pesanan hanya bisa dibatalkan saat masih menunggu konfirmasi.",
            )
            return _htmx_location_or_redirect(
                request,
                "marketplace:order_detail",
                pk=order.pk,
            )
        return render(
            request,
            "marketplace/order_confirm_cancel.html",
            {
                "order": order,
                "reference_code": order.reference_code,
            },
        )

    try:
        cancel_order(order.pk, by_user=request.user, require_owner=True)
    except OrderTransitionNotAllowed:
        messages.info(
            request,
            "Pesanan hanya bisa dibatalkan saat masih menunggu konfirmasi.",
        )
    else:
        messages.success(
            request,
            "Pesanan berhasil dibatalkan dan stok produk telah dikembalikan.",
        )

    return _htmx_location_or_redirect(
        request,
        "marketplace:order_detail",
        pk=order.pk,
    )


@staff_required
def manage_product_list(request):
    """Staff dashboard listing active and hidden marketplace products."""
    all_products = Product.objects.all()
    visible_count = all_products.filter(is_deleted=False).count()
    out_of_stock_count = all_products.filter(is_deleted=False, stock=0).count()
    hidden_count = all_products.filter(is_deleted=True).count()

    selected_query = request.GET.get("q", "").strip()[:100]
    selected_visibility = request.GET.get("visibility", "").strip()

    products = all_products
    if selected_visibility == "visible":
        products = products.filter(is_deleted=False)
    elif selected_visibility == "hidden":
        products = products.filter(is_deleted=True)
    elif selected_visibility == "out_of_stock":
        products = products.filter(is_deleted=False, stock=0)
    else:
        selected_visibility = ""

    if selected_query:
        products = products.filter(
            Q(name__icontains=selected_query)
            | Q(motif__icontains=selected_query)
            | Q(artisan_origin__icontains=selected_query)
        )

    page_obj = Paginator(products, MANAGE_PRODUCTS_PER_PAGE).get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "marketplace/manage_product_list.html",
        {
            "products": page_obj.object_list,
            "page_obj": page_obj,
            "selected_query": selected_query,
            "selected_visibility": selected_visibility,
            "visible_count": visible_count,
            "out_of_stock_count": out_of_stock_count,
            "hidden_count": hidden_count,
        },
    )


@staff_required
@rate_limit_post("product_create", "penambahan produk", limit=10, window_seconds=60)
def manage_product_create(request):
    """Create a new marketplace catalogue product (staff only)."""
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.user = request.user
            product.save()
            messages.success(
                request,
                f"Produk '{product.name}' berhasil ditambahkan ke katalog.",
            )
            return _htmx_location_or_redirect(
                request,
                "marketplace:manage_product_list",
            )
    else:
        form = ProductForm()

    return render(
        request,
        "marketplace/manage_product_form.html",
        {
            "form": form,
            "is_update": False,
        },
    )


@staff_required
@rate_limit_post("product_update", "pembaruan produk", limit=15, window_seconds=60)
def manage_product_update(request, pk):
    """Update an existing marketplace product (staff only)."""
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            validated_product = form.save(commit=False)
            with transaction.atomic():
                current_product = get_object_or_404(
                    Product.objects.select_for_update(),
                    pk=pk,
                )
                for field_name in form.Meta.fields:
                    setattr(
                        current_product,
                        field_name,
                        getattr(validated_product, field_name),
                    )
                current_product.save(
                    update_fields=[*form.Meta.fields, "updated_at"]
                )
            messages.success(
                request,
                f"Produk '{current_product.name}' berhasil diperbarui.",
            )
            return _htmx_location_or_redirect(
                request,
                "marketplace:manage_product_list",
            )
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "marketplace/manage_product_form.html",
        {
            "form": form,
            "product": product,
            "is_update": True,
        },
    )


@staff_required
@rate_limit_post("product_delete", "penyembunyian produk", limit=15, window_seconds=60)
def manage_product_delete(request, pk):
    """Soft-delete (hide) a product so existing orders remain intact."""
    product = get_object_or_404(Product, pk=pk)

    if request.method != "POST":
        return render(
            request,
            "marketplace/manage_product_confirm_delete.html",
            {"product": product},
        )

    with transaction.atomic():
        locked = get_object_or_404(Product.objects.select_for_update(), pk=pk)
        locked.is_deleted = True
        locked.save(update_fields=["is_deleted", "updated_at"])

    messages.success(
        request,
        f"Produk '{product.name}' berhasil disembunyikan dari katalog.",
    )
    return _htmx_location_or_redirect(
        request,
        "marketplace:manage_product_list",
    )


@staff_required
@rate_limit_post("product_restore", "pemulihan produk", limit=15, window_seconds=60)
def manage_product_restore(request, pk):
    """Restore a previously hidden product back to the public catalogue."""
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        with transaction.atomic():
            locked = get_object_or_404(Product.objects.select_for_update(), pk=pk)
            locked.is_deleted = False
            locked.save(update_fields=["is_deleted", "updated_at"])
        messages.success(
            request,
            f"Produk '{product.name}' berhasil ditampilkan kembali di katalog.",
        )

    return _htmx_location_or_redirect(
        request,
        "marketplace:manage_product_list",
    )


def dropoff_list(request):
    """Display active fabric drop-off points with server-side city and search filters."""
    all_points = DropOffPoint.objects.all().order_by("city", "name")
    cities = sorted(
        list(
            DropOffPoint.objects.values_list("city", flat=True).distinct()
        )
    )

    selected_city = request.GET.get("city", "").strip()
    selected_query = request.GET.get("q", "").strip()[:100]

    drop_points = all_points
    if selected_city in cities:
        drop_points = drop_points.filter(city=selected_city)
    else:
        selected_city = ""

    if selected_query:
        drop_points = drop_points.filter(
            Q(name__icontains=selected_query)
            | Q(address__icontains=selected_query)
            | Q(city__icontains=selected_query)
        )

    context = {
        "drop_points": drop_points,
        "cities": cities,
        "selected_city": selected_city,
        "selected_query": selected_query,
        "has_any_drop_points": all_points.exists(),
    }
    return render(request, "marketplace/dropoff.html", context)


FALLBACK_PROVINCES = [
    {"id": "31", "name": "DKI JAKARTA"},
    {"id": "32", "name": "JAWA BARAT"},
    {"id": "33", "name": "JAWA TENGAH"},
    {"id": "34", "name": "DI YOGYAKARTA"},
    {"id": "35", "name": "JAWA TIMUR"},
    {"id": "36", "name": "BANTEN"},
]

FALLBACK_REGENCIES = {
    "31": [
        {"id": "3171", "name": "KOTA JAKARTA SELATAN"},
        {"id": "3172", "name": "KOTA JAKARTA TIMUR"},
        {"id": "3173", "name": "KOTA JAKARTA PUSAT"},
    ],
    "32": [
        {"id": "3276", "name": "KOTA DEPOK"},
        {"id": "3273", "name": "KOTA BANDUNG"},
        {"id": "3271", "name": "KOTA BOGOR"},
    ],
    "33": [
        {"id": "3372", "name": "KOTA SURAKARTA"},
        {"id": "3374", "name": "KOTA SEMARANG"},
        {"id": "3375", "name": "KOTA PEKALONGAN"},
    ],
    "34": [
        {"id": "3471", "name": "KOTA YOGYAKARTA"},
        {"id": "3404", "name": "KABUPATEN SLEMAN"},
    ],
    "35": [
        {"id": "3578", "name": "KOTA SURABAYA"},
        {"id": "3573", "name": "KOTA MALANG"},
    ],
    "36": [
        {"id": "3674", "name": "KOTA TANGERANG SELATAN"},
        {"id": "3671", "name": "KOTA TANGERANG"},
    ],
}


def regions_api(request):
    """Fetch Indonesian provinces/regencies from Emsifa API with server-side caching & fallback mitigation."""
    from urllib.error import URLError
    from urllib.request import urlopen

    province_id = request.GET.get("province_id", "").strip()
    if province_id and not province_id.isdigit():
        return JsonResponse({"items": [], "source": "invalid"}, status=400)

    cache_key = f"mp_emsifa_regions:{province_id or 'provinces'}"
    cached_items = cache.get(cache_key)
    if cached_items is not None:
        return JsonResponse({"items": cached_items, "source": "cache"})

    url = (
        f"https://www.emsifa.com/api-wilayah-indonesia/api/regencies/{province_id}.json"
        if province_id
        else "https://www.emsifa.com/api-wilayah-indonesia/api/provinces.json"
    )
    try:
        with urlopen(url, timeout=2.5) as resp:
            raw_data = json.loads(resp.read().decode("utf-8"))
            items = [
                {"id": str(item.get("id", "")), "name": str(item.get("name", ""))}
                for item in raw_data
                if isinstance(item, dict) and item.get("id") and item.get("name")
            ]
            cache.set(cache_key, items, timeout=86400)
            return JsonResponse({"items": items, "source": "remote"})
    except (URLError, TimeoutError, ValueError, OSError):
        fallback = (
            FALLBACK_REGENCIES.get(province_id, [])
            if province_id
            else FALLBACK_PROVINCES
        )
        cache.set(cache_key, fallback, timeout=300)
        return JsonResponse({"items": fallback, "source": "fallback"})

