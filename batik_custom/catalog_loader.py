"""Memuat katalog ReBatik (gaya, palet warna, dan rekomendasi motif).

Sumber data (semuanya di folder ``batik_custom/data``):
  * catalog.json            -> 18 gaya + 24 palet warna (path gambar = static)
  * recommended_motifs.json -> rekomendasi motif (ringkas, ~60 KB)

Aman dijalankan berulang kali (idempotent). Dipakai oleh:
  * migrasi 0017_load_catalog   -> otomatis saat ``migrate`` (deploy PWS)
  * python manage.py load_catalog -> manual kapan pun dibutuhkan
"""

import json
from pathlib import Path

from django.db import transaction

DATA_DIR = Path(__file__).resolve().parent / "data"
UPLOAD_PREFIX = "cloudinary:"  # gambar hasil upload admin tidak ditimpa


def _read(name):
    with (DATA_DIR / name).open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def _norm(value):
    return " ".join(str(value).replace("\u2014", "-").replace("\u2013", "-").split()).casefold()


def _base(value):
    """'Elegant — Klasik dan Berkelas' -> 'elegant'."""
    return _norm(value).split(" - ")[0].strip()


def _keep_upload(current):
    return str(current or "").startswith(UPLOAD_PREFIX)


def _set_links(Motif, field_name, using, links):
    """Ganti isi relasi M2M untuk banyak motif sekaligus (hemat query)."""
    field = Motif._meta.get_field(field_name)
    through = field.remote_field.through
    own, other = field.m2m_field_name(), field.m2m_reverse_field_name()
    through.objects.using(using).filter(**{f"{own}_id__in": list(links)}).delete()
    rows = [
        through(**{f"{own}_id": motif_id, f"{other}_id": target_id})
        for motif_id, targets in links.items()
        for target_id in dict.fromkeys(targets)
    ]
    through.objects.using(using).bulk_create(rows, batch_size=500)


def _referenced_motif_ids(Motif, using, ids):
    """Motif yang dipakai desain/pesanan tidak boleh dihapus."""
    used = set()
    for rel in Motif._meta.related_objects:
        if rel.many_to_many or rel.related_model is Motif:
            continue
        used.update(
            rel.related_model._default_manager.using(using)
            .filter(**{f"{rel.field.name}__in": ids})
            .values_list(rel.field.name, flat=True)
        )
    return used


def load_catalog(apps=None, using="default", log=print):
    if apps is None:
        from django.apps import apps as global_apps
        apps = global_apps

    Style = apps.get_model("batik_custom", "StyleOptions")
    Palette = apps.get_model("batik_custom", "ColorPalette")
    Fashion = apps.get_model("batik_custom", "FashionPreference")
    Motif = apps.get_model("batik_custom", "RecommendedMotif")

    catalog = _read("catalog.json")
    motif_rows = _read("recommended_motifs.json")["motifs"]
    warnings = []

    with transaction.atomic(using=using):
        # ---------- 1. gaya ----------
        style_map = {}  # (base, gender) -> [semua baris DB yang cocok]
        existing_styles = list(Style.objects.using(using).order_by("pk"))
        for entry in catalog["styles"]:
            key = (_base(entry["name"]), entry["gender"])
            rows = [s for s in existing_styles if (_base(s.name), s.gender) == key]
            if not rows:
                rows = [Style.objects.using(using).create(**entry)]
                existing_styles.extend(rows)
            for row in rows:
                if not _keep_upload(row.image.name):
                    row.image = entry["image"]
                    row.save(update_fields=["image"])
            style_map[key] = rows

        # ---------- 2. palet ----------
        palette_map = {}
        existing_palettes = {_norm(p.name): p for p in Palette.objects.using(using).order_by("pk")}
        for entry in catalog["palettes"]:
            row = existing_palettes.get(_norm(entry["name"]))
            if row is None:
                row = Palette.objects.using(using).create(**entry)
                existing_palettes[_norm(entry["name"])] = row
            elif not _keep_upload(row.image.name):
                row.image = entry["image"]
                row.save(update_fields=["image"])
            palette_map[_norm(entry["name"])] = row

        # ---------- 3. preferensi fashion ----------
        fashion_map = {}
        for name in ("Women", "Men", "Unisex"):
            fashion_map[name.casefold()] = Fashion.objects.using(using).get_or_create(name=name)[0]
        for row in Fashion.objects.using(using).all():
            fashion_map.setdefault(row.name.casefold(), row)

        # ---------- 4. motif ----------
        index = {}
        existing_motifs = Motif.objects.using(using).prefetch_related("styles").order_by("pk")
        for motif in existing_motifs:
            key = (motif.name, frozenset(s.pk for s in motif.styles.all()))
            index.setdefault(key, motif)

        kept_ids, created, updated = [], 0, 0
        style_links, palette_links, fashion_links = {}, {}, {}
        for entry in motif_rows:
            styles = style_map.get((_base(entry["style"]), entry["fashion_preference"].casefold()))
            fashion = fashion_map.get(entry["fashion_preference"].casefold())
            if not styles or fashion is None:
                warnings.append(f"Gaya/preferensi tidak ditemukan: {entry['style']} ({entry['fashion_preference']})")
                continue
            palettes = []
            for palette_name in entry["palettes"]:
                palette = palette_map.get(_norm(palette_name))
                if palette is None:
                    warnings.append(f"Palet tidak ditemukan: {palette_name}")
                else:
                    palettes.append(palette)

            key = (entry["name"], frozenset(s.pk for s in styles))
            motif = index.get(key)
            if motif is None:
                motif = Motif.objects.using(using).create(
                    name=entry["name"], description=entry["description"],
                    image=entry["image"], is_active=entry.get("is_active", True),
                )
                index[key] = motif
                created += 1
            else:
                motif.description = entry["description"]
                motif.is_active = entry.get("is_active", True)
                if not _keep_upload(motif.image.name if motif.image else ""):
                    motif.image = entry["image"]
                motif.save()
                updated += 1

            kept_ids.append(motif.pk)
            style_links[motif.pk] = [s.pk for s in styles]
            palette_links[motif.pk] = [p.pk for p in palettes]
            fashion_links[motif.pk] = [fashion.pk]

        _set_links(Motif, "styles", using, style_links)
        _set_links(Motif, "palettes", using, palette_links)
        _set_links(Motif, "fashion_preference", using, fashion_links)

        # ---------- 5. bersihkan data lama yang tidak terpakai ----------
        stale_ids = list(
            Motif.objects.using(using).exclude(pk__in=kept_ids).values_list("pk", flat=True)
        )
        deleted = deactivated = 0
        if stale_ids:
            used = _referenced_motif_ids(Motif, using, stale_ids)
            removable = [pk for pk in stale_ids if pk not in used]
            for start in range(0, len(removable), 500):
                Motif.objects.using(using).filter(pk__in=removable[start:start + 500]).delete()
            deleted = len(removable)
            if used:
                Motif.objects.using(using).filter(pk__in=used).update(is_active=False)
                deactivated = len(used)

    log(
        "[batik_custom] katalog dimuat: "
        f"{len(style_map)} gaya, {len(palette_map)} palet, "
        f"motif baru {created}, diperbarui {updated}, "
        f"lama dihapus {deleted}, lama dinonaktifkan {deactivated}."
    )
    for message in sorted(set(warnings)):
        log(f"[batik_custom] PERINGATAN: {message}")
    return {"created": created, "updated": updated, "deleted": deleted, "warnings": warnings}
