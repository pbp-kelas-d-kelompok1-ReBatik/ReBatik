# Generated for ReBatik order flow.
import django.conf
import django.db.models.deletion
from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [("batik_custom", "0013_saveddesign"), migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name="BatikOrder", fields=[
        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("style_name", models.CharField(blank=True, max_length=100)), ("design_settings", models.JSONField(blank=True, default=dict)),
        ("product_type", models.CharField(choices=[("fabric", "Kain Batik"), ("shirt", "Kemeja"), ("outer", "Outer")], max_length=20)),
        ("material", models.CharField(max_length=100)), ("quantity", models.PositiveSmallIntegerField(default=1)), ("unit", models.CharField(default="pcs", max_length=20)), ("notes", models.TextField(blank=True)),
        ("recipient_name", models.CharField(max_length=120)), ("phone", models.CharField(max_length=30)), ("address", models.TextField()), ("province", models.CharField(max_length=100)), ("city", models.CharField(max_length=100)), ("district", models.CharField(blank=True, max_length=100)), ("postal_code", models.CharField(max_length=10)),
        ("payment_method", models.CharField(choices=[("bank", "Transfer Bank"), ("ewallet", "E-Wallet"), ("va", "Virtual Account"), ("qris", "QRIS")], max_length=20)),
        ("unit_price", models.PositiveIntegerField(default=250000)), ("total_price", models.PositiveIntegerField(default=250000)),
        ("status", models.CharField(choices=[("pending", "Menunggu konfirmasi"), ("confirmed", "Dikonfirmasi"), ("processing", "Diproses"), ("completed", "Selesai"), ("cancelled", "Dibatalkan")], default="pending", max_length=20)), ("created_at", models.DateTimeField(auto_now_add=True)),
        ("motif", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="batik_custom.recommendedmotif")), ("palette", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="orders", to="batik_custom.colorpalette")), ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="batik_orders", to=django.conf.settings.AUTH_USER_MODEL)),
    ], options={"ordering": ["-created_at"]})]
