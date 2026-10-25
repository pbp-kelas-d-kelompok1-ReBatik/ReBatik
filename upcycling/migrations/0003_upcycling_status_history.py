from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def record_existing_statuses(apps, schema_editor):
    UpcyclingRequest = apps.get_model("upcycling", "UpcyclingRequest")
    UpcyclingStatusHistory = apps.get_model("upcycling", "UpcyclingStatusHistory")
    database = schema_editor.connection.alias
    UpcyclingStatusHistory.objects.using(database).bulk_create(
        [
            UpcyclingStatusHistory(
                request_id=request.pk,
                from_status="",
                to_status=request.status,
            )
            for request in UpcyclingRequest.objects.using(database).only(
                "pk",
                "status",
            )
        ],
        batch_size=500,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("upcycling", "0002_align_upcycling_choice_labels"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UpcyclingStatusHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "from_status",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("PENDING", "Menunggu Tinjauan"),
                            ("PROCESSING", "Diproses"),
                            ("COMPLETED", "Selesai"),
                            ("CANCELLED", "Dibatalkan"),
                        ],
                        max_length=12,
                    ),
                ),
                (
                    "to_status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Menunggu Tinjauan"),
                            ("PROCESSING", "Diproses"),
                            ("COMPLETED", "Selesai"),
                            ("CANCELLED", "Dibatalkan"),
                        ],
                        max_length=12,
                    ),
                ),
                (
                    "changed_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="upcycling_status_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_history",
                        to="upcycling.upcyclingrequest",
                    ),
                ),
            ],
            options={
                "verbose_name": "riwayat status permintaan upcycling",
                "verbose_name_plural": "riwayat status permintaan upcycling",
                "ordering": ["changed_at", "pk"],
            },
        ),
        migrations.RunPython(record_existing_statuses, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="upcyclingrequest",
            index=models.Index(
                fields=["user", "status", "-created_at"],
                name="upreq_user_status_created_idx",
            ),
        ),
    ]
