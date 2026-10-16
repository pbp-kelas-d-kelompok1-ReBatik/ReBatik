from django import forms
from .models import UpcyclingRequest


class UpcyclingRequestForm(forms.ModelForm):
    class Meta:
        model = UpcyclingRequest
        fields = [
            "fabric",
            "category",
            "product",
            "quantity",
            "notes",
            "delivery_method",
            "address",
            "whatsapp",
        ]
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": 1, "max": 20}),
            "notes": forms.Textarea(attrs={"rows": 4}),
            "whatsapp": forms.TextInput(attrs={"type": "tel"}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity < 1 or quantity > 20:
            raise forms.ValidationError(
                "Jumlah produk harus antara 1 dan 20."
            )
        return quantity

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        product = cleaned_data.get("product")

        allowed_products = {
            "TAS": {"TOTE_BAG", "SLING_BAG", "LAINNYA"},
            "POUCH": {"POUCH", "LAINNYA"},
            "PAKAIAN": {"KEMEJA", "LAINNYA"},
            "AKSESORIS": {"AKSESORIS", "LAINNYA"},
            "LAINNYA": {"LAINNYA"},
        }

        if category and product:
            if product not in allowed_products.get(category, set()):
                self.add_error(
                    "product",
                    "Model produk tidak sesuai dengan kategori yang dipilih.",
                )

        return cleaned_data