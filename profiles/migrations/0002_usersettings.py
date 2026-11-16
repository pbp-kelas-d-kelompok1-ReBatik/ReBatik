from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_notifications", models.BooleanField(default=True)),
                ("activity_notifications", models.BooleanField(default=True)),
                ("promotional_notifications", models.BooleanField(default=True)),
                ("email_notifications", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="user_settings", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Pengaturan pengguna",
                "verbose_name_plural": "Pengaturan pengguna",
            },
        ),
    ]
