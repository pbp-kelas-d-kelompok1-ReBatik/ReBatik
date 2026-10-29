
import json
import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
APP_LABEL = "batik_custom"
MODEL_NAME = "RecommendedMotif"
JSON_FILE = BASE_DIR / "recommended_motifs.json"
IMAGE_DIR = BASE_DIR / "static" / "img" / "catalog" / "recommended_motifs"
DRY_RUN = "--cek" in sys.argv

sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.apps import apps
from django.core.files import File
from django.db import transaction

Motif = apps.get_model(APP_LABEL, MODEL_NAME)

def normalize(value):
    return str(value).strip().casefold()

def get_base_style(value):
    value = str(value).strip()
    value = re.sub(r"\s*\((Women|Men)\)\s*$", "", value, flags=re.IGNORECASE)
    return value.strip()

def find_m2m_field(keyword):
    for field in Motif._meta.many_to_many:
        if keyword.casefold() in field.name.casefold():
            return field
    available = [field.name for field in Motif._meta.many_to_many]
    sys.exit(f"Field ManyToMany yang memuat '{keyword}' tidak ditemukan pada model {MODEL_NAME}. Field tersedia: {available}")

def build_map(queryset):
    result = {}
    for obj in queryset.order_by("pk"):
        result.setdefault(normalize(obj), obj)
    return result

def report_missing(title, values):
    if values:
        print(f"\nTIDAK DITEMUKAN ({title}):")
        for value in sorted(values, key=str.casefold):
            print(f"  - {value}")

if not JSON_FILE.is_file():
    sys.exit(f"File JSON tidak ditemukan: {JSON_FILE}")

if not IMAGE_DIR.is_dir():
    sys.exit(f"Folder gambar tidak ditemukan: {IMAGE_DIR}")

try:
    with JSON_FILE.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)
except (json.JSONDecodeError, OSError) as exc:
    sys.exit(f"Gagal membaca JSON: {exc}")

if not isinstance(data, list):
    sys.exit("Format JSON harus berupa list berisi objek motif.")

f_styles = find_m2m_field("style")
f_palettes = find_m2m_field("palette")
f_fashion = find_m2m_field("fashion")

palette_map = build_map(f_palettes.remote_field.model.objects.all())
fashion_map = build_map(f_fashion.remote_field.model.objects.all())
style_map = {}

for obj in f_styles.remote_field.model.objects.all().order_by("pk"):
    text = str(obj).strip()
    base_name = re.split(r"\s*[—–-]\s*", text, maxsplit=1)[0]
    style_map.setdefault(normalize(base_name), obj)

image_index = {}
for path in IMAGE_DIR.iterdir():
    if path.is_file():
        image_index.setdefault(path.name.casefold(), path)

required_fields = {"name", "description", "image", "styles", "palettes", "fashion_preference"}
missing = {"field": set(), "palet": set(), "fashion": set(), "style": set(), "gambar": set()}
images = {}
valid_entries = []

for index, entry in enumerate(data, start=1):
    if not isinstance(entry, dict):
        missing["field"].add(f"Entri {index}: bukan objek JSON")
        continue
    absent = required_fields - entry.keys()
    if absent:
        missing["field"].add(f"Entri {index}: field {', '.join(sorted(absent))}")
        continue
    invalid_lists = [key for key in ("styles", "palettes", "fashion_preference") if not isinstance(entry[key], list)]
    if invalid_lists:
        missing["field"].add(f"Entri {index}: {', '.join(invalid_lists)} harus berupa list")
        continue
    valid_entries.append(entry)
    for palette in entry["palettes"]:
        if normalize(palette) not in palette_map:
            missing["palet"].add(str(palette))
    for fashion in entry["fashion_preference"]:
        if normalize(fashion) not in fashion_map:
            missing["fashion"].add(str(fashion))
    for style in entry["styles"]:
        base_name = get_base_style(style)
        if normalize(base_name) not in style_map:
            missing["style"].add(str(style))
    image_key = str(entry["image"])
    filename = Path(image_key.replace("\\", "/")).name.casefold()
    if image_key not in images:
        images[image_key] = image_index.get(filename)
    if images[image_key] is None:
        missing["gambar"].add(image_key)

print(f"Entri di JSON      : {len(data)}")
print(f"Entri dengan field : {len(valid_entries)}")
print(f"Palet di DB        : {len(palette_map)}")
print(f"Fashion di DB      : {len(fashion_map)}")
print(f"Style di DB        : {len(style_map)}")
print(f"File gambar        : {len(image_index)}")
print(f"Folder gambar      : {IMAGE_DIR}")

for category, values in missing.items():
    report_missing(category, values)

if any(missing.values()):
    sys.exit("\nVALIDASI GAGAL. Database belum diubah. Perbaiki item yang ditampilkan, lalu jalankan --cek lagi.")

if DRY_RUN:
    sys.exit("\nVALIDASI BERHASIL. Semua referensi cocok. Jalankan script tanpa --cek untuk mengimpor data.")

name_unique = Motif._meta.get_field("name").unique
created = 0
skipped = 0

try:
    with transaction.atomic():
        for entry in valid_entries:
            name = str(entry["name"]).strip()
            description = str(entry["description"]).strip()
            if name_unique:
                style_label = get_base_style(entry["styles"][0]) if entry["styles"] else "Style"
                palette_label = str(entry["palettes"][0]) if entry["palettes"] else "Palette"
                fashion_label = str(entry["fashion_preference"][0]) if entry["fashion_preference"] else "Fashion"
                name = f"{name} — {style_label} · {palette_label} · {fashion_label}"
            if Motif.objects.filter(name=name, description=description).exists():
                skipped += 1
                continue
            obj = Motif(name=name, description=description, is_active=entry.get("is_active", True))
            image_key = str(entry["image"])
            image_path = images[image_key]
            obj.image = f"recommended_motifs/{image_path.name}"
            obj.save()
            style_objects = [style_map[normalize(get_base_style(style))] for style in entry["styles"]]
            getattr(obj, f_styles.name).set(style_objects)
            palette_objects = [palette_map[normalize(palette)] for palette in entry["palettes"]]
            getattr(obj, f_palettes.name).set(palette_objects)
            fashion_objects = [fashion_map[normalize(fashion)] for fashion in entry["fashion_preference"]]
            getattr(obj, f_fashion.name).set(fashion_objects)
            created += 1
except Exception as exc:
    print(f"\nIMPORT GAGAL: {exc}")
    print("Transaksi database dibatalkan.")
    raise

print("\nIMPORT SELESAI!")
print(f"Data dibuat   : {created}")
print(f"Data dilewati : {skipped}")
print(f"Total motif   : {Motif.objects.count()}")
