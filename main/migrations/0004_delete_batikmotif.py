
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_remove_batikmotif_favorit'),
    ]

    operations = [
    migrations.DeleteModel(name='BatikMotif',)
    ]
