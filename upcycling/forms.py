import re

from django import forms
from .models import NOTES_MAX_LENGTH, UpcyclingRequest

FIELD_CLASSES = (
    "block w-full px-4 py-3 text-[var(--brown)] "
    "focus:outline-none focus:ring-2 focus:ring-[var(--gold)]"
)

PRODUCTS_BY_CATEGORY = {
    "TAS": ("TOTE_BAG", "SLING_BAG", "BACKPACK", "SHOULDER_BAG", "LAINNYA"),
    "POUCH": ("POUCH", "PENCIL_CASE", "MAKEUP_POUCH", "LAPTOP_SLEEVE", "LAINNYA"),
    "PAKAIAN": ("KEMEJA", "OUTER", "ROK", "LAINNYA"),
    "AKSESORIS": (
        "AKSESORIS",
        "SCRUNCHIE",
        "BUCKET_HAT",
        "HEADBAND",
        "KEYCHAIN",
        "LAINNYA",
    ),
    "RUMAH_TANGGA": ("SARUNG_BANTAL", "LAINNYA"),
    "LAINNYA": ("LAINNYA",),
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
        """Configure request choices and labels."""
        super().__init__(*args, **kwargs)

        choices_by_field = {
            "fabric": UpcyclingRequest.FABRIC_CHOICES,
            "category": UpcyclingRequest.CATEGORY_CHOICES,
        }
        for field_name, choices in choices_by_field.items():
            self.fields[field_name].choices = choices

        self.fields["fabric_photo"].label = "Foto kain"
        self.fields["fabric_photo"].required = self.instance._state.adding
        self.fields["fabric_photo"].widget.attrs.update({"accept": "image/*"})
        self.fields["fabric"].label = "Jenis kain atau barang yang akan diolah"
        self.fields["fabric_condition"].label = "Kondisi kain menurut Anda"
        self.fields["fabric_condition"].choices = [
            ("", "Pilih kondisi kain (opsional)"),
            *UpcyclingRequest.FabricCondition.choices,
        ]
        self.fields["fabric_dimensions"].label = "Perkiraan ukuran atau jumlah kain"
        self.fields["fabric_composition"].label = "Komposisi bahan (opsional)"
        self.fields["fabric_composition"].help_text = (
            "Jika diketahui, tulis serat penyusun kain, misalnya katun 95% dan elastane 5%."
        )
        self.fields["wants_batik_accent"].label = (
            "Tambahkan kain bermotif batik dari ReBatik"
        )
        self.fields["batik_motif"].label = "Motif batik yang diinginkan (opsional)"
        self.fields["motif_placement"].label = "Penempatan motif (opsional)"
        self.fields["design_notes"].label = "Catatan desain tambahan (opsional)"
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
            "fabric_composition",
            "category",
            "product",
            "custom_product",
            "wants_batik_accent",
            "batik_motif",
            "motif_placement",
            "design_notes",
            "quantity",
            "notes",
            "whatsapp",
        ]
        labels = {
            "fabric": "Jenis kain atau barang yang akan diolah",
            "category": "Kategori Produk",
            "product": "Model Produk",
            "custom_product": "Produk yang diinginkan",
            "wants_batik_accent": "Tambahkan kain bermotif batik dari ReBatik",
            "batik_motif": "Motif batik yang diinginkan (opsional)",
            "motif_placement": "Penempatan motif (opsional)",
            "design_notes": "Catatan desain tambahan (opsional)",
            "quantity": "Jumlah Produk",
            "notes": "Deskripsi dan Catatan Khusus (opsional)",
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
            "fabric_photo": forms.FileInput(
                attrs={
                    "class": "upcycling-photo-input",
                    "accept": "image/*",
                    "aria-label": "Tambah foto kain",
                }
            ),
            "fabric_dimensions": forms.TextInput(attrs={"class": f"{FIELD_CLASSES} upcycling-field upcycling-input", "placeholder": "Contoh: 1 celana jeans atau kain 1 × 2 m"}),
            "fabric_composition": forms.TextInput(
                attrs={
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-input",
                    "maxlength": 120,
                    "placeholder": "Contoh: katun 95%, elastane 5%",
                }
            ),
            "fabric_condition": forms.Select(attrs={"class": f"{FIELD_CLASSES} upcycling-field upcycling-input"}),
            "wants_batik_accent": forms.CheckboxInput(
                attrs={"class": "upcycling-checkbox"}
            ),
            "batik_motif": forms.TextInput(
                attrs={
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-input",
                    "maxlength": 150,
                    "placeholder": "Contoh: Mega Mendung, Parang, atau Kawung",
                }
            ),
            "motif_placement": forms.TextInput(
                attrs={
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-input",
                    "maxlength": 150,
                    "placeholder": "Contoh: bagian depan tote bag",
                }
            ),
            "design_notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "maxlength": NOTES_MAX_LENGTH,
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-textarea",
                    "placeholder": "Warna, ukuran aksen, atau detail desain lainnya",
                }
            ),
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
            "notes": forms.Textarea(
                attrs={
                    "rows": 4,
                    "maxlength": NOTES_MAX_LENGTH,
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-textarea",
                    "placeholder": "Ceritakan model, warna, ukuran, atau catatan khusus...",
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

        if not cleaned_data.get("wants_batik_accent"):
            cleaned_data["batik_motif"] = ""
            cleaned_data["motif_placement"] = ""
            cleaned_data["design_notes"] = ""

        return cleaned_data


class FabricHandoffForm(forms.ModelForm):
    """Collect fabric handoff details after the artisan approves the request."""

    class Meta:
        model = UpcyclingRequest
        fields = ["fabric_delivery_method", "fabric_delivery_location"]
        labels = {
            "fabric_delivery_method": "Cara menyerahkan kain",
            "fabric_delivery_location": "Catatan penyerahan (opsional)",
        }
        widgets = {
            "fabric_delivery_method": forms.Select(
                attrs={"class": f"{FIELD_CLASSES} upcycling-field upcycling-input"}
            ),
            "fabric_delivery_location": forms.TextInput(
                attrs={
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-input",
                    "placeholder": "Contoh: waktu yang diinginkan atau catatan untuk admin",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        method_field = self.fields["fabric_delivery_method"]
        if not self.instance.fabric_delivery_location:
            method_field.choices = [
                ("", "Pilih cara menyerahkan kain"),
                *method_field.choices,
            ]
            self.initial["fabric_delivery_method"] = ""
        self.fields["fabric_delivery_location"].required = False
        self.fields["fabric_delivery_location"].help_text = (
            "Lokasi drop-off dan alamat tujuan pengiriman akan dikoordinasikan admin. "
            "Belum perlu mengisi alamat di sini."
        )


class ProductDeliveryForm(forms.ModelForm):
    """Collect delivery details when the user approves the artisan's quote."""

    class Meta:
        model = UpcyclingRequest
        fields = ["delivery_method", "address"]
        labels = {
            "delivery_method": "Metode penerimaan produk",
            "address": "Alamat atau lokasi penerimaan produk",
        }
        widgets = {
            "delivery_method": forms.RadioSelect(),
            "address": forms.TextInput(
                attrs={
                    "class": f"{FIELD_CLASSES} upcycling-field upcycling-input",
                    "placeholder": "Isi setelah memilih metode penerimaan",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["delivery_method"].choices = UpcyclingRequest.DELIVERY_CHOICES
        self.fields["delivery_method"].required = True
        self.fields["address"].required = True
        self.fields["address"].help_text = (
            "Isi alamat pengiriman atau lokasi pengambilan sesuai metode yang dipilih."
        )
