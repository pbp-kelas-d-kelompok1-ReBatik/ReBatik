from django.db import models

# Create your models here.


# Model Batik Motif
class BatikMotif(models.Model):
    nama=models.CharField(max_length=255, null=False, blank=False)
    ASAL_CHOICES = [
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
    asal=models.CharField(choices=ASAL_CHOICES,max_length=300, null=False, blank=False)
    filosofi=models.TextField()
    deskripsi=models.TextField()
    gambar=models.ImageField(upload_to='batik',blank=True, null=True)

    def __str__(self):
        return super().__str__()

    
