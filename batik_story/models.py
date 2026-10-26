from django.db import models
from django.core.validators import MinValueValidator
from django.db import models



# Create your models here.


# Model Batik Motif
class BatikMotif(models.Model):
    nama=models.CharField(max_length=255, null=False, blank=False)
    ASAL_CHOICES = [
        #Jakarta
        ('JAKARTA', 'Jakarta'),
        
        # Yogyakarta & Jawa Tengah
        ('YOGYAKARTA', 'Yogyakarta'),
        ('SOLO', 'Solo'),
        ('PEKALONGAN', 'Pekalongan'),
        ('BANYUMAS', 'Banyumas'),
        ('LASEM', 'Lasem'),
        ('SEMARANG', 'Semarang'),
        ('DEMAK', 'Demak'),
        ('KUDUS', 'Kudus'),
        ('JEPARA', 'Jepara'),
        ('PATI', 'Pati'),
        ('REMBANG', 'Rembang'),
        ('WONOSOBO', 'Wonosobo'),
        ('KLATEN', 'Klaten'),
        ('SRAGEN', 'Sragen'),
        ('MAGELANG', 'Magelang'),
        ('TEGAL', 'Tegal'),
        ('BREBES', 'Brebes'),
        ('BATANG', 'Batang'),

        # Jawa Barat & Banten
        ('CIREBON', 'Cirebon'),
        ('GARUT', 'Garut'),
        ('TASIKMALAYA', 'Tasikmalaya'),
        ('INDRAMAYU', 'Indramayu'),
        ('BANDUNG', 'Bandung'),
        ('SUMEDANG', 'Sumedang'),
        ('SUBANG', 'Subang'),
        ('CIAMIS', 'Ciamis'),
        ('BANTEN', 'Banten'),
        ('LEBAK', 'Lebak'),
        ('TANGERANG', 'Tangerang'),

        # Jawa Timur
        ('MADURA', 'Madura'),
        ('TUBAN', 'Tuban'),
        ('LAMONGAN', 'Lamongan'),
        ('SIDOARJO', 'Sidoarjo'),
        ('MOJOKERTO', 'Mojokerto'),
        ('KEDIRI', 'Kediri'),
        ('MALANG', 'Malang'),
        ('PONOROGO', 'Ponorogo'),
        ('TULUNGAGUNG', 'Tulungagung'),
        ('BANYUWANGI', 'Banyuwangi'),
        ('JEMBER', 'Jember'),
        ('BLITAR', 'Blitar'),
        ('BOJONEGORO', 'Bojonegoro'),
        ('PASURUAN', 'Pasuruan'),
        ('PROBOLINGGO', 'Probolinggo'),

        # Bali & Nusa Tenggara
        ('BALI', 'Bali'),
        ('LOMBOK', 'Lombok'),
        ('SUMBA', 'Sumba'),
        ('FLORES', 'Flores'),

        # Sumatra
        ('ACEH', 'Aceh'),
        ('JAMBI', 'Jambi'),
        ('PALEMBANG', 'Palembang'),
        ('BENGKULU', 'Bengkulu'),
        ('LAMPUNG', 'Lampung'),
        ('RIAU', 'Riau'),
        ('BANGKA_BELITUNG', 'Bangka Belitung'),

        # Kalimantan
        ('KALIMANTAN_BARAT', 'Kalimantan Barat'),
        ('KALIMANTAN_SELATAN', 'Kalimantan Selatan'),
        ('KALIMANTAN_TIMUR', 'Kalimantan Timur'),

        # Sulawesi
        ('SULAWESI_UTARA', 'Sulawesi Utara'),
        ('SULAWESI_TENGAH', 'Sulawesi Tengah'),
        ('SULAWESI_SELATAN', 'Sulawesi Selatan'),
        ('SULAWESI_TENGGARA', 'Sulawesi Tenggara'),

        # Maluku
        ('MALUKU', 'Maluku'),
    ]
    ASAL_CHOICES.sort(key=lambda x: x[1])
    asal=models.CharField(choices=ASAL_CHOICES,max_length=300, null=False, blank=False)
    filosofi=models.TextField()
    deskripsi=models.TextField()
    gambar=models.ImageField(upload_to='batik/',blank=True, null=True)

    def __str__(self):
        return self.nama


class DonasiKain(models.Model):

    JENIS_DONASI = [
        ("PAKAIAN", "Pakaian"),
        ("KAIN", "Kain Bekas"),
        ("HIJAB", "Hijab/Aksesori"),
        ("LAINNYA", "Lainnya"),
    ]

    KATEGORI_PAKAIAN = [
        ("ANAK", "Anak-anak"),
        ("DEWASA_LAKI", "Dewasa laki-laki"),
        ("DEWASA_PEREMPUAN", "Dewasa perempuan"),
        ("TIDAK_SPESIFIK", "Tidak spesifik"),
    ]

    KONDISI_BARANG = [
        ("SANGAT_BAIK", "Sangat Baik"),
        ("BAIK", "Baik"),
        ("CUKUP", "Cukup"),
        ("TIDAK_LAYAK", "Tidak layak pakai"),
    ]

    METODE_DONASI = [
        ("JEMPUT", "Dijemput oleh pihak pengelola"),
        ("KIRIM_SENDIRI", "Saya mengirim sendiri"),
    ]

    STATUS_DONASI = [
        ("MENUNGGU", "Menunggu konfirmasi"),
        ("DIKONFIRMASI", "Dikonfirmasi"),
        ("SELESAI", "Selesai"),
    ]

    donor_name = models.CharField(max_length=120)
    whatsapp = models.CharField(max_length=25)
    email = models.EmailField()
    address = models.TextField()
    city = models.CharField(max_length=100)

    item_name = models.CharField(max_length=150)
    donation_type = models.CharField(
        max_length=20, choices=JENIS_DONASI
    )
    clothing_category = models.CharField(
        max_length=30, choices=KATEGORI_PAKAIAN, blank=True
    )
    quantity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)]
    )
    condition = models.CharField(
        max_length=20, choices=KONDISI_BARANG
    )
    description = models.TextField()
    photo = models.ImageField(
        upload_to="donasi_kain/", blank=True, null=True
    )

    donation_method = models.CharField(
        max_length=20, choices=METODE_DONASI
    )
    pickup_date = models.DateField(blank=True, null=True)
    additional_notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_DONASI,
        default="MENUNGGU",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.item_name} - {self.donor_name}"


    
