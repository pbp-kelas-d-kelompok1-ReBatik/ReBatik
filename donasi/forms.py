
from django import forms
from .models import DonasiKain


class DonasiKainForm(forms.ModelForm):

    class Meta:
        model = DonasiKain

        fields = [
            "donor_name",
            "whatsapp",
            "email",
            "address",
            "city",
            "item_name",
            "donation_type",
            "clothing_category",
            "quantity",
            "condition",
            "description",
            "photo",
            "donation_method",
            "pickup_date",
            "additional_notes",
        ]

        widgets = {
            "donor_name": forms.TextInput(attrs={
                "class": "donasi-input",
                "placeholder": "Nama lengkap donatur",
            }),
            "whatsapp": forms.TextInput(attrs={
                "class": "donasi-input",
                "placeholder": "Contoh: 081234567890",
            }),
            "email": forms.EmailInput(attrs={
                "class": "donasi-input",
                "placeholder": "nama@email.com",
            }),
            "address": forms.Textarea(attrs={
                "class": "donasi-input",
                "rows": 3,
                "placeholder": "Alamat lengkap",
            }),
            "city": forms.TextInput(attrs={
                "class": "donasi-input",
                "placeholder": "Kota/Kabupaten",
            }),
            "item_name": forms.TextInput(attrs={
                "class": "donasi-input",
                "placeholder": "Contoh: Baju batik perempuan",
            }),
            "donation_type": forms.RadioSelect(),
            "clothing_category": forms.RadioSelect(),
            "quantity": forms.NumberInput(attrs={
                "class": "donasi-input",
                "min": 1,
                "step": 1,
            }),
            "condition": forms.RadioSelect(),
            "description": forms.Textarea(attrs={
                "class": "donasi-input",
                "rows": 4,
                "placeholder": "Jelaskan motif, warna, bahan, dan kondisi",
            }),
            "photo": forms.ClearableFileInput(attrs={
                "class": "donasi-file-input",
                "accept": "image/*",
            }),
            "donation_method": forms.RadioSelect(),
            "pickup_date": forms.DateInput(attrs={
                "class": "donasi-input",
                "type": "date",
            }),
            "additional_notes": forms.Textarea(attrs={
                "class": "donasi-input",
                "rows": 3,
                "placeholder": "Catatan tambahan (opsional)",
            }),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")

        if photo and photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "Ukuran foto maksimal 5 MB."
            )

        return photo
