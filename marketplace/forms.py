from django import forms

from .models import MarketplaceOrder


class MarketplaceOrderForm(forms.ModelForm):
    class Meta:
        model = MarketplaceOrder
        fields = ["quantity", "recipient_name", "phone", "address", "notes"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": 1, "class": "w-full rounded-xl border p-3"}),
            "recipient_name": forms.TextInput(attrs={"class": "w-full rounded-xl border p-3", "placeholder": "Nama penerima"}),
            "phone": forms.TextInput(attrs={"class": "w-full rounded-xl border p-3", "placeholder": "Nomor WhatsApp"}),
            "address": forms.Textarea(attrs={"class": "w-full rounded-xl border p-3", "rows": 3, "placeholder": "Alamat lengkap"}),
            "notes": forms.Textarea(attrs={"class": "w-full rounded-xl border p-3", "rows": 2, "placeholder": "Catatan tambahan (opsional)"}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity < 1:
            raise forms.ValidationError("Jumlah minimal 1 produk.")
        return quantity
