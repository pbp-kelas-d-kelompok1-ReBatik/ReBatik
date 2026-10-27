from django.contrib import admin
from .models import (
    StyleOptions,
    ColorPalette,
    StyleProfile,
    FashionPreference,
    RecommendedMotif,
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
