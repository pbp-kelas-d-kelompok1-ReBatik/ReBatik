from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import UpcyclingRequest


class UpcyclingRequestAdminForm(forms.ModelForm):
    class Meta:
        model = UpcyclingRequest
        fields = "__all__"

    def clean_status(self):
        new_status = self.cleaned_data["status"]
        if self.instance._state.adding or new_status == self.instance.status:
            return new_status

        allowed_transitions = {
            UpcyclingRequest.Status.PENDING: {
                UpcyclingRequest.Status.PROCESSING,
                UpcyclingRequest.Status.CANCELLED,
            },
            UpcyclingRequest.Status.PROCESSING: {
                UpcyclingRequest.Status.COMPLETED,
                UpcyclingRequest.Status.CANCELLED,
            },
            UpcyclingRequest.Status.COMPLETED: set(),
            UpcyclingRequest.Status.CANCELLED: set(),
        }
        if new_status not in allowed_transitions.get(self.instance.status, set()):
            raise ValidationError("Perubahan status permintaan tersebut tidak diizinkan.")
        return new_status


@admin.register(UpcyclingRequest)
class UpcyclingRequestAdmin(admin.ModelAdmin):
    form = UpcyclingRequestAdminForm
    list_display = (
        "product",
        "custom_product",
        "fabric",
        "category",
        "quantity",
        "user",
        "status",
        "created_at",
    )
    list_filter = ("status", "fabric", "category", "delivery_method")
    search_fields = (
        "user__username",
        "user__email",
        "custom_product",
        "whatsapp",
        "address",
    )
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
