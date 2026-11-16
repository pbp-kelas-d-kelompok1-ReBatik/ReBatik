from django.db import migrations, models


ITEM_FORM_MAP = (
    ("celana", "PANTS"),
    ("kaos", "TOP"),
    ("kemeja", "TOP"),
    ("jaket", "JACKET"),
    ("outer", "JACKET"),
    ("potongan", "FABRIC"),
    ("kain", "FABRIC"),
)


def migrate_item_form_values(apps, schema_editor):
    request_model = apps.get_model("upcycling", "UpcyclingRequest")
    for request in request_model.objects.exclude(current_item_form="").iterator():
        previous_value = request.current_item_form
        normalized_value = previous_value.casefold()
        item_form = next(
            (code for keyword, code in ITEM_FORM_MAP if keyword in normalized_value),
            "OTHER",
        )
        request.current_item_form = item_form
        if item_form == "OTHER":
            request.current_item_form_other = previous_value
        request.save(update_fields=["current_item_form", "current_item_form_other"])


def restore_item_form_values(apps, schema_editor):
    request_model = apps.get_model("upcycling", "UpcyclingRequest")
    labels = {
        "PANTS": "Celana",
        "TOP": "Kaos / Kemeja",
        "JACKET": "Jaket / Outer",
        "FABRIC": "Kain lembaran / Potongan kain",
    }
    for request in request_model.objects.exclude(current_item_form="").iterator():
        request.current_item_form = (
            request.current_item_form_other
            if request.current_item_form == "OTHER"
            else labels.get(request.current_item_form, request.current_item_form)
        )
        request.current_item_form_other = ""
        request.save(update_fields=["current_item_form", "current_item_form_other"])


class Migration(migrations.Migration):

    dependencies = [
        ("upcycling", "0018_upcyclingrequest_current_item_form_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="upcyclingrequest",
            name="current_item_form_other",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.RunPython(migrate_item_form_values, restore_item_form_values),
        migrations.AlterField(
            model_name="upcyclingrequest",
            name="current_item_form",
            field=models.CharField(
                blank=True,
                choices=[
                    ("PANTS", "Celana"),
                    ("TOP", "Kaos / Kemeja"),
                    ("JACKET", "Jaket / Outer"),
                    ("FABRIC", "Kain lembaran / Potongan kain"),
                    ("OTHER", "Lainnya"),
                ],
                max_length=20,
            ),
        ),
    ]
