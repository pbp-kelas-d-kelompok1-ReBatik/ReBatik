from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0002_order_orderstatushistory_alter_dropoffpoint_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="dropoffpoint",
            name="code",
            field=models.SlugField(blank=True, max_length=60, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="dropoffpoint",
            name="province",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="dropoffpoint",
            name="phone",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="dropoffpoint",
            name="accepted_items",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]

