from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("rewards", "0005_reward_image"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="reward",
            options={
                "ordering": ["points_required", "name"],
                "verbose_name": "voucher",
                "verbose_name_plural": "katalog voucher",
            },
        ),
    ]
