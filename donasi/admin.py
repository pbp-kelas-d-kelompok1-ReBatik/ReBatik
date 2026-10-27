
from django.contrib import admin
from .models import DonasiKain


@admin.register(DonasiKain)
class DonasiKainAdmin(admin.ModelAdmin):
    list_display = (
        "item_name",
        "donor_name",
        "donation_type",
        "quantity",
        "condition",
        "status",
        "created_at",
    )

    list_filter = (
        "donation_type",
        "condition",
        "status",
        "created_at",
    )

    search_fields = (
        "item_name",
        "donor_name",
        "city",
    )

    readonly_fields = ("created_at",)
