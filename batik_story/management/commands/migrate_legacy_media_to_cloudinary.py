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

        migrated = 0
        failed = 0
        for instance, field_name, old_name, source_path in pending:
            record = f"{instance._meta.label}#{instance.pk}.{field_name}"
            cloudinary_name = None
            try:
                with source_path.open("rb") as source:
                    cloudinary_name = default_storage.save(old_name, File(source))
            except Exception as error:
                failed += 1
                self.stderr.write(
                    self.style.ERROR(f"Failed to upload {record}: {error}")
                )
                continue

            try:
                updated = instance.__class__.objects.filter(
                    pk=instance.pk,
                    **{field_name: old_name},
                ).update(**{field_name: cloudinary_name})
            except Exception as error:
                failed += 1
                try:
                    default_storage.delete(cloudinary_name)
                except Exception as cleanup_error:
                    error = f"{error}; cleanup failed: {cleanup_error}"
                self.stderr.write(
                    self.style.ERROR(f"Failed to update {record}: {error}")
                )
                continue

            if not updated:
                failed += 1
                try:
                    default_storage.delete(cloudinary_name)
                except Exception as error:
                    self.stderr.write(
                        self.style.ERROR(
                            f"Could not remove unused upload for {record}: {error}"
                        )
                    )
                self.stderr.write(
                    self.style.ERROR(
                        f"Skipped {record}: its stored file changed after preflight."
                    )
                )
                continue

            migrated += 1

        if failed:
            self.stdout.write(
                f"Migrated {migrated} local image/file record(s) to Cloudinary."
            )
            raise CommandError(
                f"{failed} record(s) failed or changed during migration; "
                "see errors above and rerun after resolving them."
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Migrated {migrated} local image/file record(s) to Cloudinary."
            )
        )
