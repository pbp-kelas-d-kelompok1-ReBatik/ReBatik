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


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleImageInput

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        return [super().clean(image, initial) for image in data]

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
    fabric_photos = MultipleImageField(required=False)
    reference_photos = MultipleImageField(required=False)

    def __init__(self, *args, **kwargs):
        """Configure request choices and labels."""
        super().__init__(*args, **kwargs)

        choices_by_field = {
            "fabric": UpcyclingRequest.FABRIC_CHOICES,
            "category": UpcyclingRequest.CATEGORY_CHOICES,
            "has_batik_pattern": UpcyclingRequest.BatikPatternStatus.choices,
            "current_item_form": UpcyclingRequest.CurrentItemForm.choices,
        }
        for field_name, choices in choices_by_field.items():
            self.fields[field_name].choices = choices

        self.fields["fabric_photos"].label = "Foto barang atau kain (1–3 foto)"
        self.fields["fabric_photos"].widget.attrs.update(
            {
                "accept": "image/*",
                "multiple": True,
                "class": "upcycling-photo-input",
                "aria-label": "Pilih 1 hingga 3 foto barang atau kain",
                "hx-preserve": True,
            }
        )
        self.existing_fabric_photo_count = (
            int(bool(self.instance.fabric_photo))
            + self.instance.additional_fabric_photos.count()
            if not self.instance._state.adding
            else 0
        )
        self.fields["reference_photos"].label = "Foto contoh hasil yang Anda inginkan (opsional)"
        self.fields["reference_photos"].widget.attrs.update(
            {
                "accept": "image/*",
                "multiple": True,
                "class": "upcycling-photo-input",
                "aria-label": "Pilih hingga 3 foto referensi produk atau desain",
                "hx-preserve": True,
            }
        )
        self.existing_reference_photo_count = (
            self.instance.reference_photos.count()
            if not self.instance._state.adding
            else 0
        )
        self.fields["fabric"].label = "Jenis bahan utama yang akan diolah"
        self.fields["has_batik_pattern"].label = (
            "Apakah barang atau kain Anda sudah memiliki motif batik?"
        )
        self.fields["has_batik_pattern"].choices = [
            ("", "Pilih jawaban"),
            *UpcyclingRequest.BatikPatternStatus.choices,
        ]
        self.fields["has_batik_pattern"].widget.choices = self.fields[
            "has_batik_pattern"
        ].choices
        self.fields["has_batik_pattern"].required = True
        if self.instance._state.adding and not self.is_bound:
            self.fields["has_batik_pattern"].initial = ""
        self.fields["current_item_form"].label = (
            "Barang atau kain apa yang ingin Anda olah?"
        )
        self.fields["current_item_form"].choices = [
            *UpcyclingRequest.CurrentItemForm.choices,
        ]
        self.fields["current_item_form"].widget = forms.RadioSelect(
            attrs={"class": "sr-only"}
        )
        self.fields["current_item_form"].widget.choices = self.fields[
            "current_item_form"
        ].choices
        self.fields["current_item_form"].required = True
        if self.instance._state.adding and not self.is_bound:
            self.fields["current_item_form"].initial = ""
        self.fields["current_item_form_other"].label = "Sebutkan bentuk lainnya"
        self.fields["current_item_form_other"].widget.attrs.update(
            {"placeholder": "Contoh: tas kain lama atau taplak meja"}
        )
        self.fields["fabric_condition"].label = (
            "Bagaimana kondisi barang atau kain Anda?"
        )
        self.fields["fabric_condition"].choices = [
            ("", "Pilih kondisi (opsional)"),
            *UpcyclingRequest.FabricCondition.choices,
        ]
        self.fields["fabric_dimensions"].label = (
            "Berapa banyak barang atau bahan yang ingin diolah?"
        )
        self.fields["fabric_dimensions"].help_text = (
            "Tidak perlu mengukur tepat. Contoh: 1 celana jeans ukuran L, 2 kaos, "
            "atau kain sekitar 1 × 2 m. Informasi ini membantu artisan memperkirakan kecukupan bahan."
        )
        self.fields["wants_batik_accent"].label = (
            "Kombinasikan bahan saya dengan kain batik dari ReBatik"
        )
        self.fields["batik_motif"].label = "Motif batik yang diinginkan (opsional)"
        self.fields["motif_placement"].label = (
            "Di bagian mana Anda ingin kain batik ditambahkan? (opsional)"
        )
        self.fields["quantity"].label = "Berapa produk baru yang ingin dibuat?"
        self.fields["notes"].help_text = (
            "Tuliskan preferensi warna, ukuran produk, atau permintaan lain untuk artisan."
        )
        self.fields["fabric_other_description"].label = "Sebutkan bahan lainnya"
        self.fields["fabric_other_description"].widget.attrs.update(
            {"placeholder": "Contoh: kanvas, corduroy, atau linen"}
        )

    class Meta:
        model = UpcyclingRequest
        fields = [
            "fabric",
            "fabric_other_description",
            "current_item_form",
            "current_item_form_other",
            "has_batik_pattern",
            "fabric_condition",
            "fabric_dimensions",
            "category",
            "product",
            "custom_product",
            "wants_batik_accent",
            "batik_motif",
            "motif_placement",
            "quantity",
            "notes",
            "whatsapp",
        ]
        labels = {
            "fabric": "Jenis bahan utama yang akan diolah",
            "has_batik_pattern": "Apakah barang atau kain Anda sudah memiliki motif batik?",
            "category": "Kategori Produk",
            "product": "Pilih produk yang ingin dibuat",
            "custom_product": "Produk yang diinginkan",
            "wants_batik_accent": "Kombinasikan bahan saya dengan kain batik dari ReBatik",
            "batik_motif": "Motif batik yang diinginkan (opsional)",
            "motif_placement": "Penempatan motif (opsional)",
            "quantity": "Berapa produk baru yang ingin dibuat?",
            "notes": "Catatan tambahan untuk artisan (opsional)",
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
            "current_item_form": forms.RadioSelect(attrs={"class": "sr-only"}),
            "current_item_form_other": forms.TextInput(
                attrs={"class": f"{FIELD_CLASSES} upcycling-field upcycling-input", "maxlength": 120}
            ),
            "has_batik_pattern": forms.RadioSelect(attrs={"class": "sr-only"}),
            "fabric_dimensions": forms.TextInput(attrs={"class": f"{FIELD_CLASSES} upcycling-field upcycling-input", "placeholder": "Contoh: 1 celana jeans ukuran L, 2 kaos, atau kain 1 × 2 m"}),
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

    def clean_fabric_photos(self):
        photos = self.cleaned_data.get("fabric_photos", [])
        if self.existing_fabric_photo_count + len(photos) < 1:
            raise forms.ValidationError("Unggah minimal 1 foto barang atau kain.")
        if self.existing_fabric_photo_count + len(photos) > 3:
            raise forms.ValidationError(
                "Jumlah foto barang atau kain maksimal 3. Foto yang sudah tersimpan tetap dihitung."
            )
        for photo in photos:
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Ukuran setiap foto barang atau kain maksimal 5 MB.")
        return photos

    def clean_reference_photos(self):
        photos = self.cleaned_data.get("reference_photos", [])
        if self.existing_reference_photo_count + len(photos) > 3:
            raise forms.ValidationError("Foto referensi maksimal 3 gambar.")
        for photo in photos:
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    "Ukuran setiap foto referensi maksimal 5 MB."
                )
        return photos

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
                "Sebutkan bahan lainnya.",
            )
        elif fabric != UpcyclingRequest.FabricType.OTHER:
            cleaned_data["fabric_other_description"] = ""
        else:
            cleaned_data["fabric_other_description"] = other_fabric
        item_form_other = cleaned_data.get("current_item_form_other", "").strip()
        if cleaned_data.get("current_item_form") == UpcyclingRequest.CurrentItemForm.OTHER:
            if not item_form_other:
                self.add_error("current_item_form_other", "Sebutkan bentuk barang lainnya.")
            cleaned_data["current_item_form_other"] = item_form_other
        else:
            cleaned_data["current_item_form_other"] = ""

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
