from pathlib import Path

from django.conf import settings
from django.db import migrations


STYLE_PATHS = {
    "style_options/bohemian.jpe": "img/catalog/style_options/bohemian.jpe",
    "style_options/bohemian_Kx4Y0Bg.jpe": "img/catalog/style_options/bohemian.jpe",
    "style_options/bohemian1.jpg": "img/catalog/style_options/bohemian1.jpg",
    "style_options/bohemian1_Pg72tKO.jpg": "img/catalog/style_options/bohemian1.jpg",
    "style_options/bohemian2.jpg": "img/catalog/style_options/bohemian2.jpg",
    "style_options/casual.jpe": "img/catalog/style_options/casual.jpe",
    "style_options/casual_OXr3eUC.jpe": "img/catalog/style_options/casual.jpe",
    "style_options/casual_OXr3eUC_85ejCbN.jpe": "img/catalog/style_options/casual.jpe",
    "style_options/casual_yTNd5M3.jpe": "img/catalog/style_options/casual.jpe",
    "style_options/casual1.webp": "img/catalog/style_options/casual1.webp",
    "style_options/casual1_2Vmx4ON.webp": "img/catalog/style_options/casual1.webp",
    "style_options/casual2.jpg": "img/catalog/style_options/casual2.jpg",
    "style_options/creative.jpg": "img/catalog/style_options/creative.jpg",
    "style_options/creative1.png": "img/catalog/style_options/creative1.png",
    "style_options/creative1_IYNWU36.png": "img/catalog/style_options/creative1.png",
    "style_options/creative2.jpg": "img/catalog/style_options/creative2.jpg",
    "style_options/creative_PoB9U13.jpg": "img/catalog/style_options/creative_iXI3qGg.jpg",
    "style_options/elegan2.jpe": "img/catalog/style_options/elegan2.jpe",
    "style_options/elegant.jpg": "img/catalog/style_options/elegant.jpg",
    "style_options/elegant_ygnIuZD.jpg": "img/catalog/style_options/elegant.jpg",
    "style_options/elegant1.png": "img/catalog/style_options/elegant1.png",
    "style_options/elegant1_n2sIuAb.png": "img/catalog/style_options/elegant1_UGFVhna.png",
    "style_options/elegant1_n2sIuAb_lmECXdD.png": "img/catalog/style_options/elegant1_UGFVhna.png",
    "style_options/minimalis.jpg": "img/catalog/style_options/minimalis.jpg",
    "style_options/minimalis_kAQBsKF.jpg": "img/catalog/style_options/minimalis.jpg",
    "style_options/minimalis1.png": "img/catalog/style_options/minimalis1.png",
    "style_options/minimalis1_SL5u48N.png": "img/catalog/style_options/minimalis1.png",
    "style_options/minimalis2.jpg": "img/catalog/style_options/minimalis2.jpg",
    "style_options/natural.jpg": "img/catalog/style_options/natural.jpg",
    "style_options/natural_vYC3DFa.jpg": "img/catalog/style_options/natural.jpg",
    "style_options/natural1.jpg": "img/catalog/style_options/natural1.jpg",
    "style_options/natural1_hDYEUDz.jpg": "img/catalog/style_options/natural1.jpg",
    "style_options/natural2.jpg": "img/catalog/style_options/natural2.jpg",
    "shared/creative1.png": "img/catalog/style_options/creative1.png",
    "img/catalog/shared/creative1.png": "img/catalog/style_options/creative1.png",
    "shared/minimalis1.webp": "img/catalog/style_options/minimalis1.png",
    "img/catalog/shared/minimalis1.webp": "img/catalog/style_options/minimalis1.png",
}

