"""Seed the dummy Drop-off Point dataset so every teammate gets it via `migrate`."""

import json
from pathlib import Path

from django.db import migrations

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "dropoff_points.json"


def seed_dropoff_points(apps, schema_editor):
    DropOffPoint = apps.get_model("marketplace", "DropOffPoint")
    if not DATA_PATH.exists():
        return
    with DATA_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    for point in payload.get("items", []):
        if not isinstance(point, dict) or not point.get("code"):
            continue
        DropOffPoint.objects.update_or_create(
            code=point["code"],
            defaults={
                "name": point["name"],
                "address": point["address"],
                "city": point["city"],
                "province": point.get("province") or "",
                "operating_hours": point.get("operating_hours") or "09:00 - 17:00 WIB",
                "latitude": point.get("latitude"),
                "longitude": point.get("longitude"),
                "phone": point.get("phone") or "",
                "accepted_items": ", ".join(point.get("accepted_items") or []),
            },
        )


def unseed_dropoff_points(apps, schema_editor):
    DropOffPoint = apps.get_model("marketplace", "DropOffPoint")
    DropOffPoint.objects.filter(code__startswith="rbt-", orders__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0003_dropoffpoint_api_fields"),
    ]

    operations = [
        migrations.RunPython(seed_dropoff_points, unseed_dropoff_points),
    ]

