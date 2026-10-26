
from django.core.validators import MinValueValidator
from django.db import models


class DonasiKain(models.Model):

    class JenisDonasi(models.TextChoices):
        PAKAIAN = "PAKAIAN", "Pakaian"
        KAIN = "KAIN", "Kain Bekas"
        HIJAB = "HIJAB", "Hijab/Aksesori"
        LAINNYA = "LAINNYA", "Lainnya"

    class KategoriPakaian(models.TextChoices):
        ANAK = "ANAK", "Anak-anak"
        DEWASA_LAKI = "DEWASA_LAKI", "Dewasa laki-laki"
        DEWASA_PEREMPUAN = "DEWASA_PEREMPUAN", "Dewasa perempuan"
        TIDAK_SPESIFIK = "TIDAK_SPESIFIK", "Tidak spesifik"

    class Kondisi(models.TextChoices):
        SANGAT_BAIK = "SANGAT_BAIK", "Sangat Baik"
        BAIK = "BAIK", "Baik"
        CUKUP = "CUKUP", "Cukup"
        TIDAK_LAYAK = "TIDAK_LAYAK", "Tidak layak pakai"

    class MetodeDonasi(models.TextChoices):
        JEMPUT = "JEMPUT", "Dijemput oleh pihak pengelola"
        KIRIM_SENDIRI = "KIRIM_SENDIRI", "Saya mengirim sendiri"

    class Status(models.TextChoices):
        MENUNGGU = "MENUNGGU", "Menunggu konfirmasi"
        DIKONFIRMASI = "DIKONFIRMASI", "Dikonfirmasi"
        SELESAI = "SELESAI", "Selesai"

    donor_name = models.CharField("Nama donatur", max_length=120)
    whatsapp = models.CharField("Nomor WhatsApp", max_length=25)
    email = models.EmailField("E-mail")
    address = models.TextField("Alamat")
    city = models.CharField("Kota/Kabupaten", max_length=100)

    item_name = models.CharField("Nama barang", max_length=150)
    donation_type = models.CharField(
        "Jenis donasi",
        max_length=20,
        choices=JenisDonasi.choices,
    )
    clothing_category = models.CharField(
        "Kategori pakaian",
        max_length=30,
        choices=KategoriPakaian.choices,
        blank=True,
    )
    quantity = models.PositiveSmallIntegerField(
        "Jumlah barang",
        validators=[MinValueValidator(1)],
    )
    condition = models.CharField(
        "Kondisi barang",
        max_length=20,
        choices=Kondisi.choices,
    )
    description = models.TextField("Deskripsi barang")
    photo = models.ImageField(
        "Foto barang",
        upload_to="donasi_kain/",
        blank=True,
        null=True,
    )

    donation_method = models.CharField(
        "Metode donasi",
        max_length=20,
        choices=MetodeDonasi.choices,
    )
    pickup_date = models.DateField(
        "Tanggal pengambilan/pengiriman",
        blank=True,
        null=True,
    )
    additional_notes = models.TextField(
        "Deskripsi tambahan",
        blank=True,
    )

    status = models.CharField(
        "Status",
        max_length=20,
        choices=Status.choices,
        default=Status.MENUNGGU,
    )
    created_at = models.DateTimeField(
        "Tanggal pengajuan",
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Donasi kain"
        verbose_name_plural = "Donasi kain"

    def __str__(self):
        return f"{self.item_name} - {self.donor_name}"
