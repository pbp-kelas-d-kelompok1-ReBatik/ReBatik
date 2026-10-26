from django.db import migrations


IMAGE_PATHS = {
    "shared/minimalis1.png": "shared/minimalis1.webp",
    "style_options/casual1.png": "style_options/casual1.webp",
}
REVERSE_IMAGE_PATHS = {
    "shared/minimalis1.webp": "shared/minimalis1.png",
    "style_options/casual1.webp": "style_options/casual1.png",
}


def convert_style_images(apps, schema_editor):
    StyleOptions = apps.get_model("batik_custom", "StyleOptions")
    for old_path, new_path in IMAGE_PATHS.items():
        StyleOptions.objects.filter(image=old_path).update(image=new_path)


def restore_style_image_extensions(apps, schema_editor):
    StyleOptions = apps.get_model("batik_custom", "StyleOptions")
    for new_path, old_path in REVERSE_IMAGE_PATHS.items():
        StyleOptions.objects.filter(image=new_path).update(image=old_path)


class Migration(migrations.Migration):
    dependencies = [("batik_custom", "0005_deduplicate_style_option_images")]

    operations = [
        migrations.RunPython(convert_style_images, restore_style_image_extensions),
    ]
