from django.core.exceptions import ValidationError
from django.db import transaction

from .models import ArtisanProfile, UpcyclingRequest, UpcyclingStatusHistory


def eligible_artisans_for_request(upcycling_request):
    """Return eligible artisan profiles with matching skills and spare capacity."""
    candidates = (
        ArtisanProfile.objects.filter(
            is_available=True,
            user__groups__name="Artisan",
            specializations__code=upcycling_request.product,
        )
        .exclude(user_id=upcycling_request.user_id)
        .select_related("user")
        .distinct()
    )
    return [
        artisan
        for artisan in candidates
        if artisan.active_request_count() < artisan.max_active_requests
    ]


@transaction.atomic
def assign_artisan_to_request(request_id, artisan_id, *, assigned_by):
    """Assign an eligible artisan to an unassigned request and record history.

    artisan_id identifies an ArtisanProfile; assigned_by is the user recorded
    in the history. Return the updated request. Raise ValidationError when the
    request or artisan is missing or the assignment is not eligible.
    """
    upcycling_request = (
        UpcyclingRequest.objects.select_for_update()
        .filter(pk=request_id)
        .first()
    )
    if upcycling_request is None:
        raise ValidationError("Request tidak ditemukan.")
    if (
        upcycling_request.status != UpcyclingRequest.Status.PENDING_ASSIGNMENT
        or upcycling_request.artisan_id is not None
    ):
        raise ValidationError("Request ini sudah tidak menunggu penugasan.")

    artisan = (
        ArtisanProfile.objects.select_for_update()
        .select_related("user")
        .filter(pk=artisan_id)
        .first()
    )
    if artisan is None:
        raise ValidationError("Artisan tidak ditemukan.")
    if artisan.user_id == upcycling_request.user_id:
        raise ValidationError("Artisan tidak dapat menangani permintaannya sendiri.")
    if not artisan.user.groups.filter(name="Artisan").exists():
        raise ValidationError("Akun ini belum memiliki peran Artisan.")
    if not artisan.is_available:
        raise ValidationError("Artisan sedang tidak tersedia.")
    if not artisan.specializations.filter(code=upcycling_request.product).exists():
        raise ValidationError("Keahlian artisan tidak cocok dengan produk ini.")
    if artisan.active_request_count() >= artisan.max_active_requests:
        raise ValidationError("Kapasitas artisan sudah penuh.")

    old_status = upcycling_request.status
    upcycling_request.artisan = artisan
    upcycling_request.status = UpcyclingRequest.Status.PENDING_REVIEW
    upcycling_request.save(update_fields=("artisan", "status", "updated_at"))
    UpcyclingStatusHistory.objects.create(
        request=upcycling_request,
        from_status=old_status,
        to_status=upcycling_request.status,
        changed_by=assigned_by,
    )
    return upcycling_request
