"""Agregasi data untuk halaman Impact Tracker.

Seluruh angka dihitung langsung dari model yang sudah ada
(``donasi.DonasiKain`` dan ``upcycling.UpcyclingRequest``). Tidak ada tabel
baru, dan tidak ada angka dampak lingkungan yang diperkirakan.

Definisi metrik (juga ditampilkan di halaman):
- Barang tercatat   : jumlah ``quantity`` seluruh pengajuan donasi.
- Barang selesai    : jumlah ``quantity`` donasi berstatus SELESAI.
- Donatur unik      : alamat e-mail unik (tanpa membedakan huruf besar/kecil),
                    karena ``DonasiKain`` tidak terhubung ke akun pengguna.
- Berat tekstil     : tidak dihitung, karena tidak ada field berat.
"""

from datetime import datetime

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce, Lower, TruncMonth
from django.utils import timezone

from donasi.models import DonasiKain
from upcycling.models import UpcyclingRequest

DONASI_DONE = DonasiKain.Status.SELESAI
UPCYCLING = UpcyclingRequest.Status

# Kunci query string ``?period=`` -> jumlah bulan (None = seluruh riwayat).
PERIOD_CHOICES = {"6": 6, "12": 12, "all": None}
PERIOD_LABELS = {"6": "6 bulan", "12": "12 bulan", "all": "Semua"}
DEFAULT_PERIOD = "12"

RECENT_ACTIVITY_LIMIT = 8

MONTH_SHORT = [
    "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
    "Jul", "Agu", "Sep", "Okt", "Nov", "Des",
]
MONTH_LONG = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def format_id_date(value):
    """Format tanggal ke bahasa Indonesia, mis. ``28 Okt 2026``."""
    local = timezone.localtime(value)
    return f"{local.day} {MONTH_SHORT[local.month - 1]} {local.year}"


def _sum(field, **filters):
    return Coalesce(Sum(field, filter=Q(**filters) if filters else None), 0)



# Statistik

def get_donation_stats():
    totals = DonasiKain.objects.aggregate(
        submissions=Count("pk"),
        items_recorded=_sum("quantity"),
        items_completed=_sum("quantity", status=DONASI_DONE),
    )

    unique_donors = (
        DonasiKain.objects.annotate(email_key=Lower("email"))
        .values("email_key")
        .distinct()
        .count()
    )

    by_status = {
        row["status"]: row["total"]
        for row in DonasiKain.objects.values("status").annotate(total=Count("pk"))
    }

    return {
        **totals,
        "unique_donors": unique_donors,
        "status_counts": {
            status: by_status.get(status, 0)
            for status in DonasiKain.Status.values
        },
    }


def get_upcycling_stats():
    active = ~Q(status=UPCYCLING.CANCELLED)
    totals = UpcyclingRequest.objects.aggregate(
        requests=Count("pk", filter=active),
        participants=Count("user", distinct=True, filter=active),
        items_completed=_sum("quantity", status=UPCYCLING.COMPLETED),
        pending=Count("pk", filter=Q(status=UPCYCLING.PENDING)),
        processing=Count("pk", filter=Q(status=UPCYCLING.PROCESSING)),
        completed=Count("pk", filter=Q(status=UPCYCLING.COMPLETED)),
    )
    return totals


def get_personal_stats(user):
    """Kontribusi pribadi.

    Hanya upcycling yang bisa dikaitkan ke akun (``UpcyclingRequest.user``).
    ``DonasiKain`` tidak punya relasi ke pengguna, sehingga donasi tidak
    ditampilkan sebagai milik pribadi (mencocokkan lewat e-mail yang belum
    diverifikasi bisa membocorkan data orang lain).
    """
    active = ~Q(status=UPCYCLING.CANCELLED)
    return UpcyclingRequest.objects.filter(user=user).aggregate(
        requests=Count("pk", filter=active),
        processing=Count(
            "pk",
            filter=Q(status__in=[UPCYCLING.PENDING, UPCYCLING.PROCESSING]),
        ),
        completed=Count("pk", filter=Q(status=UPCYCLING.COMPLETED)),
        items_completed=_sum("quantity", status=UPCYCLING.COMPLETED),
    )



# Perjalanan donasi

