import os
import json
from pathlib import Path
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.conf import settings
from django.db import transaction
from django.utils.text import slugify
from batik_custom.models import StyleOptions, ColorPalette, MotifRecommendation
JSON_PATH = Path(__file__).resolve().parent.parent / "rekomendasi_batik.json"
@transaction.atomic
def import_recommendations():
    if not JSON_PATH.is_file():
        raise FileNotFoundError(f"File JSON tidak ditemukan: {JSON_PATH}")
    with JSON_PATH.open("r", encoding="utf-8") as file:
        catalog = json.load(file)
    recommendations = catalog.get("recommendations", [])
    if len(recommendations) != 48:
        raise ValueError(f"JSON harus berisi 48 kombinasi, ditemukan {len(recommendations)}.")
    created_count = 0
    updated_count = 0
    missing_images = set()
    for recommendation in recommendations:
        preference = recommendation["fashion_preference"].strip().title()
        if preference not in {"Women", "Men"}:
            raise ValueError(f"Fashion preference tidak valid: {preference}")
        style = StyleOptions.objects.filter(name__iexact=recommendation["style"], gender=preference.lower(), is_active=True).first()
        palette = ColorPalette.objects.filter(name__iexact=recommendation["color_palette"], is_active=True).first()
        if style is None:
            raise ValueError(f"Style tidak ditemukan: {recommendation['style']} ({preference})")
        if palette is None:
            raise ValueError(f"Palet tidak ditemukan: {recommendation['color_palette']}")
        for motif_data in recommendation["motifs"]:
            name = motif_data["name"].strip()
            key = f"{recommendation['id']}::{slugify(name)}"
            defaults = {
                "fashion_preference": preference,
                "style": style,
                "palette": palette,
                "name": name,
                "description": motif_data.get("description", ""),
                "suggested_colors": motif_data.get("suggested_colors", []),
                "is_active": True,
            }
            image_name = Path(str(motif_data.get("image", ""))).name
            if image_name:
                relative_image = Path("img/catalog/recommended_motifs") / image_name
                absolute_image = Path(settings.BASE_DIR) / "static" / relative_image
                if absolute_image.is_file():
                    defaults["image"] = relative_image.as_posix()
                else:
                    missing_images.add(image_name)
            _, created = MotifRecommendation.objects.update_or_create(recommendation_key=key, defaults=defaults)
            if created:
                created_count += 1
            else:
                updated_count += 1
    print("\n=== HASIL IMPORT REBATIK ===")
    print(f"Kombinasi JSON: {len(recommendations)}")
    print(f"Entri baru: {created_count}")
    print(f"Entri diperbarui: {updated_count}")
    print(f"Total MotifRecommendation: {MotifRecommendation.objects.count()}")
    if missing_images:
        print("Gambar tidak ditemukan:", ", ".join(sorted(missing_images)))
    print("Import selesai.")
if __name__ == "__main__":
    import_recommendations()
