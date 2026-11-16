from django.core.management.base import BaseCommand

from batik_custom.catalog_loader import load_catalog


class Command(BaseCommand):
    help = "Muat gaya, palet warna, dan rekomendasi motif ReBatik (aman diulang)."

    def handle(self, *args, **options):
        result = load_catalog(log=self.stdout.write)
        if result["warnings"]:
            self.stderr.write(f"{len(set(result['warnings']))} peringatan, lihat di atas.")
