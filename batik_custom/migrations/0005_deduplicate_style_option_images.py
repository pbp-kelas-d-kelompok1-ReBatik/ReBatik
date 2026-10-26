from django.db import migrations


IMAGE_PATHS = {
    "style_options/minimalis1.png": "shared/minimalis1.png",
    "style_options/creative1.png": "shared/creative1.png",
    "style_options/elegant1_7qR7h9S.png": "style_options/elegant1.png",
}


def deduplicate_style_images(apps, schema_editor):
    StyleOptions = apps.get_model("batik_custom", "StyleOptions")
    for old_path, new_path in IMAGE_PATHS.items():
        StyleOptions.objects.filter(image=old_path).update(image=new_path)


class Migration(migrations.Migration):
    dependencies = [("batik_custom", "0004_alter_styleoptions_name")]

    operations = [
        # Old duplicate files are removed, and multiple source paths can share
        # one destination. Reversing these image references would be unsafe.
        migrations.RunPython(deduplicate_style_images),
    ]
