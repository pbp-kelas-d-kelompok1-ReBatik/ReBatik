from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.templatetags.static import static


def resolve_image_url(image_field):
    """Kembalikan URL gambar yang benar untuk semua jenis nilai ImageField.

    - ``img/...``        -> file katalog di folder static (disajikan WhiteNoise)
    - ``http(s)://...``  -> dipakai apa adanya
    - lainnya            -> upload admin lewat storage (Cloudinary / media)
    """
    name = getattr(image_field, "name", "") or ""
    if not name:
        return ""
    if name.startswith(("http://", "https://", "//")):
        return name
    if name.startswith("img/"):
        return static(name)
    try:
        return image_field.url
    except ValueError:
        return ""


class ImageUrlMixin:
    @property
    def static_image_path(self):
        # Dipertahankan agar kode lama tetap jalan.
        if self.image and self.image.name.startswith("img/"):
            return self.image.name
        return ""

    @property
    def image_url(self):
        return resolve_image_url(self.image)


class StyleOptions(ImageUrlMixin, models.Model):
    GENDER_CHOICES = [
        ("women", "Women"),
        ("men", "Men"),
        ("unisex", "Unisex"),
    ]

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    detail = models.CharField(max_length=400)
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        default="women",
    )
    icon = models.CharField(max_length=50, blank=True)
    image = models.ImageField(
        upload_to="style_options/",
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_gender_display()})"


class ColorPalette(ImageUrlMixin, models.Model):
    name = models.CharField(max_length=70, unique=True)
    description = models.CharField(max_length=150, blank=True)
    colors = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(
        upload_to="colorpalette/",
        blank=True,
    )

    def __str__(self):
        return self.name


class StyleProfile(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="batik_style_profiles",
    )
    style = models.ForeignKey(
        StyleOptions,
        on_delete=models.PROTECT,
        related_name="profiles",
    )
    palette = models.ForeignKey(
        ColorPalette,
        on_delete=models.PROTECT,
        related_name="profiles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.style.name}"


class FashionPreference(models.Model):
    name = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Fashion preference"
        verbose_name_plural = "Fashion preferences"

    def __str__(self):
        return self.name


class RecommendedMotif(ImageUrlMixin, models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="recommended_motifs/",
        blank=True,
        null=True,
    )
    styles = models.ManyToManyField(
        StyleOptions,
        blank=True,
        related_name="recommended_motifs",
    )
    palettes = models.ManyToManyField(
        ColorPalette,
        blank=True,
        related_name="recommended_motifs",
    )
    fashion_preference = models.ManyToManyField(
        FashionPreference,
        blank=True,
        related_name="recommended_motifs",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Recommended motif"
        verbose_name_plural = "Recommended motifs"

    def __str__(self):
        return self.name


class SavedDesign(models.Model):
    LAYOUT_CHOICES = [
        ("single", "Single Motif"),
        ("grid", "Grid"),
        ("brick", "Brick"),
        ("half_drop", "Half Drop"),
        ("mirror", "Mirror"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_batik_designs",
    )
    title = models.CharField(max_length=150)
    motif = models.ForeignKey(
        RecommendedMotif,
        on_delete=models.PROTECT,
        related_name="saved_designs",
    )
    palette = models.ForeignKey(
        ColorPalette,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="saved_designs",
    )
    layout = models.CharField(
        max_length=20,
        choices=LAYOUT_CHOICES,
        default="grid",
    )
    scale = models.PositiveSmallIntegerField(default=100)
    rotation = models.SmallIntegerField(default=0)
    gap = models.PositiveSmallIntegerField(default=50)
    color = models.CharField(max_length=7, default="#874a29")
    tint = models.PositiveSmallIntegerField(default=0)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Saved design"
        verbose_name_plural = "Saved designs"

    def __str__(self):
        return f"{self.title} - {self.user}"


class ProductDesignOption(models.Model):
    PRODUCT_CHOICES = [
        ("fabric", "Kain Batik"),
        ("shirt", "Kemeja"),
        ("outer", "Outer"),
        ("dress", "Dress"),
        ("skirt", "Rok"),
        ("pants", "Celana"),
        ("hijab", "Hijab"),
        ("tote_bag", "Tote Bag"),
        ("pouch", "Pouch"),
        ("sling_bag", "Tas Selempang"),
        ("accessories", "Aksesori"),
        ("home_decor", "Dekorasi Rumah"),
    ]

    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_CHOICES,
    )
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to="product_designs/")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["product_type", "name"]
        verbose_name = "Product Design Option"
        verbose_name_plural = "Product Design Options"

    def __str__(self):
        return f"{self.get_product_type_display()} - {self.name}"


class BatikOrder(models.Model):
    PRODUCT_CHOICES = ProductDesignOption.PRODUCT_CHOICES

    PAYMENT_CHOICES = [
        ("bank", "Transfer Bank"),
        ("ewallet", "E-Wallet"),
        ("va", "Virtual Account"),
        ("qris", "QRIS"),
    ]

    STATUS_CHOICES = [
        ("pending", "Menunggu konfirmasi"),
        ("confirmed", "Dikonfirmasi"),
        ("processing", "Diproses"),
        ("completed", "Selesai"),
        ("cancelled", "Dibatalkan"),
    ]

    # Pengguna dan desain batik
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="batik_orders",
    )
    motif = models.ForeignKey(
        RecommendedMotif,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    palette = models.ForeignKey(
        ColorPalette,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    style_name = models.CharField(max_length=100, blank=True)
    design_settings = models.JSONField(default=dict, blank=True)

    # Produk yang dipesan
    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_CHOICES,
    )
    design_option = models.ForeignKey(
        ProductDesignOption,
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True,
    )

    # Spesifikasi produk custom
    material = models.CharField(max_length=100)
    size = models.CharField(max_length=50, blank=True)
    sleeve_type = models.CharField(max_length=50, blank=True)
    fit_type = models.CharField(max_length=50, blank=True)
    motif_placement = models.CharField(max_length=100, blank=True)
    custom_requirements = models.TextField(blank=True)

    # Jumlah pesanan
    quantity = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    unit = models.CharField(max_length=20, default="pcs")
    notes = models.TextField(blank=True)

    # Informasi penerima
    recipient_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    address = models.TextField()
    province = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10)

    # Pembayaran dan harga dalam rupiah
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
    )
    unit_price = models.PositiveIntegerField(default=250000)
    total_price = models.PositiveIntegerField(default=250000)

    # Status pesanan
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Batik Order"
        verbose_name_plural = "Batik Orders"

    def save(self, *args, **kwargs):
        if self.quantity < 1:
            raise ValueError("Jumlah pesanan minimal 1.")
        if self.design_option_id and self.product_type != self.design_option.product_type:
            raise ValueError("Kategori produk harus sesuai dengan model desain.")

        previous_status = None
        if self.pk:
            previous_status = type(self).objects.filter(pk=self.pk).values_list("status", flat=True).first()
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)

        # Perubahan status melalui admin maupun kode aplikasi akan memberi kabar ke pemilik.
        if previous_status and previous_status != self.status:
            from main.models import Notification
            Notification.objects.create(
                user=self.user,
                title="Status pesanan diperbarui",
                message=f"Pesanan #{self.pk} sekarang berstatus: {self.get_status_display()}.",
                notification_type="order_updated",
                target_url=f"/batik_custom/order/{self.pk}/confirmation/",
            )

    def __str__(self):
        return f"Pesanan #{self.pk} - {self.recipient_name}"
