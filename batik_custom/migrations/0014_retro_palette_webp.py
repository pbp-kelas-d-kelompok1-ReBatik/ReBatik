from django.db import migrations


def migrate_retro_palette_path(apps, schema_editor):
    ColorPalette = apps.get_model("batik_custom", "ColorPalette")
    ColorPalette.objects.using(schema_editor.connection.alias).filter(
        image="img/catalog/colorpalette/retro.png"
    ).update(image="img/catalog/colorpalette/retro.webp")


class Migration(migrations.Migration):
    dependencies = [("batik_custom", "0013_fix_catalog_image_paths")]

    operations = [
        migrations.RunPython(migrate_retro_palette_path, migrations.RunPython.noop),
    ]
