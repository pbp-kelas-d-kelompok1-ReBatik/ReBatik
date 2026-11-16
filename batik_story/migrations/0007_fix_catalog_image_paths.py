from pathlib import Path

from django.conf import settings
from django.db import migrations


IMAGE_PATHS = {
    "batik/parang.webp": "img/catalog/batik/parang.webp",
    "batik/ondel2.png": "img/catalog/batik/ondel2.png",
    "batik/megamendung.webp": "img/catalog/batik/megamendung.webp",
    "img/catalog/batik/ondel2.png": "img/catalog/batik/ondel2.png",
    "shared/creative1.png": "img/catalog/style_options/creative1.png",
    "img/catalog/shared/creative1.png": "img/catalog/style_options/creative1.png",
    "shared/minimalis1.webp": "img/catalog/style_options/minimalis1.png",
    "img/catalog/shared/minimalis1.webp": "img/catalog/style_options/minimalis1.png",
}


def fix_image_paths(apps, schema_editor):
    BatikMotif = apps.get_model("batik_story", "BatikMotif")
    queryset = BatikMotif.objects.using(schema_editor.connection.alias)
    for old_path, new_path in IMAGE_PATHS.items():
        # Keep a user's upload when it occupies a legacy catalog filename.
        if not old_path.startswith("img/catalog/") and (
            Path(settings.MEDIA_ROOT) / old_path
        ).is_file():
            continue
        queryset.filter(gambar=old_path).update(gambar=new_path)


class Migration(migrations.Migration):
    dependencies = [("batik_story", "0006_move_catalog_images_to_static")]

    operations = [migrations.RunPython(fix_image_paths, migrations.RunPython.noop)]
