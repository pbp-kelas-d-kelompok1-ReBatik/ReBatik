from django.db import migrations


IMAGE_PATHS = {
    "batik/parang.png": "batik/parang.webp",
    "batik/megamendung.png": "batik/megamendung.webp",
    "shared/minimalis1.png": "shared/minimalis1.webp",
}
REVERSE_IMAGE_PATHS = {
    "batik/parang.webp": "batik/parang.png",
    "batik/megamendung.webp": "batik/megamendung.png",
    "shared/minimalis1.webp": "shared/minimalis1.png",
}


def convert_motif_images(apps, schema_editor):
    BatikMotif = apps.get_model("batik_story", "BatikMotif")
    for old_path, new_path in IMAGE_PATHS.items():
        BatikMotif.objects.filter(gambar=old_path).update(gambar=new_path)


def restore_motif_image_extensions(apps, schema_editor):
    BatikMotif = apps.get_model("batik_story", "BatikMotif")
    for new_path, old_path in REVERSE_IMAGE_PATHS.items():
        BatikMotif.objects.filter(gambar=new_path).update(gambar=old_path)


class Migration(migrations.Migration):
    dependencies = [("batik_story", "0003_deduplicate_motif_images")]

    operations = [
        migrations.RunPython(convert_motif_images, restore_motif_image_extensions),
    ]
