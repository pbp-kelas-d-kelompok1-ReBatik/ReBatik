from django.contrib import admin
from .models import UpcyclingRequest


@admin.register(UpcyclingRequest)
class UpcyclingRequestAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "fabric",
        "category",
        "quantity",
        "user",
        "status",
        "created_at",
    )
    list_filter = ("status", "fabric", "category", "delivery_method")
    search_fields = ("user__username", "user__email", "whatsapp", "address")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
