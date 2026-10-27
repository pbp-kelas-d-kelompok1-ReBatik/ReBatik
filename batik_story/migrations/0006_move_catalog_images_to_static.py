from pathlib import Path
import filecmp
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
ROLLBACK_MEDIA_PREFIX = "_catalog_rollback/"


def move_catalog_references(apps, schema_editor):
    BatikMotif = apps.get_model("batik_story", "BatikMotif")
    database = schema_editor.connection.alias
    for old_path, new_path in IMAGE_PATHS.items():
        rollback_path = f"{ROLLBACK_MEDIA_PREFIX}{new_path}"
        restored_rows = BatikMotif.objects.using(database).filter(gambar=rollback_path)
        if restored_rows.exists():
            restored_rows.update(gambar=new_path)
            restored_copy = Path(settings.MEDIA_ROOT) / rollback_path
            if restored_copy.is_file():
                restored_copy.unlink()

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
        rollback_path = f"{ROLLBACK_MEDIA_PREFIX}{new_path}"
        destination = Path(settings.MEDIA_ROOT) / rollback_path
        if not source.is_file():
            raise RuntimeError(f"Cannot restore missing catalog image: {source}")
        if destination.exists() and not filecmp.cmp(source, destination, shallow=False):
            raise RuntimeError(f"Rollback image path is occupied: {destination}")
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        rows.update(gambar=rollback_path)


class Migration(migrations.Migration):
    dependencies = [("batik_story", "0005_merge_20261027_1200")]

    operations = [
        migrations.RunPython(move_catalog_references, restore_catalog_references),
    ]
