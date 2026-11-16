from django.core.validators import RegexValidator
from django.utils.html import strip_tags
from rest_framework import serializers

from config.api_utils import absolute_image_url
from batik_custom.models import (
    BatikOrder, ColorPalette, ProductDesignOption, RecommendedMotif,
    SavedDesign, StyleOptions,
)
from batik_custom.views import PRODUCT_PRICES

ROTATIONS = [0, 90, 180, 270]
MATERIALS = ["Katun Premium", "Katun Poplin", "Rayon", "Satin"]
SIZES = ["S", "M", "L", "XL", "XXL"]
SLEEVES = ["short", "long", "sleeveless"]
FITS = ["regular", "slim", "oversized", "loose"]
PLACEMENTS = ["all_over", "front", "back", "sleeve", "border"]
UNITS = ["pcs", "meter"]


# ---------------------------------------------------------------------------
# Katalog (read-only)
# ---------------------------------------------------------------------------
class StyleOptionsSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = StyleOptions
        fields = ["id", "name", "description", "detail", "gender", "icon", "image_url"]
        read_only_fields = fields

    def get_image_url(self, obj):
        return absolute_image_url(self.context.get("request"), obj.image)


class ColorPaletteSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ColorPalette
        fields = ["id", "name", "description", "colors", "image_url"]
        read_only_fields = fields

    def get_image_url(self, obj):
        return absolute_image_url(self.context.get("request"), obj.image)


class RecommendedMotifSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    style_ids = serializers.SerializerMethodField()
    palette_ids = serializers.SerializerMethodField()
    preferences = serializers.SerializerMethodField()

    class Meta:
        model = RecommendedMotif
        fields = [
            "id", "name", "description", "image_url",
            "style_ids", "palette_ids", "preferences",
        ]
        read_only_fields = fields

    def get_image_url(self, obj):
        return absolute_image_url(self.context.get("request"), obj.image)

    def get_style_ids(self, obj):
        return [style.pk for style in obj.styles.all()]

    def get_palette_ids(self, obj):
        return [palette.pk for palette in obj.palettes.all()]

    def get_preferences(self, obj):
        return [pref.name for pref in obj.fashion_preference.all()]


class ProductDesignOptionSerializer(serializers.ModelSerializer):
    product_type_display = serializers.CharField(
        source="get_product_type_display", read_only=True,
    )
    image_url = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()

    class Meta:
        model = ProductDesignOption
        fields = [
            "id", "product_type", "product_type_display", "name",
            "description", "image_url", "price",
        ]
        read_only_fields = fields

    def get_image_url(self, obj):
        return absolute_image_url(self.context.get("request"), obj.image)

    def get_price(self, obj):
        return PRODUCT_PRICES.get(obj.product_type)


