from django.db import migrations


IMAGE_PATHS = {
    "style_options/minimalis1.png": "shared/minimalis1.png",
    "style_options/creative1.png": "shared/creative1.png",
    "style_options/elegant1_7qR7h9S.png": "style_options/elegant1.png",
}
REVERSE_IMAGE_PATHS = {
    "shared/minimalis1.png": "style_options/minimalis1.png",
    "shared/creative1.png": "style_options/creative1.png",
    "style_options/elegant1.png": "style_options/elegant1_7qR7h9S.png",
}


def deduplicate_style_images(apps, schema_editor):
    StyleOptions = apps.get_model("batik_custom", "StyleOptions")
    for old_path, new_path in IMAGE_PATHS.items():
        StyleOptions.objects.filter(image=old_path).update(image=new_path)


def restore_style_image_paths(apps, schema_editor):
    StyleOptions = apps.get_model("batik_custom", "StyleOptions")
    for new_path, old_path in REVERSE_IMAGE_PATHS.items():
        StyleOptions.objects.filter(image=new_path).update(image=old_path)


class Migration(migrations.Migration):
    dependencies = [("batik_custom", "0004_alter_styleoptions_name")]

    operations = [
        migrations.RunPython(deduplicate_style_images, restore_style_image_paths),
    ]
