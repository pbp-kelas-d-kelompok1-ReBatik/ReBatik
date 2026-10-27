from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import default_storage
from django.utils._os import safe_join

from config.storage_backends import CloudinaryMediaStorage


class Command(BaseCommand):
    help = "Move existing local ImageField files and references to Cloudinary."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Check for local files without uploading or changing records.",
        )

    def handle(self, *args, **options):
        if not settings.PRODUCTION or not isinstance(
            default_storage, CloudinaryMediaStorage
        ):
            raise CommandError(
                "Run this command with PRODUCTION=True and Cloudinary configured."
            )

        pending = []
        missing = []
        for model in apps.get_models():
            for field in model._meta.fields:
                if field.get_internal_type() != "FileField":
                    continue

                for instance in model.objects.exclude(
                    **{field.name: ""}
                ).iterator():
                    old_name = getattr(instance, field.name).name
                    if not old_name or old_name.startswith("cloudinary:"):
                        continue

                    # These are bundled static assets, not MEDIA_ROOT uploads.
                    if old_name.startswith("img/catalog/"):
                        continue

                    try:
                        source_path = Path(safe_join(settings.MEDIA_ROOT, old_name))
                    except SuspiciousFileOperation:
                        missing.append(f"{model._meta.label}#{instance.pk}: {old_name}")
                        continue

                    if not source_path.is_file():
                        missing.append(f"{model._meta.label}#{instance.pk}: {old_name}")
                        continue
                    pending.append((instance, field.name, old_name, source_path))

        if missing:
            preview = "\n".join(missing[:20])
            remainder = len(missing) - min(len(missing), 20)
            if remainder:
                preview += f"\n... and {remainder} more"
            raise CommandError(
                "Some legacy media files are missing from MEDIA_ROOT; "
                "no uploads were started. Restore or otherwise resolve these "
                f"files first:\n{preview}"
            )

        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Preflight passed: {len(pending)} local image/file record(s) "
                    "can be migrated. No changes made."
                )
            )
            return

        for instance, field_name, old_name, source_path in pending:
            with source_path.open("rb") as source:
                cloudinary_name = default_storage.save(old_name, File(source))
            setattr(instance, field_name, cloudinary_name)
            instance.save(update_fields=[field_name])

        self.stdout.write(
            self.style.SUCCESS(
                f"Migrated {len(pending)} local image/file record(s) to Cloudinary."
            )
        )
