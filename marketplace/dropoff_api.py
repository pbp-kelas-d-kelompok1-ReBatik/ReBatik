"""Dummy Drop-off Point API helpers.

The dataset lives in ``marketplace/data/dropoff_points.json`` so it is versioned
with the repository. Every teammate gets the same data after ``git pull`` and
``python manage.py migrate`` (a data migration seeds the database), and can
consume it either through the JSON endpoint ``/marketplace/api/dropoff-points/``
or directly from Python via :func:`load_dummy_dropoff_points`.
"""

import json
from functools import lru_cache
from pathlib import Path

DUMMY_DROPOFF_DATA_PATH = Path(__file__).resolve().parent / "data" / "dropoff_points.json"
DUMMY_DROPOFF_SOURCE = "rebatik-dummy-dropoff-api"

_FIELDS = (
    "code",
    "name",
    "address",
    "city",
    "province",
    "operating_hours",
    "latitude",
    "longitude",
    "phone",
    "accepted_items",
)


@lru_cache(maxsize=1)
def _read_dataset():
    with DUMMY_DROPOFF_DATA_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    items = payload.get("items", []) if isinstance(payload, dict) else []
    return payload.get("version", "1.0"), tuple(
        item for item in items if isinstance(item, dict) and item.get("code")
    )


def dataset_version():
    """Return the version string declared in the dummy dataset."""
    return _read_dataset()[0]


def load_dummy_dropoff_points():
    """Return a fresh list of normalized drop-off point dictionaries."""
    points = []
    for raw in _read_dataset()[1]:
        point = {field: raw.get(field) for field in _FIELDS}
        accepted = point.get("accepted_items") or []
        point["accepted_items"] = [str(item) for item in accepted]
        point["maps_url"] = (
            f"https://www.google.com/maps?q={point['latitude']},{point['longitude']}"
            if point.get("latitude") is not None and point.get("longitude") is not None
            else None
        )
        points.append(point)
    return points


def filter_dropoff_points(points, *, city="", query=""):
    """Filter dictionaries by exact city (case-insensitive) and free-text query."""
    city = (city or "").strip().lower()
    query = (query or "").strip().lower()
    result = []
    for point in points:
        if city and str(point.get("city", "")).lower() != city:
            continue
        if query:
            haystack = " ".join(
                str(point.get(key, "")) for key in ("name", "address", "city", "province")
            ).lower()
            if query not in haystack:
                continue
        result.append(point)
    return result


def find_dropoff_point(code):
    """Return a single point by its unique code, or ``None``."""
    for point in load_dummy_dropoff_points():
        if point["code"] == code:
            return point
    return None


def model_defaults_from_point(point):
    """Map an API dictionary to ``DropOffPoint`` model field values."""
    return {
        "name": point["name"],
        "address": point["address"],
        "city": point["city"],
        "province": point.get("province") or "",
        "operating_hours": point.get("operating_hours") or "09:00 - 17:00 WIB",
        "latitude": point.get("latitude"),
        "longitude": point.get("longitude"),
        "phone": point.get("phone") or "",
        "accepted_items": ", ".join(point.get("accepted_items") or []),
    }


def sync_dummy_dropoff_points(model=None):
    """Upsert every dummy point into the database. Returns ``(created, updated)``."""
    if model is None:
        from .models import DropOffPoint as model  # noqa: N813

    created = updated = 0
    for point in load_dummy_dropoff_points():
        _, was_created = model.objects.update_or_create(
            code=point["code"],
            defaults=model_defaults_from_point(point),
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return created, updated

