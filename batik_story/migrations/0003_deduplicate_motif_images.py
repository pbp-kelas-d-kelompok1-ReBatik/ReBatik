from django.db import migrations


IMAGE_PATHS = {
    "batik/parang_yoMvvLE.png": "batik/parang.png",
    "batik/ondel2_2RuT1tx.png": "batik/ondel2.png",
    "batik/megamendung_Sht7s4M.png": "batik/megamendung.png",
    "batik/creative1.png": "shared/creative1.png",
    "batik/creative1_9ueFUyz.png": "shared/creative1.png",
    "batik/creative1_fN29Rb1.png": "shared/creative1.png",
    "batik/minimalis1.png": "shared/minimalis1.png",
    "batik_story/batik/Batik_Parang.png": "batik/parang.png",
}
REVERSE_IMAGE_PATHS = {
    "batik/parang.png": "batik/parang.png",
    "batik/ondel2.png": "batik/ondel2.png",
    "batik/megamendung.png": "batik/megamendung.png",
    "shared/creative1.png": "batik/creative1.png",
    "shared/minimalis1.png": "batik/minimalis1.png",
}


def deduplicate_motif_images(apps, schema_editor):
    BatikMotif = apps.get_model("batik_story", "BatikMotif")
    for old_path, new_path in IMAGE_PATHS.items():
        BatikMotif.objects.filter(gambar=old_path).update(gambar=new_path)


def restore_motif_image_paths(apps, schema_editor):
    BatikMotif = apps.get_model("batik_story", "BatikMotif")
    for new_path, old_path in REVERSE_IMAGE_PATHS.items():
        BatikMotif.objects.filter(gambar=new_path).update(gambar=old_path)


class Migration(migrations.Migration):
    dependencies = [("batik_story", "0002_batikmotif_id_story")]

    operations = [
        migrations.RunPython(deduplicate_motif_images, restore_motif_image_paths),
    ]
