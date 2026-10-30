from datetime import timedelta

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import router, transaction
from django.utils import timezone

from rewards.services import award_upcycling_completion

from .models import (
    AdditionalFabricPhoto,
    ArtisanProfile,
    ProductType,
    UpcyclingRequest,
    UpcyclingStatusHistory,
    fabric_handoff_deadline,
)
from .services import eligible_artisans_for_request


class ArtisanProfileAdminForm(forms.ModelForm):
    class Meta:
        model = ArtisanProfile
        fields = "__all__"


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(ArtisanProfile)
class ArtisanProfileAdmin(admin.ModelAdmin):
    form = ArtisanProfileAdminForm
    list_display = ("user", "is_available", "max_active_requests", "active_requests")
    list_filter = ("is_available", "specializations")
    filter_horizontal = ("specializations",)
    search_fields = ("user__username", "user__email")

    @admin.display(description="Permintaan aktif")
    def active_requests(self, obj):
        return obj.active_request_count()


class UpcyclingRequestAdminForm(forms.ModelForm):
    class Meta:
        model = UpcyclingRequest
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        """Limit artisan choices to eligible profiles and the current assignee."""
        super().__init__(*args, **kwargs)
        artisan_field = self.fields.get("artisan")
        if not artisan_field:
            return
        if self.instance.pk:
            eligible_ids = [
                profile.pk for profile in eligible_artisans_for_request(self.instance)
            ]
            if self.instance.artisan_id:
                eligible_ids.append(self.instance.artisan_id)
            eligible = ArtisanProfile.objects.filter(pk__in=eligible_ids)
        else:
            eligible = ArtisanProfile.objects.none()
        artisan_field.queryset = eligible
        artisan_field.label_from_instance = lambda artisan: (
            f"{artisan.user} · tersedia · {artisan.active_request_count()}/{artisan.max_active_requests} request aktif"
        )

    def clean(self):
        """Validate assignment and workflow requirements for the selected status."""
        cleaned = super().clean()
        if not cleaned:
            return cleaned
        request_obj = self.instance
        artisan = cleaned.get("artisan")
        status = cleaned.get("status")
        old_artisan_id = request_obj.artisan_id if request_obj.pk else None
        old_status = request_obj.status if request_obj.pk else None

        if artisan and artisan.pk != old_artisan_id:
            if artisan.user_id == request_obj.user_id:
                self.add_error("artisan", "Artisan tidak dapat menangani permintaannya sendiri.")
            elif old_status not in {
                None,
                UpcyclingRequest.Status.PENDING_ASSIGNMENT,
                UpcyclingRequest.Status.PENDING_REVIEW,
                UpcyclingRequest.Status.AWAITING_FABRIC,
            }:
                self.add_error("artisan", "Artisan hanya dapat diganti sebelum kain diterima.")
            else:
                artisan = ArtisanProfile.objects.select_for_update().get(pk=artisan.pk)
                if not artisan.is_available:
                    self.add_error("artisan", "Artisan sedang tidak tersedia.")
                elif artisan.active_request_count() >= artisan.max_active_requests:
                    self.add_error("artisan", "Kapasitas artisan sudah penuh.")
                else:
                    product_code = cleaned.get("product")
                    if not artisan.specializations.filter(code=product_code).exists():
                        self.add_error("artisan", "Keahlian artisan tidak cocok dengan produk ini.")
                    else:
                        cleaned["status"] = UpcyclingRequest.Status.PENDING_REVIEW

        if status != UpcyclingRequest.Status.PENDING_ASSIGNMENT and not artisan:
            self.add_error("artisan", "Request harus memiliki artisan setelah penugasan.")
        if status == UpcyclingRequest.Status.INSPECTION and not (
            cleaned.get("fabric_received_at") and cleaned.get("fabric_received_by")
        ):
            self.add_error(None, "Konfirmasi penerimaan kain diperlukan sebelum inspeksi.")
        if bool(cleaned.get("fabric_received_at")) != bool(cleaned.get("fabric_received_by")):
            self.add_error(None, "Waktu dan aktor penerimaan kain harus dicatat bersama.")
        if status == UpcyclingRequest.Status.AWAITING_APPROVAL and cleaned.get("quoted_price") is None:
            self.add_error("quoted_price", "Harga final perlu diisi sebelum meminta persetujuan user.")
        if status == UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS and (
            not cleaned.get("approved_at") or cleaned.get("quoted_price") is None
        ):
            self.add_error(None, "Persetujuan harga wajib dicatat sebelum meminta detail penerimaan produk.")
        if status == UpcyclingRequest.Status.IN_PROGRESS:
            if not cleaned.get("approved_at"):
                self.add_error(None, "User harus menyetujui penawaran sebelum produksi.")
            if not cleaned.get("delivery_method") or not cleaned.get("address"):
                self.add_error(None, "Metode dan alamat penerimaan produk wajib sebelum produksi.")
        if status == UpcyclingRequest.Status.EXPIRED:
            deadline = cleaned.get("fabric_deadline")
            if cleaned.get("fabric_received_at") or not deadline or deadline > timezone.now():
                self.add_error(None, "Request hanya dapat kedaluwarsa setelah tenggat lewat dan kain belum diterima.")
        if status == UpcyclingRequest.Status.REJECTED and not cleaned.get("rejection_reason"):
            self.add_error("rejection_reason", "Alasan penolakan wajib dicatat.")
        if status == UpcyclingRequest.Status.CANCELLED and not cleaned.get("cancellation_reason"):
            self.add_error("cancellation_reason", "Alasan pembatalan wajib dicatat.")
        if cleaned.get("return_status") == UpcyclingRequest.ReturnStatus.RETURNED:
            if not cleaned.get("fabric_received_at"):
                self.add_error("return_status", "Tidak ada kain yang perlu ditandai telah dikembalikan.")
        if status == UpcyclingRequest.Status.COMPLETED and request_obj.pk and request_obj.status == UpcyclingRequest.Status.READY:
            proof_received_at = cleaned.get("delivery_proof_received_at")
            if not cleaned.get("delivery_proof"):
                self.add_error("delivery_proof", "Bukti penyerahan wajib untuk konfirmasi manual admin.")
            if not cleaned.get("completion_notes"):
                self.add_error("completion_notes", "Catatan konfirmasi manual wajib diisi.")
            if not proof_received_at or proof_received_at + timedelta(days=3) > timezone.now():
                self.add_error(None, "Konfirmasi manual baru boleh dilakukan 3 hari setelah bukti penyerahan dicatat.")
        return cleaned

    def clean_status(self):
        """Reject status transitions outside the admin workflow."""
        new_status = self.cleaned_data["status"]
        if self.instance._state.adding or new_status == self.instance.status:
            return new_status
        allowed = {
            UpcyclingRequest.Status.PENDING_ASSIGNMENT: {UpcyclingRequest.Status.PENDING_REVIEW, UpcyclingRequest.Status.CANCELLED},
            UpcyclingRequest.Status.PENDING_REVIEW: {UpcyclingRequest.Status.AWAITING_FABRIC, UpcyclingRequest.Status.REJECTED, UpcyclingRequest.Status.CANCELLED},
            UpcyclingRequest.Status.AWAITING_FABRIC: {UpcyclingRequest.Status.PENDING_REVIEW, UpcyclingRequest.Status.INSPECTION, UpcyclingRequest.Status.EXPIRED, UpcyclingRequest.Status.CANCELLED},
            UpcyclingRequest.Status.INSPECTION: {UpcyclingRequest.Status.AWAITING_APPROVAL, UpcyclingRequest.Status.REJECTED, UpcyclingRequest.Status.CANCELLED},
            UpcyclingRequest.Status.AWAITING_APPROVAL: {UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS, UpcyclingRequest.Status.CANCELLED},
            UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS: {UpcyclingRequest.Status.IN_PROGRESS, UpcyclingRequest.Status.CANCELLED},
            UpcyclingRequest.Status.IN_PROGRESS: {UpcyclingRequest.Status.READY, UpcyclingRequest.Status.CANCELLED},
            UpcyclingRequest.Status.READY: {UpcyclingRequest.Status.COMPLETED},
            UpcyclingRequest.Status.COMPLETED: set(),
            UpcyclingRequest.Status.REJECTED: set(),
            UpcyclingRequest.Status.CANCELLED: set(),
            UpcyclingRequest.Status.EXPIRED: set(),
        }
        if new_status not in allowed.get(self.instance.status, set()):
            raise ValidationError("Perubahan status permintaan tersebut tidak diizinkan.")
        return new_status


