import re

from django import forms
from .models import NOTES_MAX_LENGTH, UpcyclingRequest

FIELD_CLASSES = (
    "block w-full px-4 py-3 text-[var(--brown)] "
    "focus:outline-none focus:ring-2 focus:ring-[var(--gold)]"
)

PRODUCTS_BY_CATEGORY = {
    "TAS": ("TOTE_BAG", "SLING_BAG", "LAINNYA"),
    "POUCH": ("POUCH", "LAPTOP_SLEEVE", "LAINNYA"),
    "PAKAIAN": ("KEMEJA", "LAINNYA"),
    "AKSESORIS": ("AKSESORIS", "SCRUNCHIE", "BUCKET_HAT", "LAINNYA"),
    "RUMAH_TANGGA": ("SARUNG_BANTAL", "LAINNYA"),
    "LAINNYA": ("LAINNYA",),
}

DEFAULT_ADDRESS_DETAILS = {
    "label": "Alamat / Lokasi Penerimaan Produk",
    "placeholder": "Alamat pengiriman atau lokasi pengambilan produk",
    "help_text": "Pilih metode penerimaan produk untuk melihat informasi yang perlu diisi.",
    "required_message": "Isi alamat atau lokasi penerimaan produk.",
}

ADDRESS_DETAILS_BY_METHOD = {
    "KURIR": {
        "label": "Alamat pengiriman",
        "placeholder": "Masukkan alamat lengkap penerima produk",
        "help_text": "Masukkan alamat lengkap tujuan pengiriman produk.",
        "required_message": "Masukkan alamat pengiriman.",
    },
    "DROP_OFF": {
        "label": "Rencana lokasi pengambilan produk",
        "placeholder": "Lokasi pengambilan produk jadi",
        "help_text": "Tuliskan lokasi tempat Anda akan menerima produk jadi.",
        "required_message": "Masukkan lokasi pengambilan produk.",
    },
}


def get_product_options_by_category():
    """Return product choices grouped for the request form's category picker."""
    product_labels = dict(UpcyclingRequest.PRODUCT_CHOICES)
    return {
        category: [
            {"value": value, "label": product_labels[value]}
            for value in values
        ]
        for category, values in PRODUCTS_BY_CATEGORY.items()
    }


class UpcyclingRequestForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        """Configure model choices and delivery-specific address guidance."""
        super().__init__(*args, **kwargs)

        choices_by_field = {
            "fabric": UpcyclingRequest.FABRIC_CHOICES,
            "category": UpcyclingRequest.CATEGORY_CHOICES,
            "delivery_method": UpcyclingRequest.DELIVERY_CHOICES,
            "fabric_delivery_method": UpcyclingRequest.FABRIC_DELIVERY_CHOICES,
        }
        for field_name, choices in choices_by_field.items():
            self.fields[field_name].choices = choices

        delivery_method = (
            self.data.get("delivery_method")
            if self.is_bound
            else self.initial.get("delivery_method")
            or getattr(self.instance, "delivery_method", "")
        )
        address_details = ADDRESS_DETAILS_BY_METHOD.get(
            delivery_method,
            DEFAULT_ADDRESS_DETAILS,
        )
        address_field = self.fields["address"]
        address_field.label = address_details["label"]
        address_field.help_text = address_details["help_text"]
        address_field.error_messages["required"] = address_details[
            "required_message"
        ]
        address_field.widget.attrs["placeholder"] = address_details[
            "placeholder"
        ]

        for method, details in ADDRESS_DETAILS_BY_METHOD.items():
            data_prefix = "kurir" if method == "KURIR" else "drop-off"
            for detail_name, detail_value in details.items():
                address_field.widget.attrs[
                    f"data-{data_prefix}-{detail_name.replace('_', '-')}"
                ] = detail_value

        for detail_name, detail_value in DEFAULT_ADDRESS_DETAILS.items():
            address_field.widget.attrs[
                f"data-default-{detail_name.replace('_', '-')}"
            ] = detail_value
        address_field.widget.attrs["aria-describedby"] = "address-help"
        self.fields["fabric_photo"].label = "Foto kain"
        self.fields["fabric_photo"].required = self.instance._state.adding
        self.fields["fabric_photo"].widget.attrs.update({"accept": "image/*"})
        self.fields["fabric_condition"].label = "Kondisi kain menurut Anda"
        self.fields["fabric_dimensions"].label = "Perkiraan ukuran atau jumlah kain"
        self.fields["fabric_delivery_method"].label = "Cara menyerahkan kain"
        self.fields["fabric_delivery_location"].label = "Lokasi/rencana penyerahan kain"
        self.fields["fabric_delivery_location"].required = False
        self.fields["fabric_other_description"].label = "Jenis kain lainnya"
        self.fields["fabric_other_description"].widget.attrs.update(
            {"placeholder": "Contoh: kanvas, corduroy, atau linen"}
        )

    class Meta:
        model = UpcyclingRequest
        fields = [
            "fabric",
            "fabric_other_description",
            "fabric_photo",
            "fabric_condition",
            "fabric_dimensions",
            "fabric_delivery_method",
            "fabric_delivery_location",
            "category",
            "product",
            "custom_product",
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
            "custom_product": "Produk yang diinginkan",
            "quantity": "Jumlah Produk",
            "notes": "Deskripsi dan Catatan Khusus (opsional)",
            "delivery_method": "Metode Penerimaan Produk",
            "address": "Alamat / Lokasi Penerimaan Produk",
            "whatsapp": "Nomor WhatsApp",
        }
        error_messages = {
            "notes": {
                "max_length": f"Catatan maksimal {NOTES_MAX_LENGTH} karakter."
            }
        }
        widgets = {
            "fabric": forms.RadioSelect(attrs={"class": "sr-only"}),
            "fabric_other_description": forms.TextInput(attrs={"class": f"{FIELD_CLASSES} upcycling-field upcycling-input", "maxlength": 100}),
            "fabric_photo": forms.ClearableFileInput(attrs={"class": f"{FIELD_CLASSES} upcycling-field upcycling-input", "accept": "image/*"}),
            "fabric_dimensions": forms.TextInput(attrs={"class": f"{FIELD_CLASSES} upcycling-field upcycling-input", "placeholder": "Contoh: 1 celana jeans atau kain 1 × 2 m"}),
            "fabric_delivery_location": forms.TextInput(attrs={"class": f"{FIELD_CLASSES} upcycling-field upcycling-input", "placeholder": "Lokasi/rencana penyerahan kain"}),
            "fabric_condition": forms.Select(attrs={"class": f"{FIELD_CLASSES} upcycling-field upcycling-input"}),
            "fabric_delivery_method": forms.Select(attrs={"class": f"{FIELD_CLASSES} upcycling-field upcycling-input"}),
            "category": forms.RadioSelect(attrs={"class": "sr-only"}),
            # The product chips are rendered in the template; retain this
            # select as the submitted form value.
            "product": forms.Select(attrs={"class": "sr-only"}),
            "custom_product": forms.TextInput(
                attrs={
                    "maxlength": 100,
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-input",
                    "placeholder": "Contoh: sarung bantal",
                }
            ),
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
                    "maxlength": NOTES_MAX_LENGTH,
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-textarea",
                    "placeholder": "Ceritakan model, warna, ukuran, atau catatan khusus...",
                }
            ),
            "address": forms.TextInput(
                attrs={
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-input",
                }
            ),
            "whatsapp": forms.TextInput(
                attrs={
                    "type": "tel",
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-input",
                    "placeholder": "Contoh: +6281234567890",
                }
            ),
        }

    def clean_quantity(self):
        """Reject quantities outside the supported product range."""
        quantity = self.cleaned_data["quantity"]
        if quantity < 1 or quantity > 20:
            raise forms.ValidationError(
                "Jumlah produk harus antara 1 dan 20."
            )
        return quantity

    def clean_fabric_photo(self):
        photo = self.cleaned_data.get("fabric_photo")
        if photo and photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Ukuran foto kain maksimal 5 MB.")
        return photo

    def clean_whatsapp(self):
        """Validate and normalize an Indonesian mobile number."""
        whatsapp = self.cleaned_data["whatsapp"]
        normalized = re.sub(r"[\s().-]", "", whatsapp)

        if not re.fullmatch(r"(?:0|\+?62)8[1-9][0-9]{7,10}", normalized):
            raise forms.ValidationError(
                "Masukkan nomor HP Indonesia yang valid, misalnya +6281234567890."
            )

        if normalized.startswith("0"):
            return f"+62{normalized[1:]}"
        if normalized.startswith("62"):
            return f"+{normalized}"
        return normalized

    def clean(self):
        """Validate product/category compatibility and custom product names."""
        cleaned_data = super().clean()
        fabric = cleaned_data.get("fabric")
        other_fabric = cleaned_data.get("fabric_other_description", "").strip()
        category = cleaned_data.get("category")
        product = cleaned_data.get("product")
        custom_product = cleaned_data.get("custom_product", "").strip()

        if fabric == UpcyclingRequest.FabricType.OTHER and not other_fabric:
            self.add_error(
                "fabric_other_description",
                "Tuliskan jenis kain yang akan digunakan.",
            )
        elif fabric != UpcyclingRequest.FabricType.OTHER:
            cleaned_data["fabric_other_description"] = ""
        else:
            cleaned_data["fabric_other_description"] = other_fabric

        if product == "LAINNYA" and not custom_product:
            self.add_error(
                "custom_product",
                "Tuliskan produk yang Anda inginkan.",
            )
        elif product != "LAINNYA":
            cleaned_data["custom_product"] = ""
        else:
            cleaned_data["custom_product"] = custom_product

        if category and product:
            if product not in PRODUCTS_BY_CATEGORY.get(category, ()):
                self.add_error(
                    "product",
                    "Model produk tidak sesuai dengan kategori yang dipilih.",
                )

        return cleaned_data
