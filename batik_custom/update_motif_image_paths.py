import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
JSON_FILE = BASE_DIR / "recommended_motifs.json"
IMAGE_DIR = BASE_DIR / "static" / "img" / "catalog" / "recommended_motifs"
DRY_RUN = "--cek" in sys.argv

sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.apps import apps
from django.db import transaction

Motif = apps.get_model("batik_custom", "RecommendedMotif")

with JSON_FILE.open("r", encoding="utf-8-sig") as file:
    entries = json.load(file)

if not IMAGE_DIR.is_dir():
    sys.exit(f"Folder gambar tidak ditemukan: {IMAGE_DIR}")

image_index = {
    path.name.casefold(): path
    for path in IMAGE_DIR.iterdir()
    if path.is_file()
}

updates = {}
missing_images = set()
missing_motifs = []
ambiguous = []
already_static = 0

for entry in entries:
    image_key = str(entry["image"])
    filename = Path(image_key.replace("\\", "/")).name
    source = image_index.get(filename.casefold())

    if source is None:
        missing_images.add(filename)
        continue

    target_path = f"img/catalog/recommended_motifs/{source.name}"

    queryset = Motif.objects.filter(
        name=entry["name"],
        description=entry["description"],
    )

    count = queryset.count()

    if count == 0:
        missing_motifs.append(entry["name"])
        continue

    if count > 1:
        ambiguous.append((entry["name"], count))

    for motif in queryset:
        current = str(motif.image.name or "")

        if current == target_path:
            already_static += 1
            continue

        updates[motif.pk] = target_path

print(f"Total data JSON       : {len(entries)}")
print(f"Motif yang ditemukan  : {len(updates)}")
print(f"Sudah memakai static  : {already_static}")
print(f"Gambar tidak ditemukan: {len(missing_images)}")
print(f"Motif tidak ditemukan : {len(missing_motifs)}")
print(f"Nama/deskripsi ganda  : {len(ambiguous)}")

if missing_images:
    print("\nGAMBAR TIDAK DITEMUKAN:")
    for name in sorted(missing_images):
        print(f"- {name}")

if missing_motifs:
    print("\nMOTIF TIDAK DITEMUKAN:")
    for name in sorted(set(missing_motifs)):
        print(f"- {name}")

if ambiguous:
    print("\nCATATAN: Ada pasangan nama/deskripsi yang cocok dengan beberapa baris.")
    for name, count in ambiguous[:10]:
        print(f"- {name}: {count} baris")

if missing_images or missing_motifs:
    sys.exit("\nPemeriksaan gagal. Database belum diubah.")

if DRY_RUN:
    sys.exit("\nPEMERIKSAAN BERHASIL. Belum ada perubahan database. Periksa jumlah di atas sebelum melanjutkan.")

with transaction.atomic():
    for pk, target_path in updates.items():
        Motif.objects.filter(pk=pk).update(image=target_path)

print("\nPEMBARUAN PATH SELESAI.")
print(f"Path diperbarui: {len(updates)}")
print(f"Total motif sekarang: {Motif.objects.count()}")
print("File gambar lama tidak dihapus.")
