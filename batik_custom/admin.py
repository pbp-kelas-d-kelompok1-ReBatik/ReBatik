from django.contrib import admin
from .models import StyleOptions, ColorPalette, StyleProfile,RecommendedMotif

# Register your models here.

admin.site.register(StyleOptions)
admin.site.register(ColorPalette)
admin.site.register(StyleProfile)
admin.site.register(RecommendedMotif)