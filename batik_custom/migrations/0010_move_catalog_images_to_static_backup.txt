from pathlib import Path
import filecmp
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
ROLLBACK_MEDIA_PREFIX = "_catalog_rollback/"


def move_restored_references(queryset, field_name, new_path):
    rollback_path = f"{ROLLBACK_MEDIA_PREFIX}{new_path}"
    rows = queryset.filter(**{field_name: rollback_path})
    if not rows.exists():
        return

    rows.update(**{field_name: new_path})
    restored_copy = Path(settings.MEDIA_ROOT) / rollback_path
    if restored_copy.is_file():
        restored_copy.unlink()


def move_catalog_references(apps, schema_editor):
    StyleOptions = apps.get_model("batik_custom", "StyleOptions")
    RecommendedMotif = apps.get_model("batik_custom", "RecommendedMotif")
    MotifRecommendation = apps.get_model("batik_custom", "MotifRecommendation")

    database = schema_editor.connection.alias
    for model, paths in (
        (StyleOptions, STYLE_IMAGE_PATHS),
        (RecommendedMotif, MOTIF_IMAGE_PATHS),
        (MotifRecommendation, MOTIF_IMAGE_PATHS),
    ):
        model = model.objects.using(database)
        for old_path, new_path in paths.items():
            move_restored_references(model, "image", new_path)
            # Preserve an actual upload if one occupies the same legacy filename.
            if (Path(settings.MEDIA_ROOT) / old_path).is_file():
                continue
            model.filter(image=old_path).update(image=new_path)


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
            rollback_path = f"{ROLLBACK_MEDIA_PREFIX}{new_path}"
            destination = Path(settings.MEDIA_ROOT) / rollback_path
            if not source.is_file():
                raise RuntimeError(f"Cannot restore missing catalog image: {source}")
            if destination.exists() and not filecmp.cmp(source, destination, shallow=False):
                raise RuntimeError(f"Rollback image path is occupied: {destination}")
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            rows.update(image=rollback_path)


class Migration(migrations.Migration):
    dependencies = [("batik_custom", "0009_merge_20261027_1159")]

    operations = [
        migrations.RunPython(move_catalog_references, restore_catalog_references),
    ]
