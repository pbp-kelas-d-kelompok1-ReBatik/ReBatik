import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

DESCRIPTION_MAX_LENGTH = 2000
NOTES_MAX_LENGTH = 2000
MAX_ORDER_QUANTITY = 10


class ProductQuerySet(models.QuerySet):
    def available(self):
        """Return only active (non-soft-deleted) catalogue products."""
        return self.filter(is_deleted=False)


class Product(models.Model):
    class Category(models.TextChoices):
        TAS = "TAS", "Tas"
        POUCH = "POUCH", "Pouch"
        PAKAIAN = "PAKAIAN", "Pakaian"
        AKSESORIS = "AKSESORIS", "Aksesoris"

    CATEGORY_CHOICES = Category.choices

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="marketplace_products",
    )
    name = models.CharField(max_length=255)
    motif = models.CharField(max_length=150)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=Category.TAS,
    )
    description = models.TextField(
        max_length=DESCRIPTION_MAX_LENGTH,
        blank=True,
    )
    badge_status = models.CharField(max_length=50, blank=True, null=True)
    material_source = models.CharField(max_length=255)
    artisan_origin = models.CharField(max_length=150)
    price = models.PositiveIntegerField()
    stock = models.PositiveIntegerField(default=1)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(
                fields=["is_deleted", "category", "-created_at"],
                name="mp_prod_del_cat_created_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gt=0),
                name="mp_product_price_positive",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def is_in_stock(self):
        """Return True when the product is visible and has available stock."""
        return not self.is_deleted and self.stock > 0


class DropOffPoint(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)
    operating_hours = models.CharField(max_length=100, default="09:00 - 17:00 WIB")
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    class Meta:
        ordering = ["city", "name"]

    def __str__(self):
        return f"{self.name} - {self.city}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Menunggu Konfirmasi"
        PROCESSING = "PROCESSING", "Diproses"
        READY = "READY", "Dikirim / Siap Diambil"
        COMPLETED = "COMPLETED", "Selesai"
        CANCELLED = "CANCELLED", "Dibatalkan"

    class DeliveryMethod(models.TextChoices):
        DROP_OFF = "DROP_OFF", "Ambil di Drop-off Point"
        KURIR = "KURIR", "Dikirim Kurir"

    STATUS_CHOICES = Status.choices
    DELIVERY_CHOICES = DeliveryMethod.choices

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="marketplace_orders",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    product_name = models.CharField(max_length=255)
    unit_price = models.PositiveIntegerField()
    quantity = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_ORDER_QUANTITY)],
    )
    total_price = models.PositiveIntegerField()
    delivery_method = models.CharField(
        max_length=10,
        choices=DELIVERY_CHOICES,
    )
    dropoff_point = models.ForeignKey(
        DropOffPoint,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    address = models.CharField(max_length=255, blank=True)
    whatsapp = models.CharField(max_length=20)
    notes = models.TextField(max_length=NOTES_MAX_LENGTH, blank=True)
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(
                fields=["user", "status", "-created_at"],
                name="mp_order_user_status_created",
            ),
        ]

    def __str__(self):
        return f"{self.reference_code} — {self.product_name} ({self.user})"

    @property
    def reference_code(self):
        """Return a short, stable public reference derived from the UUID."""
        short_id = self.pk.hex[:8].upper()
        return f"MP-{short_id}"


ALLOWED_ORDER_STATUS_TRANSITIONS = {
    Order.Status.PENDING: {
        Order.Status.PROCESSING,
        Order.Status.CANCELLED,
    },
    Order.Status.PROCESSING: {
        Order.Status.READY,
        Order.Status.CANCELLED,
    },
    Order.Status.READY: {
        Order.Status.COMPLETED,
    },
    Order.Status.COMPLETED: set(),
    Order.Status.CANCELLED: set(),
}


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(
        max_length=12,
        choices=Order.STATUS_CHOICES,
        blank=True,
    )
    to_status = models.CharField(
        max_length=12,
        choices=Order.STATUS_CHOICES,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketplace_order_status_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at", "pk"]
        verbose_name = "riwayat status pesanan marketplace"
        verbose_name_plural = "riwayat status pesanan marketplace"

    def __str__(self):
        return f"{self.order.reference_code}: {self.get_to_status_display()}"
