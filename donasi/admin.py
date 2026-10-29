
from django.contrib import admin
from django import forms
from django.db import transaction
from rewards.models import PointTransaction
from rewards.services import award_verified_donation

from .models import DonasiKain


class DonasiKainAdminForm(forms.ModelForm):
    class Meta:
        model = DonasiKain
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        if not cleaned:
            return cleaned

        if self.instance.pk:
            award = PointTransaction.objects.filter(
                donation_id=self.instance.pk,
                kind=PointTransaction.Kind.DONATION,
            ).first()
            if award:
                if cleaned.get("status") == DonasiKain.Status.MENUNGGU:
                    self.add_error(
                        "status",
                        "Donasi yang sudah menghasilkan poin tidak dapat dikembalikan ke status menunggu.",
                    )
                if cleaned.get("user") and cleaned["user"].pk != award.user_id:
                    self.add_error("user", "Pemilik donasi yang sudah diberi poin tidak dapat diganti.")
                if cleaned.get("verified_weight_kg") != award.weight_kg:
                    self.add_error("verified_weight_kg", "Berat donasi yang sudah diberi poin tidak dapat diubah.")

        if (
            self.instance.pk
            and cleaned.get("status") == DonasiKain.Status.DIKONFIRMASI
            and cleaned.get("user")
            and not cleaned.get("verified_weight_kg")
        ):
            self.add_error("verified_weight_kg", "Masukkan berat hasil verifikasi untuk pemberian poin.")
        return cleaned


@admin.register(DonasiKain)
class DonasiKainAdmin(admin.ModelAdmin):
    form = DonasiKainAdminForm
    list_display = (
        "item_name",
        "donor_name",
        "donation_type",
        "quantity",
        "condition",
        "status",
        "verified_weight_kg",
        "created_at",
    )

    list_filter = (
        "donation_type",
        "condition",
        "status",
        "created_at",
    )

    search_fields = (
        "item_name",
        "donor_name",
        "city",
    )

    readonly_fields = ("created_at",)

    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            old_status = DonasiKain.objects.values_list("status", flat=True).get(pk=obj.pk)

        with transaction.atomic():
            super().save_model(request, obj, form, change)
            if (
                old_status != DonasiKain.Status.DIKONFIRMASI
                and obj.status == DonasiKain.Status.DIKONFIRMASI
                and obj.user_id
                and obj.verified_weight_kg
            ):
                award_verified_donation(
                    obj.user,
                    donation_reference=str(obj.pk),
                    donation=obj,
                    weight_kg=obj.verified_weight_kg,
                )
