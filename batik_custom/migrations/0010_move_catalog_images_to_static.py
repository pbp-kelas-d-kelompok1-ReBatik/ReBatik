
from pathlib import Path
import filecmp
import shutil

from django.conf import settings
from django.db import migrations


STYLE_IMAGE_PATHS = {
    "style_options/bohemian.jpe": "img/catalog/style_options/bohemian.jpe",
    "style_options/bohemian1.jpg": "img/catalog/style_options/bohemian1.jpg",
    "style_options/casual.jpe": "img/catalog/style_options/casual.jpe",
    "style_options/casual1.webp": "img/catalog/style_options/casual1.webp",
    "style_options/creative.jpg": "img/catalog/style_options/creative.jpg",
    "style_options/creative_iXI3qGg.jpg": "img/catalog/style_options/creative_iXI3qGg.jpg",
    "style_options/elegant.jpg": "img/catalog/style_options/elegant.jpg",
    "style_options/elegant1.png": "img/catalog/style_options/elegant1.png",
    "style_options/minimalis.jpg": "img/catalog/style_options/minimalis.jpg",
    "style_options/natural.jpg": "img/catalog/style_options/natural.jpg",
    "style_options/natural1.jpg": "img/catalog/style_options/natural1.jpg",
    "shared/creative1.png": "img/catalog/shared/creative1.png",
    "shared/minimalis1.webp": "img/catalog/shared/minimalis1.webp",
}

MOTIF_IMAGE_NAMES = (
    "ceplok.png",
    "flora_nusantara.png",
    "kawung.png",
    "kawung_minimal.png",
    "megamendung.png",
    "ondel2.png",
    "parang.png",
    "sekar_jagad.png",
    "semen.png",
    "truntum.png",
)

MOTIF_IMAGE_PATHS = {
    f"recommended_motifs/{name}":
        f"img/catalog/recommended_motifs/{name}"
    for name in MOTIF_IMAGE_NAMES
}

ROLLBACK_MEDIA_PREFIX = "_catalog_rollback"


def media_path(relative_path):
    """Resolve a relative path inside MEDIA_ROOT."""
    return Path(settings.MEDIA_ROOT) / relative_path


def static_path(relative_path):
    """Resolve a catalog image in the project's static directory."""
    return Path(settings.BASE_DIR) / "static" / relative_path


def move_restored_references(queryset, field_name, new_path):
    """
    Restore references previously placed in the rollback directory.
    The temporary file is deleted only after database references
    have been updated successfully.
    """
    rollback_path = f"{ROLLBACK_MEDIA_PREFIX}/{new_path}"

    rows = queryset.filter(**{field_name: rollback_path})

    if not rows.exists():
        return

    source = static_path(new_path)

    if not source.is_file():
        raise RuntimeError(
            f"Catalog image does not exist: {source}"
        )

    rows.update(**{field_name: new_path})

    restored_copy = media_path(rollback_path)

    if restored_copy.is_file():
        restored_copy.unlink()


def move_catalog_references(apps, schema_editor):
    """
    Forward migration:
    Move database references to static catalog images only when
    the original media file is missing.
    """
    StyleOptions = apps.get_model("batik_custom", "StyleOptions")
    RecommendedMotif = apps.get_model(
        "batik_custom", "RecommendedMotif"
    )

    database = schema_editor.connection.alias

    models_and_paths = (
        (StyleOptions, STYLE_IMAGE_PATHS),
        (RecommendedMotif, MOTIF_IMAGE_PATHS),
    )

    for model_class, paths in models_and_paths:
        queryset = model_class.objects.using(database)

        for old_path, new_path in paths.items():
            # Recover references left by an earlier rollback.
            move_restored_references(
                queryset, "image", new_path
            )

            old_file = media_path(old_path)

            # Keep existing uploaded media files unchanged.
            if old_file.is_file():
                continue

            new_file = static_path(new_path)

            # Never update the database to a missing image.
            if not new_file.is_file():
                raise RuntimeError(
                    "Cannot migrate catalog image reference. "
                    f"Original media is missing: {old_file}; "
                    f"static image is missing: {new_file}"
                )

            queryset.filter(image=old_path).update(
                image=new_path
            )


def restore_catalog_references(apps, schema_editor):
    """
    Reverse migration:
    Copy static images into MEDIA_ROOT before changing references,
    so the referenced files continue to exist after rollback.
    """
    StyleOptions = apps.get_model("batik_custom", "StyleOptions")
    RecommendedMotif = apps.get_model(
        "batik_custom", "RecommendedMotif"
    )

    database = schema_editor.connection.alias

    models_and_paths = (
        (StyleOptions, STYLE_IMAGE_PATHS),
        (RecommendedMotif, MOTIF_IMAGE_PATHS),
    )

    for model_class, paths in models_and_paths:
        queryset = model_class.objects.using(database)

        for old_path, new_path in paths.items():
            rows = queryset.filter(image=new_path)

            if not rows.exists():
                continue

            source = static_path(new_path)
            rollback_path = (
                f"{ROLLBACK_MEDIA_PREFIX}/{new_path}"
            )
            destination = media_path(rollback_path)

            if not source.is_file():
                raise RuntimeError(
                    "Cannot reverse catalog migration: "
                    f"static image is missing: {source}"
                )

            # Check before changing any database references.
            if destination.exists():
                if not filecmp.cmp(
                    source, destination, shallow=False
                ):
                    raise RuntimeError(
                        "Rollback destination contains a "
                        f"different file: {destination}"
                    )
            else:
                destination.parent.mkdir(
                    parents=True, exist_ok=True
                )
                shutil.copy2(source, destination)

            # Update only after the rollback copy is available.
            rows.update(image=rollback_path)


class Migration(migrations.Migration):
    dependencies = [
        ("batik_custom", "0009_merge_20261027_1159"),
    ]

    operations = [
        migrations.RunPython(
            move_catalog_references,
            restore_catalog_references,
        ),
    ]
