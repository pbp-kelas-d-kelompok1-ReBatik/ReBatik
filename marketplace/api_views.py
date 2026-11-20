"""Web service DRF Marketplace & Drop-off Point untuk aplikasi Flutter.

Semua endpoint berada di bawah ``/api/v1/marketplace/``. Logika bisnis
(validasi form, reservasi stok, voucher, pembatalan) memakai ulang
``forms.py`` dan ``services.py`` yang sama dengan halaman web.
"""
from django.db.models import Q
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from rewards.models import Reward, RewardRedemption

from .forms import CheckoutForm, ProductForm
from .models import DropOffPoint, Order, Product
from .permissions import IsArtisanStaffOrReadOnly
from .serializers import DropOffPointSerializer, OrderSerializer, ProductSerializer
from .services import (
    OrderTransitionNotAllowed,
    OutOfStock,
    VoucherUnavailable,
    cancel_order,
    place_order,
)
from .views import is_artisan_or_staff

PRODUCT_SORTS = {
    "newest": ("-created_at", "-pk"),
    "price_asc": ("price", "-created_at", "-pk"),
    "price_desc": ("-price", "-created_at", "-pk"),
}
PRODUCT_FORM_FIELDS = ProductForm._meta.fields


def _form_errors(form):
    """Ubah error Django Form ke format error DRF: {field: [pesan, ...]}."""
    return Response(
        {field: [str(msg) for msg in messages] for field, messages in form.errors.items()},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _orders_for(user):
    return (
        Order.objects.filter(user=user)
        .select_related("product", "dropoff_point", "reward_redemption")
        .prefetch_related("status_history")
    )


# ---------------------------------------------------------------- Produk


@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsArtisanStaffOrReadOnly])
def product_list(request):
    """GET: katalog produk (filter ``q``, ``category``, ``sort``).
    POST: tambah produk baru (Artisan/Admin)."""
    if request.method == "POST":
        form = ProductForm(data=request.data)
        if not form.is_valid():
            return _form_errors(form)
        product = form.save(commit=False)
        product.user = request.user
        product.save()
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)

    include_deleted = (
        request.query_params.get("include_deleted") in ("1", "true")
        and is_artisan_or_staff(request.user)
    )
    products = Product.objects.all() if include_deleted else Product.objects.available()

    category = request.query_params.get("category", "").strip().upper()
    if category in dict(Product.CATEGORY_CHOICES):
        products = products.filter(category=category)

    query = request.query_params.get("q", "").strip()[:100]
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(motif__icontains=query)
            | Q(material_source__icontains=query)
            | Q(artisan_origin__icontains=query)
            | Q(description__icontains=query)
        )

    sort = request.query_params.get("sort", "newest").strip()
    products = products.order_by(*PRODUCT_SORTS.get(sort, PRODUCT_SORTS["newest"]))
    return Response(ProductSerializer(products, many=True).data)


@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsArtisanStaffOrReadOnly])
def product_detail(request, pk):
    """GET detail produk; PUT/PATCH ubah produk; DELETE sembunyikan (soft delete)."""
    queryset = (
        Product.objects.all() if is_artisan_or_staff(request.user)
        else Product.objects.available()
    )
    product = get_object_or_404(queryset, pk=pk)

    if request.method in ("GET", "HEAD"):
        return Response(ProductSerializer(product).data)

    if request.method == "DELETE":
        # Sama seperti web: produk disembunyikan, bukan dihapus, karena
        # pesanan lama masih mereferensikannya (on_delete=PROTECT).
        product.is_deleted = True
        product.save(update_fields=["is_deleted", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    data = request.data
    if request.method == "PATCH":
        # PATCH: field yang tidak dikirim memakai nilai lama produk.
        incoming = request.data.dict() if hasattr(request.data, "dict") else dict(request.data)
        data = {**model_to_dict(product, fields=PRODUCT_FORM_FIELDS), **incoming}
    form = ProductForm(data=data, instance=product)
    if not form.is_valid():
        return _form_errors(form)
    form.save()
    return Response(ProductSerializer(product).data)


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsArtisanStaffOrReadOnly])
def product_restore(request, pk):
    """Tampilkan kembali produk yang sebelumnya disembunyikan."""
    product = get_object_or_404(Product, pk=pk)
    product.is_deleted = False
    product.save(update_fields=["is_deleted", "updated_at"])
    return Response(ProductSerializer(product).data)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def category_list(request):
    """Pilihan kategori produk untuk dropdown/chip filter di Flutter."""
    return Response([
        {"value": value, "label": label} for value, label in Product.CATEGORY_CHOICES
    ])


