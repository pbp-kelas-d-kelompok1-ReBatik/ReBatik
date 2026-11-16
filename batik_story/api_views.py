from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from batik_story.models import BatikMotif
from batik_story.permissions import IsStaffOrReadOnly
from batik_story.serializers import BatikMotifSerializer


def _motifs():
    return BatikMotif.objects.prefetch_related("favorited_by")


@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsStaffOrReadOnly])
def motif_list(request):
    if request.method in ("GET", "HEAD"):
        motifs = _motifs()
        query = request.query_params.get("q", "").strip()
        asal = request.query_params.get("asal", "").strip()
        sort = request.query_params.get("sort", "nama_asc").strip()

        if query:
            motifs = motifs.filter(
                Q(nama__icontains=query)
                | Q(asal__icontains=query)
                | Q(filosofi__icontains=query)
                | Q(deskripsi__icontains=query)
            )
        if asal in {choice[0] for choice in BatikMotif.ASAL_CHOICES}:
            motifs = motifs.filter(asal=asal)
        if sort == "nama_desc":
            motifs = motifs.order_by("-nama", "id_story")
        else:
            motifs = motifs.order_by("nama", "id_story")

        serializer = BatikMotifSerializer(
            motifs, many=True, context={"request": request},
        )
        return Response(serializer.data)

    serializer = BatikMotifSerializer(
        data=request.data, context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsStaffOrReadOnly])
def motif_detail(request, motif_id):
    motif = get_object_or_404(_motifs(), id_story=motif_id)

    if request.method in ("GET", "HEAD"):
        serializer = BatikMotifSerializer(motif, context={"request": request})
        return Response(serializer.data)

    if request.method == "DELETE":
        motif.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = BatikMotifSerializer(
        motif, data=request.data, partial=request.method == "PATCH",
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def motif_favorite(request, motif_id):
    motif = get_object_or_404(BatikMotif, id_story=motif_id)
    if motif.favorited_by.filter(pk=request.user.pk).exists():
        motif.favorited_by.remove(request.user)
    else:
        motif.favorited_by.add(request.user)
    serializer = BatikMotifSerializer(motif, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def origin_list(request):
    """Daftar asal daerah untuk dropdown filter di aplikasi mobile."""
    return Response([
        {"value": value, "label": label}
        for value, label in BatikMotif.ASAL_CHOICES
    ])
