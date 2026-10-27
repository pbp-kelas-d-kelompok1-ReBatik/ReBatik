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


def deduplicate_motif_images(apps, schema_editor):
    BatikMotif = apps.get_model("batik_story", "BatikMotif")
    for old_path, new_path in IMAGE_PATHS.items():
        BatikMotif.objects.filter(gambar=old_path).update(gambar=new_path)


class Migration(migrations.Migration):
    dependencies = [("batik_story", "0002_batikmotif_id_story")]

    operations = [
        # Multiple deleted image paths can collapse to one target, so restoring
        # the prior per-row filename would require keeping an audit of old paths.
        migrations.RunPython(deduplicate_motif_images),
    ]
