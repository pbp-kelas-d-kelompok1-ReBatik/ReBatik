
from django.db import transaction

from .models import FashionPreference


FASHION_PREFERENCES = [
    "Women",
    "Men",
    "Unisex",
]


@transaction.atomic
def load_fashion_preferences():
    """
    Memastikan preferensi fashion tersedia.
    Aman dijalankan berulang kali.
    Tidak menghapus data yang sudah ada.
    """
    preferences = []

    for name in FASHION_PREFERENCES:
        preference, created = FashionPreference.objects.get_or_create(
            name=name
        )
        preferences.append(preference)

    return preferences
