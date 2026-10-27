import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

import django
django.setup()

from pathlib import Path
from django.conf import settings
from batik_custom.models import RecommendedMotif

IMAGE_MAP = {
    "kawung": "kawung",
    "kawung minimal": "kawung",
    "truntum": "truntum",
    "parang": "parang",
    "parang sederhana": "parang",
    "parang kontemporer": "parang",
    "ceplok": "ceplok",
    "ceplok geometris": "ceplok",
    "mega mendung": "megamendung",
    "flora nusantara": "flora_nusantara",
    "sekar jagad": "sekar_jagad",
    "batik semen": "semen",
    "semen": "semen",
    "ondel-ondel": "ondel2",
    "ondel ondel": "ondel2",
}


def connect_images():
    image_dir = Path(settings.MEDIA_ROOT) / "recommended_motifs"
    updated = 0

    if not image_dir.is_dir():
        print(f"Folder tidak ditemukan: {image_dir}")
        return

    for motif in RecommendedMotif.objects.all():
        prefix = IMAGE_MAP.get(motif.name.strip().casefold())

        if not prefix:
            continue

        files = sorted(image_dir.glob(f"{prefix}.*"))

        if not files:
            print(f"Gambar belum ditemukan untuk: {motif.name}")
            continue

        relative_path = files[0].relative_to(
            Path(settings.MEDIA_ROOT)
        ).as_posix()

        motif.image.name = relative_path
        motif.save(update_fields=["image"])
        updated += 1

    print(f"Selesai! {updated} data motif sudah dihubungkan.")


if __name__ == "__main__":
    import django
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    connect_images()
