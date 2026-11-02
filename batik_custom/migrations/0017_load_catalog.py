from django.db import migrations


def load_catalog_forward(apps, schema_editor):
    """Isi katalog otomatis saat ``migrate`` (tidak perlu shell di PWS)."""
    from batik_custom.catalog_loader import load_catalog

    try:
        load_catalog(apps=apps, using=schema_editor.connection.alias)
    except Exception as exc:  # jangan sampai deploy gagal total
        print(f"[batik_custom] load_catalog gagal: {exc!r}. "
              "Jalankan: python manage.py load_catalog")


class Migration(migrations.Migration):
    dependencies = [("batik_custom", "0016_merge_20261030_0005")]

    operations = [migrations.RunPython(load_catalog_forward, migrations.RunPython.noop)]
