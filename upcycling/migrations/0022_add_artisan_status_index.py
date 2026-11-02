from django.db import migrations, models


INDEX = models.Index(
    fields=["artisan", "status"],
    name="upreq_artisan_status_idx",
)


def ensure_artisan_status_index(apps, schema_editor):
    UpcyclingRequest = apps.get_model("upcycling", "UpcyclingRequest")
    table_name = UpcyclingRequest._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(
            cursor, table_name
        )
    if INDEX.name not in constraints:
        schema_editor.add_index(UpcyclingRequest, INDEX)


def remove_artisan_status_index(apps, schema_editor):
    UpcyclingRequest = apps.get_model("upcycling", "UpcyclingRequest")
    table_name = UpcyclingRequest._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(
            cursor, table_name
        )
    if INDEX.name in constraints:
        schema_editor.remove_index(UpcyclingRequest, INDEX)


class Migration(migrations.Migration):
    dependencies = [
        ("upcycling", "0021_upcyclingrequest_additional_fee_amount_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    ensure_artisan_status_index,
                    remove_artisan_status_index,
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="upcyclingrequest",
                    index=INDEX,
                ),
            ],
        ),
    ]
