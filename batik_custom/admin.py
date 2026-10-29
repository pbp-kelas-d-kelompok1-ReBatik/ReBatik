
from django.contrib import admin
from .models import (
    ProductDesignOption,
    StyleOptions,
    ColorPalette,
    StyleProfile,
    FashionPreference,
    RecommendedMotif,
    BatikOrder,
)


@admin.register(StyleOptions)
class StyleOptionsAdmin(admin.ModelAdmin):
    list_display = ("name", "gender", "is_active")
    list_filter = ("gender", "is_active")
    search_fields = ("name",)


@admin.register(ColorPalette)
class ColorPaletteAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(StyleProfile)
class StyleProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "style", "palette", "updated_at")


@admin.register(FashionPreference)
class FashionPreferenceAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(RecommendedMotif)
class RecommendedMotifAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("styles", "palettes", "is_active")
    search_fields = ("name",)
    filter_horizontal = ("styles", "palettes", "fashion_preference")

@admin.register(BatikOrder)
class BatikOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient_name", "product_type", "quantity", "total_price", "status", "created_at")
    list_filter = ("status", "product_type", "payment_method", "created_at")
    search_fields = ("recipient_name", "phone", "user__username")
    readonly_fields = ("created_at",)

@admin.register(ProductDesignOption)
class ProductDesignOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "product_type", "is_active")
    list_filter = ("product_type", "is_active")
    search_fields = ("name", "description")
    list_editable = ("is_active",)