# ---------------------------------------------------------------------------
# Desain tersimpan
# ---------------------------------------------------------------------------
class SavedDesignSerializer(serializers.ModelSerializer):
    motif = serializers.PrimaryKeyRelatedField(
        queryset=RecommendedMotif.objects.filter(is_active=True),
    )
    palette = serializers.PrimaryKeyRelatedField(
        queryset=ColorPalette.objects.filter(is_active=True),
        required=False, allow_null=True,
    )
    layout = serializers.ChoiceField(
        choices=SavedDesign.LAYOUT_CHOICES, default="grid",
    )
    scale = serializers.IntegerField(min_value=40, max_value=220, default=100)
    rotation = serializers.ChoiceField(choices=ROTATIONS, default=0)
    gap = serializers.IntegerField(min_value=0, max_value=60, default=50)
    color = serializers.CharField(
        max_length=7, default="#874a29",
        validators=[RegexValidator(r"^#[0-9a-fA-F]{6}$", "Warna harus berformat #RRGGBB.")],
    )
    tint = serializers.IntegerField(min_value=0, max_value=70, default=0)
    motif_name = serializers.CharField(source="motif.name", read_only=True)
    motif_image_url = serializers.SerializerMethodField()
    palette_name = serializers.SerializerMethodField()

    class Meta:
        model = SavedDesign
        fields = [
            "id", "title", "motif", "motif_name", "motif_image_url",
            "palette", "palette_name", "layout", "scale", "rotation",
            "gap", "color", "tint", "is_public", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_title(self, value):
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Judul desain tidak boleh kosong.")
        return value

    def validate_motif(self, value):
        # Sama seperti halaman edit di web: motif tidak bisa diganti.
        if self.instance is not None and value != self.instance.motif:
            raise serializers.ValidationError("Motif tidak dapat diubah.")
        return value

    def get_motif_image_url(self, obj):
        return absolute_image_url(self.context.get("request"), obj.motif.image)

    def get_palette_name(self, obj):
        return obj.palette.name if obj.palette else ""


# ---------------------------------------------------------------------------
# Pesanan
# ---------------------------------------------------------------------------
def _optional_choice(choices):
    return serializers.ChoiceField(choices=choices, required=False, allow_blank=True)


class BatikOrderSerializer(serializers.ModelSerializer):
    motif = serializers.PrimaryKeyRelatedField(
        queryset=RecommendedMotif.objects.filter(is_active=True),
    )
    palette = serializers.PrimaryKeyRelatedField(
        queryset=ColorPalette.objects.filter(is_active=True),
        required=False, allow_null=True,
    )
    design_option = serializers.PrimaryKeyRelatedField(
        queryset=ProductDesignOption.objects.filter(is_active=True),
    )
    material = serializers.ChoiceField(choices=MATERIALS)
    size = _optional_choice(SIZES)
    sleeve_type = _optional_choice(SLEEVES)
    fit_type = _optional_choice(FITS)
    motif_placement = _optional_choice(PLACEMENTS)
    quantity = serializers.IntegerField(min_value=1, max_value=100, default=1)
    unit = serializers.ChoiceField(choices=UNITS, default="pcs")
    phone = serializers.RegexField(
        r"^\+?[0-9\s\-]{8,30}$", max_length=30,
        error_messages={"invalid": "Nomor telepon tidak valid."},
    )
    postal_code = serializers.RegexField(
        r"^\d{4,10}$", max_length=10,
        error_messages={"invalid": "Kode pos harus berupa angka."},
    )

    motif_name = serializers.CharField(source="motif.name", read_only=True)
    design_option_name = serializers.SerializerMethodField()
    palette_name = serializers.SerializerMethodField()
    product_type_display = serializers.CharField(source="get_product_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)

    class Meta:
        model = BatikOrder
        fields = [
            "id", "motif", "motif_name", "palette", "palette_name",
            "style_name", "design_settings",
            "product_type", "product_type_display",
            "design_option", "design_option_name",
            "material", "size", "sleeve_type", "fit_type", "motif_placement",
            "custom_requirements", "quantity", "unit", "notes",
            "recipient_name", "phone", "address", "province", "city",
            "district", "postal_code",
            "payment_method", "payment_method_display",
            "unit_price", "total_price", "status", "status_display", "created_at",
        ]
        # Harga, total, status dan waktu ditentukan server, bukan klien.
        read_only_fields = ["id", "unit_price", "total_price", "status", "created_at"]

    def get_palette_name(self, obj):
        return obj.palette.name if obj.palette else ""

    def get_design_option_name(self, obj):
        return obj.design_option.name if obj.design_option else ""

    def validate_design_settings(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("design_settings harus berupa objek JSON.")
        return value

    def validate(self, attrs):
        if attrs["design_option"].product_type != attrs["product_type"]:
            raise serializers.ValidationError(
                {"design_option": "Pilih model yang sesuai dengan jenis produk."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["unit_price"] = PRODUCT_PRICES[validated_data["product_type"]]
        return BatikOrder.objects.create(**validated_data)
