from pathlib import Path
import shutil

from django.conf import settings
from django.db import migrations


IMAGE_PATHS = {
    "batik/parang.webp": "img/catalog/batik/parang.webp",
    "batik/ondel2.png": "img/catalog/batik/ondel2.png",
    "batik/megamendung.webp": "img/catalog/batik/megamendung.webp",
    "batik/kawung.webp": "img/catalog/batik/kawung.webp",
    "shared/creative1.png": "img/catalog/shared/creative1.png",
    "shared/minimalis1.webp": "img/catalog/shared/minimalis1.webp",
}


def move_catalog_references(apps, schema_editor):
    BatikMotif = apps.get_model("batik_story", "BatikMotif")
    database = schema_editor.connection.alias
    for old_path, new_path in IMAGE_PATHS.items():
        # Preserve an actual upload if one occupies the same legacy filename.
        if (Path(settings.MEDIA_ROOT) / old_path).is_file():
            continue
        BatikMotif.objects.using(database).filter(gambar=old_path).update(
            gambar=new_path
        )


def restore_catalog_references(apps, schema_editor):
    BatikMotif = apps.get_model("batik_story", "BatikMotif")
    database = schema_editor.connection.alias
    for old_path, new_path in IMAGE_PATHS.items():
        rows = BatikMotif.objects.using(database).filter(gambar=new_path)
        if not rows.exists():
            continue

        source = Path(settings.BASE_DIR) / "static" / new_path
        destination = Path(settings.MEDIA_ROOT) / old_path
        if source.is_file() and not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        rows.update(gambar=old_path)


class Migration(migrations.Migration):
    dependencies = [("batik_story", "0005_merge_20261027_1200")]

    operations = [
        migrations.RunPython(move_catalog_references, restore_catalog_references),
    ]
