from pathlib import Path
import shutil

from django.conf import settings
from django.db import migrations


STYLE_IMAGE_PATHS = {
    "style_options/bohemian.jpe": "img/catalog/style_options/bohemian.jpe",
    "style_options/bohemian1.jpg": "img/catalog/style_options/bohemian1.jpg",
    "style_options/casual.jpe": "img/catalog/style_options/casual.jpe",
    "style_options/casual1.webp": "img/catalog/style_options/casual1.webp",
    "style_options/creative.jpg": "img/catalog/style_options/creative.jpg",
    "style_options/creative_iXI3qGg.jpg": "img/catalog/style_options/creative_iXI3qGg.jpg",
    "style_options/elegant.jpg": "img/catalog/style_options/elegant.jpg",
    "style_options/elegant1.png": "img/catalog/style_options/elegant1.png",
    "style_options/minimalis.jpg": "img/catalog/style_options/minimalis.jpg",
    "style_options/natural.jpg": "img/catalog/style_options/natural.jpg",
    "style_options/natural1.jpg": "img/catalog/style_options/natural1.jpg",
    "shared/creative1.png": "img/catalog/shared/creative1.png",
    "shared/minimalis1.webp": "img/catalog/shared/minimalis1.webp",
}

MOTIF_IMAGE_NAMES = (
    "ceplok.png",
    "flora_nusantara.png",
    "kawung.png",
    "kawung_minimal.png",
    "megamendung.png",
    "ondel2.png",
    "parang.png",
    "sekar_jagad.png",
    "semen.png",
    "truntum.png",
)
MOTIF_IMAGE_PATHS = {
    f"recommended_motifs/{name}": f"img/catalog/recommended_motifs/{name}"
    for name in MOTIF_IMAGE_NAMES
}


def move_catalog_references(apps, schema_editor):
    StyleOptions = apps.get_model("batik_custom", "StyleOptions")
    RecommendedMotif = apps.get_model("batik_custom", "RecommendedMotif")
    MotifRecommendation = apps.get_model("batik_custom", "MotifRecommendation")

    for old_path, new_path in STYLE_IMAGE_PATHS.items():
        # Preserve an actual upload if one occupies the same legacy filename.
        if (Path(settings.MEDIA_ROOT) / old_path).is_file():
            continue
        StyleOptions.objects.using(schema_editor.connection.alias).filter(
            image=old_path
        ).update(image=new_path)

    for model in (RecommendedMotif, MotifRecommendation):
        for old_path, new_path in MOTIF_IMAGE_PATHS.items():
            if (Path(settings.MEDIA_ROOT) / old_path).is_file():
                continue
            model.objects.using(schema_editor.connection.alias).filter(
                image=old_path
            ).update(image=new_path)


def restore_catalog_references(apps, schema_editor):
    StyleOptions = apps.get_model("batik_custom", "StyleOptions")
    RecommendedMotif = apps.get_model("batik_custom", "RecommendedMotif")
    MotifRecommendation = apps.get_model("batik_custom", "MotifRecommendation")
    database = schema_editor.connection.alias

    for model, paths in (
        (StyleOptions, STYLE_IMAGE_PATHS),
        (RecommendedMotif, MOTIF_IMAGE_PATHS),
        (MotifRecommendation, MOTIF_IMAGE_PATHS),
    ):
        for old_path, new_path in paths.items():
            rows = model.objects.using(database).filter(image=new_path)
            if not rows.exists():
                continue

            source = Path(settings.BASE_DIR) / "static" / new_path
            destination = Path(settings.MEDIA_ROOT) / old_path
            if source.is_file() and not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            rows.update(image=old_path)


class Migration(migrations.Migration):
    dependencies = [("batik_custom", "0009_merge_20261027_1159")]

    operations = [
        migrations.RunPython(move_catalog_references, restore_catalog_references),
    ]
