from django.core.management.base import BaseCommand

from marketplace.dropoff_api import DUMMY_DROPOFF_DATA_PATH, sync_dummy_dropoff_points


class Command(BaseCommand):
    help = "Sinkronkan data dummy Drop-off Point (marketplace/data/dropoff_points.json) ke database."

    def handle(self, *args, **options):
        created, updated = sync_dummy_dropoff_points()
        self.stdout.write(
            self.style.SUCCESS(
                f"Drop-off Point tersinkron dari {DUMMY_DROPOFF_DATA_PATH.name}: "
                f"{created} baru, {updated} diperbarui."
            )
        )

