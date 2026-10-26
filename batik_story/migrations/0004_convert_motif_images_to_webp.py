from django.db import migrations


IMAGE_PATHS = {
    "batik/parang.png": "batik/parang.webp",
    "batik/megamendung.png": "batik/megamendung.webp",
    "shared/minimalis1.png": "shared/minimalis1.webp",
}


def convert_motif_images(apps, schema_editor):
    BatikMotif = apps.get_model("batik_story", "BatikMotif")
    for old_path, new_path in IMAGE_PATHS.items():
        BatikMotif.objects.filter(gambar=old_path).update(gambar=new_path)


class Migration(migrations.Migration):
    dependencies = [("batik_story", "0003_deduplicate_motif_images")]

    operations = [
        # The converted PNG files are no longer present, so this migration is
        # intentionally irreversible rather than restoring broken PNG paths.
        migrations.RunPython(convert_motif_images),
    ]
