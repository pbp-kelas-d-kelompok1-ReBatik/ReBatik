
import uuid
from django.db import migrations, models


def generate_story_uuids(apps, schema_editor):
    BatikMotif = apps.get_model("batik_story", "BatikMotif")

    for batik in BatikMotif.objects.filter(id_story__isnull=True).iterator():
        batik.id_story = uuid.uuid4()
        batik.save(update_fields=["id_story"])


class Migration(migrations.Migration):

    dependencies = [
        ("batik_story", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="BatikMotif",
            name="id_story",
            field=models.UUIDField(
                blank=True,
                null=True,
                editable=False,
            ),
        ),
        migrations.RunPython(
            generate_story_uuids,
            migrations.RunPython.noop,
        ),
    ]
