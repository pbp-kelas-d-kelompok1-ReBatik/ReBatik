from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from batik_custom.models import (
    BatikOrder, ColorPalette, ProductDesignOption, RecommendedMotif,
    SavedDesign, StyleOptions,
)
from batik_custom.serializers import (
    BatikOrderSerializer, ColorPaletteSerializer, ProductDesignOptionSerializer,
    RecommendedMotifSerializer, SavedDesignSerializer, StyleOptionsSerializer,
)
from main.views import create_notification

PREFERENCES = {"women", "men", "unisex"}


def _int_param(request, name):
    value = request.query_params.get(name, "").strip()
    if not value:
        return None
    if not value.isdigit():
        raise serializers.ValidationError({name: "Harus berupa angka."})
    return int(value)


# ---------------------------------------------------------------------------
# Katalog publik (read-only)
# ---------------------------------------------------------------------------
@api_view(["GET", "HEAD"])
@authentication_classes([])
@permission_classes([AllowAny])
def style_list(request):
    styles = StyleOptions.objects.filter(is_active=True).order_by("name", "id")
    gender = request.query_params.get("gender", "").strip().lower()
    if gender in PREFERENCES:
        styles = styles.filter(gender__iexact=gender)
    return Response(StyleOptionsSerializer(styles, many=True, context={"request": request}).data)


@api_view(["GET", "HEAD"])
@authentication_classes([])
@permission_classes([AllowAny])
def palette_list(request):
    palettes = ColorPalette.objects.filter(is_active=True).order_by("name")
    return Response(ColorPaletteSerializer(palettes, many=True, context={"request": request}).data)


def _motif_queryset():
    return (
        RecommendedMotif.objects.filter(is_active=True)
        .prefetch_related("styles", "palettes", "fashion_preference")
    )


@api_view(["GET", "HEAD"])
@authentication_classes([])
@permission_classes([AllowAny])
def motif_list(request):
    """Rekomendasi motif; filter style/palette/preference bersifat opsional."""
    motifs = _motif_queryset()
    style_id = _int_param(request, "style")
    palette_id = _int_param(request, "palette")
    preference = request.query_params.get("preference", "").strip().lower()

    if style_id is not None:
        motifs = motifs.filter(styles__id=style_id)
    if palette_id is not None:
        motifs = motifs.filter(palettes__id=palette_id)
    if preference in PREFERENCES:
        motifs = motifs.filter(fashion_preference__name__iexact=preference)

    motifs = motifs.distinct().order_by("name")
    return Response(RecommendedMotifSerializer(motifs, many=True, context={"request": request}).data)


@api_view(["GET", "HEAD"])
@authentication_classes([])
@permission_classes([AllowAny])
def motif_detail(request, motif_id):
    motif = get_object_or_404(_motif_queryset(), pk=motif_id)
    return Response(RecommendedMotifSerializer(motif, context={"request": request}).data)


@api_view(["GET", "HEAD"])
@authentication_classes([])
@permission_classes([AllowAny])
def product_option_list(request):
    options = ProductDesignOption.objects.filter(is_active=True)
    product_type = request.query_params.get("product_type", "").strip()
    if product_type:
        options = options.filter(product_type=product_type)
    return Response(ProductDesignOptionSerializer(options, many=True, context={"request": request}).data)


# ---------------------------------------------------------------------------
# Desain tersimpan (milik pengguna login)
# ---------------------------------------------------------------------------
def _own_designs(user):
    return SavedDesign.objects.filter(user=user).select_related("motif", "palette")


@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def design_list(request):
    if request.method in ("GET", "HEAD"):
        designs = _own_designs(request.user)
        query = request.query_params.get("q", "").strip()
        layout = request.query_params.get("layout", "").strip()
        if query:
            designs = designs.filter(
                Q(title__icontains=query)
                | Q(motif__name__icontains=query)
                | Q(palette__name__icontains=query)
            )
        if layout in {choice[0] for choice in SavedDesign.LAYOUT_CHOICES}:
            designs = designs.filter(layout=layout)
        serializer = SavedDesignSerializer(
            designs.order_by("-created_at"), many=True, context={"request": request},
        )
        return Response(serializer.data)

    serializer = SavedDesignSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.save(user=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def design_detail(request, design_id):
    # Queryset dibatasi ke pemilik: desain milik orang lain -> 404.
    design = get_object_or_404(_own_designs(request.user), pk=design_id)

    if request.method in ("GET", "HEAD"):
        return Response(SavedDesignSerializer(design, context={"request": request}).data)

    if request.method == "DELETE":
        design.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = SavedDesignSerializer(
        design, data=request.data, partial=request.method == "PATCH",
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


# ---------------------------------------------------------------------------
# Pesanan (milik pengguna login)
# ---------------------------------------------------------------------------
def _own_orders(user):
    return BatikOrder.objects.filter(user=user).select_related("motif", "palette", "design_option")


@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def order_list(request):
    if request.method in ("GET", "HEAD"):
        orders = _own_orders(request.user).order_by("-created_at")
        return Response(BatikOrderSerializer(orders, many=True, context={"request": request}).data)

    serializer = BatikOrderSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    order = serializer.save(user=request.user)
    create_notification(
        request.user,
        "Pesanan berhasil dibuat",
        f"Pesanan custom batik #{order.pk} berhasil dikirim pada "
        f"{order.created_at.strftime('%d %B %Y pukul %H:%M')}. "
        f"Status: {order.get_status_display()}.",
        notification_type="order_created",
        target_url=f"/batik_custom/order/{order.pk}/confirmation/",
    )
    return Response(
        BatikOrderSerializer(order, context={"request": request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "HEAD"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def order_detail(request, order_id):
    order = get_object_or_404(_own_orders(request.user), pk=order_id)
    return Response(BatikOrderSerializer(order, context={"request": request}).data)
