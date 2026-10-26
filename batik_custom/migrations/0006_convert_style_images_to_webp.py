from django.db import migrations


IMAGE_PATHS = {
    "shared/minimalis1.png": "shared/minimalis1.webp",
    "style_options/casual1.png": "style_options/casual1.webp",
}


def convert_style_images(apps, schema_editor):
    StyleOptions = apps.get_model("batik_custom", "StyleOptions")
    for old_path, new_path in IMAGE_PATHS.items():
        StyleOptions.objects.filter(image=old_path).update(image=new_path)


class Migration(migrations.Migration):
    dependencies = [("batik_custom", "0005_deduplicate_style_option_images")]

    operations = [
        # The source PNGs were removed after conversion, so this operation
        # cannot safely restore their file references on rollback.
        migrations.RunPython(convert_style_images),
    ]
