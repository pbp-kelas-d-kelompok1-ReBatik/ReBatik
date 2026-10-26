from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import router, transaction

from rewards.services import award_upcycling_completion

from .models import UpcyclingRequest, UpcyclingStatusHistory


class UpcyclingRequestAdminForm(forms.ModelForm):
    class Meta:
        model = UpcyclingRequest
        fields = "__all__"

    def clean_status(self):
        """Validate that the requested status follows the workflow transitions."""
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


class UpcyclingStatusHistoryInline(admin.TabularInline):
    model = UpcyclingStatusHistory
    fields = ("from_status", "to_status", "changed_by", "changed_at")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        """Keep status history entries read-only in the admin interface."""
        return False


@admin.register(UpcyclingRequest)
class UpcyclingRequestAdmin(admin.ModelAdmin):
    form = UpcyclingRequestAdminForm
    inlines = (UpcyclingStatusHistoryInline,)
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

    def changeform_view(
        self,
        request,
        object_id=None,
        form_url="",
        extra_context=None,
    ):
        """Lock an edited request while its status and history are saved."""
        if request.method != "POST" or object_id is None:
            return super().changeform_view(
                request,
                object_id,
                form_url,
                extra_context,
            )

        using = router.db_for_write(self.model)
        with transaction.atomic(using=using):
            existing_request = self.get_object(request, object_id)
            if existing_request is not None:
                try:
                    self.get_queryset(request).using(using).select_for_update().get(
                        pk=existing_request.pk
                    )
                except self.model.DoesNotExist:
                    # The regular admin flow will return 404 if a concurrent
                    # delete removed the request before the lock was acquired.
                    pass
            return super().changeform_view(
                request,
                object_id,
                form_url,
                extra_context,
            )

    def save_model(self, request, obj, form, change):
        """Record the authenticated admin when a request status changes."""
        previous_status = None
        if change:
            previous_status = UpcyclingRequest.objects.values_list(
                "status",
                flat=True,
            ).get(pk=obj.pk)

        super().save_model(request, obj, form, change)

        if previous_status != obj.status:
            UpcyclingStatusHistory.objects.create(
                request=obj,
                from_status=previous_status or "",
                to_status=obj.status,
                changed_by=request.user,
            )
            if obj.status == UpcyclingRequest.Status.COMPLETED:
                award_upcycling_completion(
                    obj.user,
                    request_reference=str(obj.pk),
                )