MOTIF_FILENAMES = (
    "Batik-Sekar-Jagad-Warna-Coklat.jpg",
    "batik-lasem-motif-burung-hong.jpg",
    "batik-sidomukti.webp",
    "batik-sukapura.webp",
    "ceplok.jpg",
    "ceplok.png",
    "flora_nusantara.jpg",
    "flora_nusantara.png",
    "kawung.jpg",
    "kawung_EFz2Zs3.png",
    "kawung_minimal.png",
    "kontemporer_parang.jpg",
    "kontemporer_parang_FxTZmYB.jpg",
    "lereng.jpg",
    "megamendung.jpg",
    "nitik.jpg",
    "ondel.jpg",
    "ondel2.png",
    "parang-rusak.jpg",
    "parang.jpg",
    "sekar-jagad.jpg",
    "sekar_jagad.png",
    "semen.jpg",
    "semen.png",
    "simbut.jpg",
    "truntum-hitam.jpg",
    "truntum.jpg",
    "truntum.png",
    "tujuhrupa.webp",
    "tumpal.jpg",
)

MOTIF_PATHS = {
    old_path: f"img/catalog/recommended_motifs/{filename}"
    for filename in MOTIF_FILENAMES
    for old_path in (
        f"recommended_motifs/{filename}",
        f"img/catalog/recommended_motifs/{filename}",
    )
}
MOTIF_PATHS.update({
    "recommended_motifs/kawung.png": "img/catalog/recommended_motifs/kawung_EFz2Zs3.png",
    "img/catalog/recommended_motifs/kawung.png": "img/catalog/recommended_motifs/kawung_EFz2Zs3.png",
    "recommended_motifs/megamendung.png": "img/catalog/recommended_motifs/megamendung.jpg",
    "img/catalog/recommended_motifs/megamendung.png": "img/catalog/recommended_motifs/megamendung.jpg",
    "recommended_motifs/parang.png": "img/catalog/recommended_motifs/parang.jpg",
    "img/catalog/recommended_motifs/parang.png": "img/catalog/recommended_motifs/parang.jpg",
    "recommended_motifs/ondel2.png": "img/catalog/batik/ondel2.png",
    "img/catalog/recommended_motifs/ondel2.png": "img/catalog/batik/ondel2.png",
    "img/catalog/batik/ondel2.png": "img/catalog/batik/ondel2.png",
    "img/catalog/shared/creative1.png": "img/catalog/style_options/creative1.png",
    "img/catalog/shared/minimalis1.webp": "img/catalog/style_options/minimalis1.png",
})

COLOR_PATHS = {
    f"colorpalette/{name}": f"img/catalog/colorpalette/{name}"
    for name in (
        "Thanksgiving.jpe", "Vintage.jpe", "cool.jpe", "cristmas.jpe",
        "dark.jpe", "easter.jpe", "fall.jpe", "food.jpe", "gradient.jpe",
        "hallowen.jpe", "light.jpe", "nature.jpe", "neon.jpe", "neutral.jpe",
        "ocean.jpe", "pastel.jpe", "retro.png", "spring.jpe", "summer.png",
        "sunset.png", "valentine.jpe", "warm.jpe", "wedding.webp", "winter.jpe",
    )
}


def fix_image_paths(apps, schema_editor):
    database = schema_editor.connection.alias
    for model_name, field_name, path_map in (
        ("StyleOptions", "image", STYLE_PATHS),
        ("RecommendedMotif", "image", MOTIF_PATHS),
        ("ColorPalette", "image", COLOR_PATHS),
    ):
        Model = apps.get_model("batik_custom", model_name)
        queryset = Model.objects.using(database)
        for old_path, new_path in path_map.items():
            # Keep a user's upload when it occupies a legacy catalog filename.
            if not old_path.startswith("img/catalog/") and (
                Path(settings.MEDIA_ROOT) / old_path
            ).is_file():
                continue
            queryset.filter(**{field_name: old_path}).update(
                **{field_name: new_path}
            )


class Migration(migrations.Migration):
    dependencies = [("batik_custom", "0012_colorpalette_image")]

    operations = [migrations.RunPython(fix_image_paths, migrations.RunPython.noop)]
