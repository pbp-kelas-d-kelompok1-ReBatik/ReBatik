import uuid
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

NOTES_MAX_LENGTH = 2000


class UpcyclingRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Menunggu Tinjauan"
        PROCESSING = "PROCESSING", "Diproses"
        COMPLETED = "COMPLETED", "Selesai"
        CANCELLED = "CANCELLED", "Dibatalkan"

    FABRIC_CHOICES = [
        ("PARANG", "Kain Motif Parang"),
        ("KAWUNG", "Kain Motif Kawung"),
        ("MEGA_MENDUNG", "Kain Motif Mega Mendung"),
        ("NEW_DONATION", "Donasikan Kain Baru"),
    ]

    CATEGORY_CHOICES = [
        ("TAS", "Tas"),
        ("POUCH", "Pouch"),
        ("PAKAIAN", "Pakaian"),
        ("AKSESORIS", "Aksesoris"),
        ("LAINNYA", "Lainnya"),
    ]

    PRODUCT_CHOICES = [
        ("TOTE_BAG", "Tote Bag"),
        ("SLING_BAG", "Sling Bag"),
        ("POUCH", "Pouch"),
        ("KEMEJA", "Kemeja"),
        ("AKSESORIS", "Aksesoris"),
        ("LAINNYA", "Lainnya"),
    ]

    DELIVERY_CHOICES = [
        ("DROP_OFF", "Ambil di Drop-off"),
        ("KURIR", "Dikirim Kurir"),
    ]

    STATUS_CHOICES = Status.choices

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="upcycling_requests",
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False,)
    fabric = models.CharField(max_length=20, choices=FABRIC_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    product = models.CharField(max_length=20, choices=PRODUCT_CHOICES)
    custom_product = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )
    notes = models.TextField(max_length=NOTES_MAX_LENGTH, blank=True)
    delivery_method = models.CharField(max_length=10, choices=DELIVERY_CHOICES)
    address = models.CharField(max_length=255)
    whatsapp = models.CharField(max_length=20)
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "status", "-created_at"],
                name="upreq_user_status_created_idx",
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
        short_id = self.pk.hex[:8].upper()
        return f"RB-{short_id}"


class UpcyclingStatusHistory(models.Model):
    request = models.ForeignKey(
        UpcyclingRequest,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(
        max_length=12,
        choices=UpcyclingRequest.STATUS_CHOICES,
        blank=True,
    )
    to_status = models.CharField(
        max_length=12,
        choices=UpcyclingRequest.STATUS_CHOICES,
    )
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
