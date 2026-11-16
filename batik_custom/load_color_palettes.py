
import json
from pathlib import Path
from django.conf import settings
from django.db import transaction
from batik_custom.models import ColorPalette

JSON_PATH = Path(settings.BASE_DIR) / "color_pallete.json"

@transaction.atomic
def load_color_palettes():
    if not JSON_PATH.is_file():
        raise FileNotFoundError(f"File JSON tidak ditemukan: {JSON_PATH}")

    with JSON_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list) or len(data) != 24:
        raise ValueError(
            f"JSON harus berisi 24 palet, ditemukan "
            f"{len(data) if isinstance(data, list) else 'format bukan list'}."
        )

    names = [str(item.get("name", "")).strip() for item in data]

    if any(not name for name in names):
        raise ValueError("Semua palet wajib memiliki nama.")

    if len(names) != len(set(names)):
        raise ValueError("Ada nama palet duplikat di JSON.")

    created_count = 0
    updated_count = 0

    for item in data:
        name = item["name"].strip()
        colors = item.get("colors", [])

        if not isinstance(colors, list) or not colors:
            raise ValueError(f"Colors kosong atau tidak valid: {name}")

        obj, created = ColorPalette.objects.update_or_create(
            name=name,
            defaults={
                "description": item.get("description", "")[:150],
                "colors": colors,
                "is_active": item.get("is_active", True),
            },
        )

        if created:
            created_count += 1
        else:
            updated_count += 1

    deactivated_count = (
        ColorPalette.objects.exclude(name__in=names)
        .filter(is_active=True)
        .update(is_active=False)
    )

    print("=== HASIL LOAD COLOR PALETTES ===")
    print(f"Palet di JSON: {len(data)}")
    print(f"Palet baru: {created_count}")
    print(f"Palet diperbarui: {updated_count}")
    print(f"Palet lama dinonaktifkan: {deactivated_count}")
    print(
        "Total palet aktif:",
        ColorPalette.objects.filter(is_active=True).count(),
    )
    print(
        "Nama palet:",
        ", ".join(
            ColorPalette.objects.filter(is_active=True)
            .order_by("name")
            .values_list("name", flat=True)
        ),
    )

load_color_palettes()
