import uuid
from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

NOTES_MAX_LENGTH = 2000


def fabric_handoff_deadline(approved_at):
    """Use a group-configurable handoff window, defaulting to seven days."""
    return approved_at + timedelta(
        days=getattr(settings, "UPCYCLING_FABRIC_DEADLINE_DAYS", 7)
    )


class ProductType(models.Model):
    """Products artisans can make from user-owned fabric."""

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class ArtisanProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="artisan_profile",
    )
    specializations = models.ManyToManyField(
        ProductType,
        blank=True,
        related_name="artisans",
    )
    is_available = models.BooleanField(default=True)
    max_active_requests = models.PositiveSmallIntegerField(default=3)

    def active_request_count(self):
        return self.upcycling_requests.exclude(
            status__in=UpcyclingRequest.TERMINAL_STATUSES
        ).count()

    def has_capacity(self):
        return self.active_request_count() < self.max_active_requests

    def __str__(self):
        return f"Artisan: {self.user}"


class UpcyclingRequest(models.Model):
    class Status(models.TextChoices):
        PENDING_ASSIGNMENT = "PENDING_ASSIGNMENT", "Menunggu penugasan artisan"
        PENDING_REVIEW = "PENDING_REVIEW", "Menunggu review artisan"
        AWAITING_FABRIC = "AWAITING_FABRIC", "Menunggu kain diserahkan"
        INSPECTION = "INSPECTION", "Pemeriksaan kain"
        AWAITING_APPROVAL = "AWAITING_APPROVAL", "Menunggu persetujuan harga"
        IN_PROGRESS = "IN_PROGRESS", "Sedang diproduksi"
        READY = "READY", "Siap diserahkan"
        COMPLETED = "COMPLETED", "Selesai"
        REJECTED = "REJECTED", "Ditolak"
        CANCELLED = "CANCELLED", "Dibatalkan"
        EXPIRED = "EXPIRED", "Kedaluwarsa"

    class ReturnStatus(models.TextChoices):
        NOT_REQUIRED = "NOT_REQUIRED", "Tidak perlu dikembalikan"
        PENDING_RETURN = "PENDING_RETURN", "Menunggu pengembalian kain"
        RETURNED = "RETURNED", "Kain sudah dikembalikan"

    class FabricType(models.TextChoices):
        DENIM = "DENIM", "Denim"
        COTTON = "COTTON", "Katun"
        BATIK = "BATIK", "Batik"
        MIXED = "MIXED", "Campuran"
        OTHER = "OTHER", "Lainnya"

    class FabricCondition(models.TextChoices):
        GOOD = "GOOD", "Baik"
        FAIR = "FAIR", "Cukup"
        LIGHT_DAMAGE = "LIGHT_DAMAGE", "Rusak ringan"

    class DeliveryMethod(models.TextChoices):
        DROP_OFF = "DROP_OFF", "Ambil di lokasi drop-off"
        COURIER = "KURIR", "Dikirim kurir"

    class FabricDeliveryMethod(models.TextChoices):
        DROP_OFF = "DROP_OFF", "Drop-off kain"
        SELF_SHIP = "SELF_SHIP", "Kirim kain sendiri"

    TERMINAL_STATUSES = (
        Status.COMPLETED,
        Status.REJECTED,
        Status.CANCELLED,
        Status.EXPIRED,
    )

    FABRIC_CHOICES = FabricType.choices
    CATEGORY_CHOICES = [
        ("TAS", "Tas"),
        ("POUCH", "Pouch"),
        ("PAKAIAN", "Pakaian"),
        ("AKSESORIS", "Aksesori"),
        ("RUMAH_TANGGA", "Perlengkapan Rumah"),
        ("LAINNYA", "Lainnya"),
    ]
    PRODUCT_CHOICES = [
        ("TOTE_BAG", "Tote Bag"),
        ("SLING_BAG", "Sling Bag"),
        ("BACKPACK", "Backpack"),
        ("SHOULDER_BAG", "Shoulder Bag"),
        ("POUCH", "Pouch"),
        ("PENCIL_CASE", "Tempat Pensil"),
        ("MAKEUP_POUCH", "Pouch Kosmetik"),
        ("KEMEJA", "Kemeja"),
        ("OUTER", "Outer"),
        ("ROK", "Rok"),
        ("AKSESORIS", "Aksesori"),
        ("SCRUNCHIE", "Scrunchie"),
        ("BUCKET_HAT", "Bucket Hat"),
        ("HEADBAND", "Headband"),
        ("KEYCHAIN", "Gantungan Kunci Kain"),
        ("LAPTOP_SLEEVE", "Sleeve Laptop"),
        ("SARUNG_BANTAL", "Sarung Bantal"),
        ("LAINNYA", "Lainnya"),
    ]
    DELIVERY_CHOICES = DeliveryMethod.choices
    FABRIC_DELIVERY_CHOICES = FabricDeliveryMethod.choices
    STATUS_CHOICES = Status.choices

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="upcycling_requests",
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    artisan = models.ForeignKey(
        ArtisanProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="upcycling_requests",
    )
    fabric = models.CharField(max_length=20, choices=FABRIC_CHOICES)
    fabric_other_description = models.CharField(max_length=100, blank=True)
    fabric_photo = models.ImageField(upload_to="upcycling/fabric/", blank=True, null=True)
    fabric_condition = models.CharField(
        max_length=20,
        choices=FabricCondition.choices,
        blank=True,
    )
    fabric_dimensions = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    product = models.CharField(max_length=20, choices=PRODUCT_CHOICES)
    custom_product = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )
    notes = models.TextField(max_length=NOTES_MAX_LENGTH, blank=True)
    fabric_delivery_method = models.CharField(
        max_length=20,
        choices=FabricDeliveryMethod.choices,
        default=FabricDeliveryMethod.DROP_OFF,
    )
    fabric_delivery_location = models.CharField(max_length=255, blank=True)
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_CHOICES)
    address = models.CharField(max_length=255)
    whatsapp = models.CharField(max_length=20)
    status = models.CharField(
        max_length=24,
        choices=STATUS_CHOICES,
        default=Status.PENDING_ASSIGNMENT,
    )
    review_notes = models.TextField(blank=True)
    review_approved_at = models.DateTimeField(null=True, blank=True)
    fabric_deadline = models.DateTimeField(null=True, blank=True)
    fabric_received_at = models.DateTimeField(null=True, blank=True)
    fabric_received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fabric_receipts_confirmed",
    )
    fabric_receipt_notes = models.TextField(blank=True)
    inspection_notes = models.TextField(blank=True)
    quoted_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    quotation_notes = models.TextField(blank=True)
    quoted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_stage = models.CharField(max_length=30, blank=True)
    rejection_reason = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)
    return_status = models.CharField(
        max_length=20,
        choices=ReturnStatus.choices,
        default=ReturnStatus.NOT_REQUIRED,
    )
    return_method = models.CharField(max_length=20, blank=True)
    return_cost_bearer = models.CharField(max_length=20, blank=True)
    return_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fabric_returns_confirmed",
    )
    return_confirmed_at = models.DateTimeField(null=True, blank=True)
    return_notes = models.TextField(blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="upcycling_completions_confirmed",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_notes = models.TextField(blank=True)
    delivery_proof = models.FileField(upload_to="upcycling/delivery/", blank=True, null=True)
    delivery_proof_received_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status", "-created_at"], name="upreq_user_status_created_idx"),
            models.Index(fields=["artisan", "status"], name="upreq_artisan_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(quoted_price__isnull=True) | Q(quoted_price__gte=0),
                name="upreq_quote_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.get_product_name()} — {self.user}"

    def get_product_name(self):
        if self.product == "LAINNYA" and self.custom_product:
            return self.custom_product
        return self.get_product_display()

    @property
    def reference_code(self):
        return f"RB-{self.pk.hex[:8].upper()}"


class UpcyclingStatusHistory(models.Model):
    request = models.ForeignKey(
        UpcyclingRequest,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(max_length=24, choices=UpcyclingRequest.STATUS_CHOICES, blank=True)
    to_status = models.CharField(max_length=24, choices=UpcyclingRequest.STATUS_CHOICES)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="upcycling_status_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at", "pk"]
        verbose_name = "riwayat status permintaan upcycling"
        verbose_name_plural = "riwayat status permintaan upcycling"

    def __str__(self):
        return f"{self.request.reference_code}: {self.get_to_status_display()}"


class UpcyclingRateLimitBucket(models.Model):
    class Action(models.TextChoices):
        CREATE = "CREATE", "Buat permintaan"
        UPDATE = "UPDATE", "Edit permintaan"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="upcycling_rate_limit_buckets",
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    window_started_at = models.DateTimeField()
    request_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "action"], name="upcycling_rate_limit_user_action_uniq"),
        ]

    def __str__(self):
        return f"{self.user_id}: {self.get_action_display()} ({self.request_count})"