def get_journeys(donation_stats, upcycling_stats):
    """Tahapan sesuai status yang benar-benar ada di model.

    Angka pada tiap tahap adalah jumlah pengajuan yang *saat ini* berada di
    status tersebut.
    """
    counts = donation_stats["status_counts"]
    return [
        {
            "title": "Donasi Kain",
            "stages": [
                {
                    "label": "Pengajuan",
                    "description": "Donasi diajukan dan menunggu konfirmasi pengelola.",
                    "count": counts[DonasiKain.Status.MENUNGGU],
                },
                {
                    "label": "Dikonfirmasi",
                    "description": "Pengelola menyetujui dan mengatur penerimaan barang.",
                    "count": counts[DonasiKain.Status.DIKONFIRMASI],
                },
                {
                    "label": "Selesai",
                    "description": "Barang sudah diterima dan selesai diproses.",
                    "count": counts[DonasiKain.Status.SELESAI],
                },
            ],
        },
        {
            "title": "Upcycling",
            "stages": [
                {
                    "label": "Menunggu Tinjauan",
                    "description": "Permintaan masuk dan menunggu ditinjau.",
                    "count": upcycling_stats["pending"],
                },
                {
                    "label": "Diproses",
                    "description": "Kain sedang diolah menjadi produk baru.",
                    "count": upcycling_stats["processing"],
                },
                {
                    "label": "Selesai",
                    "description": "Produk upcycling sudah selesai dibuat.",
                    "count": upcycling_stats["completed"],
                },
            ],
        },
    ]



# Grafik bulanan

def _shift_month(year, month, delta):
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def _month_start(year, month):
    return timezone.make_aware(datetime(year, month, 1))


def get_period_options(active_period):
    return [
        {"key": key, "label": label, "active": key == active_period}
        for key, label in PERIOD_LABELS.items()
    ]


def get_monthly_chart(period):
    """Barang donasi per bulan pengajuan, dipisah selesai vs belum selesai.

    ``DonasiKain`` hanya menyimpan ``created_at`` (tidak ada tanggal selesai),
    sehingga setiap bulan menunjukkan barang yang *diajukan* pada bulan itu
    dan status terkininya.
    """
    now = timezone.localtime()
    end = (now.year, now.month)
    months = PERIOD_CHOICES[period]

    queryset = DonasiKain.objects.all()
    if months is not None:
        start = _shift_month(*end, -(months - 1))
        queryset = queryset.filter(created_at__gte=_month_start(*start))
    else:
        first = queryset.order_by("created_at").values_list(
            "created_at", flat=True
        ).first()
        if first is None:
            return {"has_data": False, "bars": [], "total": 0}
        first = timezone.localtime(first)
        start = (first.year, first.month)

    rows = {
        (row["month"].year, row["month"].month): row
        for row in queryset.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            completed=_sum("quantity", status=DONASI_DONE),
            in_progress=Coalesce(
                Sum("quantity", filter=~Q(status=DONASI_DONE)), 0
            ),
        )
    }

    bars = []
    year, month = start
    while (year, month) <= end:
        row = rows.get((year, month))
        completed = row["completed"] if row else 0
        in_progress = row["in_progress"] if row else 0
        bars.append(
            {
                "label": MONTH_SHORT[month - 1],
                "long_label": f"{MONTH_LONG[month - 1]} {year}",
                "year": year,
                "show_year": month == 1 or not bars,
                "completed": completed,
                "in_progress": in_progress,
                "total": completed + in_progress,
            }
        )
        year, month = _shift_month(year, month, 1)

    peak = max((bar["total"] for bar in bars), default=0)
    for bar in bars:
        bar["completed_pct"] = round(bar["completed"] / peak * 100, 1) if peak else 0
        bar["in_progress_pct"] = round(bar["in_progress"] / peak * 100, 1) if peak else 0

    total = sum(bar["total"] for bar in bars)
    return {
        "has_data": total > 0,
        "bars": bars,
        "total": total,
        "peak": peak,
    }


# Aktivitas terbaru (tanpa data pribadi)


def get_recent_activity(limit=RECENT_ACTIVITY_LIMIT):
    """Gabungan donasi dan upcycling terbaru.

    Hanya field generik yang diambil: jenis, jumlah, status, tanggal. Nama,
    e-mail, WhatsApp, alamat, kota, nama barang, dan catatan bebas sengaja
    tidak dimuat.
    """
    donations = DonasiKain.objects.only(
        "donation_type", "quantity", "status", "created_at"
    ).order_by("-created_at")[:limit]

    upcycling = (
        UpcyclingRequest.objects.exclude(status=UPCYCLING.CANCELLED)
        .only("product", "quantity", "status", "created_at")
        .order_by("-created_at")[:limit]
    )

    items = [
        {
            "kind": "donasi",
            "kind_label": "Donasi",
            "title": f"Donasi {obj.get_donation_type_display()}",
            "quantity": obj.quantity,
            "status": obj.status,
            "status_label": obj.get_status_display(),
            "done": obj.status == DONASI_DONE,
            "created_at": obj.created_at,
        }
        for obj in donations
    ] + [
        {
            "kind": "upcycling",
            "kind_label": "Upcycling",
            "title": f"Upcycling {obj.get_product_display()}",
            "quantity": obj.quantity,
            "status": obj.status,
            "status_label": obj.get_status_display(),
            "done": obj.status == UPCYCLING.COMPLETED,
            "created_at": obj.created_at,
        }
        for obj in upcycling
    ]

    items.sort(key=lambda item: item["created_at"], reverse=True)
    items = items[:limit]
    for item in items:
        item["date_text"] = format_id_date(item["created_at"])
    return items