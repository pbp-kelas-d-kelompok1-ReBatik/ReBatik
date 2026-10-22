from django import forms
from .models import UpcyclingRequest

FIELD_CLASSES = (
    "block w-full px-4 py-3 text-[var(--brown)] "
    "focus:outline-none focus:ring-2 focus:ring-[var(--gold)]"
)


class UpcyclingRequestForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        choices_by_field = {
            "fabric": UpcyclingRequest.FABRIC_CHOICES,
            "category": UpcyclingRequest.CATEGORY_CHOICES,
            "delivery_method": UpcyclingRequest.DELIVERY_CHOICES,
        }
        for field_name, choices in choices_by_field.items():
            self.fields[field_name].choices = choices

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
        labels = {
            "fabric": "Kain",
            "category": "Kategori Produk",
            "product": "Model Produk",
            "quantity": "Jumlah Produk",
            "notes": "Deskripsi dan Catatan Khusus (opsional)",
            "delivery_method": "Metode Pengiriman Kain",
            "address": "Alamat / Lokasi",
            "whatsapp": "No. WhatsApp",
        }
        widgets = {
            "fabric": forms.RadioSelect(attrs={"class": "sr-only"}),
            "category": forms.RadioSelect(attrs={"class": "sr-only"}),
            # The product chips are rendered in the template; retain this
            # select as the submitted form value.
            "product": forms.Select(attrs={"class": "sr-only"}),
            "quantity": forms.NumberInput(
                attrs={
                    "min": 1,
                    "max": 20,
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-input",
                }
            ),
            "delivery_method": forms.RadioSelect(attrs={"class": "sr-only"}),
            "notes": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-textarea",
                    "placeholder": "Ceritakan model, warna, ukuran, atau catatan khusus...",
                }
            ),
            "address": forms.TextInput(
                attrs={
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-input",
                    "placeholder": "Alamat penjemputan (kurir) atau lokasi drop-off",
                }
            ),
            "whatsapp": forms.TextInput(
                attrs={
                    "type": "tel",
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-input",
                    "placeholder": "Contoh: 0812xxxxxxx",
                }
            ),
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