class UpcyclingStatusHistoryInline(admin.TabularInline):
    model = UpcyclingStatusHistory
    fields = ("from_status", "to_status", "changed_by", "changed_at")
    readonly_fields = fields
    extra = 0
    can_delete = False


class AdditionalFabricPhotoInline(admin.TabularInline):
    model = AdditionalFabricPhoto
    extra = 0
    max_num = 2

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(UpcyclingRequest)
class UpcyclingRequestAdmin(admin.ModelAdmin):
    form = UpcyclingRequestAdminForm
    inlines = (AdditionalFabricPhotoInline, UpcyclingStatusHistoryInline)
    list_display = ("reference_code", "product", "user", "artisan", "status", "return_status", "created_at")
    list_filter = ("status", "return_status", "fabric", "category", "delivery_method")
    search_fields = ("user__username", "user__email", "custom_product", "whatsapp", "address")
    readonly_fields = ("created_at", "updated_at", "review_approved_at", "fabric_deadline", "quoted_at", "approved_at", "return_confirmed_by", "return_confirmed_at", "ready_at", "delivery_proof_received_at", "completed_at")
    date_hierarchy = "created_at"
    fieldsets = (
        ("Request", {"fields": ("user", "artisan", "fabric", "fabric_other_description", "fabric_photo", "fabric_composition", "fabric_condition", "fabric_dimensions", "category", "product", "custom_product", "wants_batik_accent", "batik_motif", "motif_placement", "design_notes", "quantity", "notes", "status")} ),
        ("Penyerahan dan inspeksi kain", {"fields": ("fabric_delivery_method", "fabric_delivery_location", "review_notes", "review_approved_at", "fabric_deadline", "fabric_received_at", "fabric_received_by", "fabric_receipt_notes", "inspection_notes", "rejection_stage", "rejection_reason")} ),
        ("Penawaran harga", {"fields": ("quoted_price", "quotation_notes", "quoted_at", "approved_at")} ),
        ("Pengembalian kain", {"fields": ("return_status", "return_method", "return_cost_bearer", "return_confirmed_by", "return_confirmed_at", "return_notes", "cancellation_reason")} ),
        ("Penyerahan produk", {"fields": ("delivery_method", "address", "whatsapp", "ready_at", "delivery_proof", "delivery_proof_received_at", "completed_by", "completed_at", "completion_notes")} ),
        ("Waktu", {"fields": ("created_at", "updated_at")} ),
    )

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        """Lock an existing request while processing an admin POST."""
        if request.method != "POST":
            return super().changeform_view(request, object_id, form_url, extra_context)
        using = router.db_for_write(self.model)
        with transaction.atomic(using=using):
            if object_id is not None:
                existing = self.get_object(request, object_id)
                if existing is not None:
                    self.get_queryset(request).using(using).select_for_update().filter(pk=existing.pk).first()
            return super().changeform_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        """Save workflow timestamps and record status changes and completion points."""
        old = None
        if change:
            old = UpcyclingRequest.objects.get(pk=obj.pk)
        now = timezone.now()
        if obj.delivery_proof and (old is None or not old.delivery_proof):
            obj.delivery_proof_received_at = now
        if old and obj.artisan_id != old.artisan_id and old.status == UpcyclingRequest.Status.AWAITING_FABRIC:
            obj.status = UpcyclingRequest.Status.PENDING_REVIEW
            obj.review_approved_at = None
            obj.fabric_deadline = None
        if obj.status == UpcyclingRequest.Status.AWAITING_FABRIC and not obj.review_approved_at:
            obj.review_approved_at = now
            obj.fabric_deadline = fabric_handoff_deadline(now)
        if obj.status == UpcyclingRequest.Status.AWAITING_APPROVAL and not obj.quoted_at:
            obj.quoted_at = now
        if obj.status == UpcyclingRequest.Status.READY and not obj.ready_at:
            obj.ready_at = now
        if (
            obj.status in (UpcyclingRequest.Status.REJECTED, UpcyclingRequest.Status.CANCELLED)
            and obj.fabric_received_at
            and (old is None or old.status != obj.status)
        ):
            obj.return_status = UpcyclingRequest.ReturnStatus.PENDING_RETURN
        if (
            obj.return_status == UpcyclingRequest.ReturnStatus.RETURNED
            and (old is None or old.return_status != UpcyclingRequest.ReturnStatus.RETURNED)
        ):
            obj.return_confirmed_by = request.user
            obj.return_confirmed_at = obj.return_confirmed_at or now

        super().save_model(request, obj, form, change)
        if old is None or old.status != obj.status:
            UpcyclingStatusHistory.objects.create(
                request=obj,
                from_status=old.status if old else "",
                to_status=obj.status,
                changed_by=request.user,
            )
            if obj.status == UpcyclingRequest.Status.COMPLETED:
                obj.completed_by = request.user
                obj.completed_at = obj.completed_at or now
                obj.save(update_fields=("completed_by", "completed_at"))
                award_upcycling_completion(
                    obj.user,
                    request_reference=str(obj.pk),
                    upcycling_request=obj,
                )