# ------------------------------------------------------- Drop-off Point


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def dropoff_point_list(request):
    """Daftar titik Drop-off (filter ``city`` dan ``q``)."""
    points = DropOffPoint.objects.all().order_by("city", "name")
    city = request.query_params.get("city", "").strip()[:100]
    if city:
        points = points.filter(city__iexact=city)
    query = request.query_params.get("q", "").strip()[:100]
    if query:
        points = points.filter(
            Q(name__icontains=query)
            | Q(address__icontains=query)
            | Q(city__icontains=query)
            | Q(province__icontains=query)
        )
    return Response(DropOffPointSerializer(points, many=True).data)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def dropoff_point_detail(request, pk):
    point = get_object_or_404(DropOffPoint, pk=pk)
    return Response(DropOffPointSerializer(point).data)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def dropoff_city_list(request):
    """Daftar kota unik untuk filter Drop-off Point."""
    cities = (
        DropOffPoint.objects.order_by("city").values_list("city", flat=True).distinct()
    )
    return Response(list(cities))


# --------------------------------------------------------------- Pesanan


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def order_list(request):
    """GET: riwayat pesanan milik user (filter ``status``).
    POST: checkout satu produk. Body: product, quantity, delivery_method,
    dropoff_point (id, jika DROP_OFF), address (jika KURIR), whatsapp,
    notes, voucher_code."""
    if request.method == "GET":
        orders = _orders_for(request.user)
        order_status = request.query_params.get("status", "").strip().upper()
        if order_status in dict(Order.STATUS_CHOICES):
            orders = orders.filter(status=order_status)
        return Response(OrderSerializer(orders, many=True).data)

    product_id = str(request.data.get("product", "")).strip()
    if not product_id.isdigit():
        return Response({"product": ["Pilih produk yang valid."]}, status=status.HTTP_400_BAD_REQUEST)
    product = get_object_or_404(Product.objects.available(), pk=int(product_id))
    form = CheckoutForm(data=request.data, product=product, user=request.user)
    if not form.is_valid():
        return _form_errors(form)

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
            voucher_code=form.cleaned_data.get("voucher_code", ""),
        )
    except VoucherUnavailable as exc:
        return Response({"voucher_code": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
    except OutOfStock as exc:
        return Response(
            {"quantity": [f"Stok tersedia tinggal {exc.available_stock} produk."]},
            status=status.HTTP_409_CONFLICT,
        )
    except Product.DoesNotExist:
        return Response({"detail": "Produk tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

    order = _orders_for(request.user).get(pk=order.pk)
    return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def order_detail(request, pk):
    order = get_object_or_404(_orders_for(request.user), pk=pk)
    return Response(OrderSerializer(order).data)


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def order_cancel(request, pk):
    """Batalkan pesanan milik user (hanya saat status PENDING); stok & voucher dikembalikan."""
    get_object_or_404(Order, pk=pk, user=request.user)
    try:
        cancel_order(pk, by_user=request.user, require_owner=True)
    except OrderTransitionNotAllowed as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    order = _orders_for(request.user).get(pk=pk)
    return Response(OrderSerializer(order).data)


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def voucher_list(request):
    """Voucher Rewards milik user yang masih bisa dipakai saat checkout."""
    redemptions = RewardRedemption.objects.filter(
        user=request.user,
        reward__reward_type=Reward.Type.VOUCHER,
        status=RewardRedemption.Status.FULFILLED,
        voucher_status=RewardRedemption.VoucherStatus.AVAILABLE,
    ).select_related("reward")
    return Response([
        {
            "voucher_code": item.voucher_code,
            "reward_name": item.reward.name,
            "discount_value": int(item.discount_value_snapshot or item.reward.discount_value or 0),
        }
        for item in redemptions
    ])
