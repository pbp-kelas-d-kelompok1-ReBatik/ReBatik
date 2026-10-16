import uuid
from django.conf import settings
from django.db import models


class UpcyclingRequest(models.Model):
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
        ("LAINNYA", "Model lain"),
    ]

    DELIVERY_CHOICES = [
        ("DROP_OFF", "Drop-off"),
        ("KURIR", "Kurir"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Menunggu tinjauan"),
        ("PROCESSING", "Sedang dikerjakan"),
        ("COMPLETED", "Selesai"),
        ("CANCELLED", "Dibatalkan"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="upcycling_requests",
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False,)
    fabric = models.CharField(max_length=20, choices=FABRIC_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    product = models.CharField(max_length=20, choices=PRODUCT_CHOICES)
    quantity = models.PositiveSmallIntegerField(default=1)
    notes = models.TextField(blank=True)
    delivery_method = models.CharField(max_length=10, choices=DELIVERY_CHOICES)
    address = models.CharField(max_length=255)
    whatsapp = models.CharField(max_length=20)
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="PENDING",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_product_display()} — {self.user}"