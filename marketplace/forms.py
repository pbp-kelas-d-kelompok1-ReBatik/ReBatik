
from urllib.parse import urlparse

from django import forms

from .models import (
    DESCRIPTION_MAX_LENGTH,
    MAX_ORDER_QUANTITY,
    NOTES_MAX_LENGTH,
    DropOffPoint,
    MarketplaceOrder,
    Order,
    Product,
)
from .validators import normalize_indonesian_whatsapp


MIN_PRODUCT_PRICE = 1_000
MAX_PRODUCT_PRICE = 100_000_000
MAX_PRODUCT_STOCK = 10_000

FIELD_CLASSES = (
    "block w-full px-4 py-3 text-[var(--brown)] "
    "focus:outline-none focus:ring-2 focus:ring-[var(--gold)] "
    "mp-field mp-input"
)

TEXTAREA_CLASSES = (
    "block w-full px-4 py-3 text-[var(--brown)] "
    "focus:outline-none focus:ring-2 focus:ring-[var(--gold)] "
    "mp-field mp-textarea"
)


# =====================================================
# MARKETPLACE ORDER FORM (fitur dari branch kamu)
# =====================================================

class MarketplaceOrderForm(forms.ModelForm):
    class Meta:
        model = MarketplaceOrder
        fields = [
            "quantity",
            "recipient_name",
            "phone",
            "address",
            "notes",
        ]
        widgets = {
            "quantity": forms.NumberInput(
                attrs={
                    "min": 1,
                    "class": "w-full rounded-xl border p-3",
                }
            ),
            "recipient_name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border p-3",
                    "placeholder": "Nama penerima",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border p-3",
                    "placeholder": "Nomor WhatsApp",
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "w-full rounded-xl border p-3",
                    "rows": 3,
                    "placeholder": "Alamat lengkap",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "w-full rounded-xl border p-3",
                    "rows": 2,
                    "placeholder": "Catatan tambahan (opsional)",
                }
            ),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity < 1:
            raise forms.ValidationError("Jumlah minimal 1 produk.")
        return quantity


# =====================================================
# PRODUCT FORM (fitur dari main)
# =====================================================

class ProductForm(forms.ModelForm):
    price = forms.IntegerField(
        label="Harga (Rp)",
        min_value=MIN_PRODUCT_PRICE,
        max_value=MAX_PRODUCT_PRICE,
        widget=forms.NumberInput(
            attrs={
                "min": MIN_PRODUCT_PRICE,
                "max": MAX_PRODUCT_PRICE,
                "step": 500,
                "class": FIELD_CLASSES,
                "placeholder": "Contoh: 185000",
            }
        ),
        error_messages={
            "required": "Masukkan harga produk.",
            "min_value": "Harga produk minimal Rp 1.000.",
            "max_value": "Harga produk maksimal Rp 100.000.000.",
            "invalid": "Masukkan harga berupa angka bulat.",
        },
    )

    stock = forms.IntegerField(
        label="Stok",
        min_value=0,
        max_value=MAX_PRODUCT_STOCK,
        initial=1,
        widget=forms.NumberInput(
            attrs={
                "min": 0,
                "max": MAX_PRODUCT_STOCK,
                "class": FIELD_CLASSES,
            }
        ),
        error_messages={
            "required": "Masukkan jumlah stok produk.",
            "min_value": "Stok tidak boleh negatif.",
            "max_value": f"Stok maksimal {MAX_PRODUCT_STOCK}.",
        },
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "motif",
            "category",
            "description",
            "material_source",
            "artisan_origin",
            "badge_status",
            "price",
            "stock",
            "image_url",
        ]
        labels = {
            "name": "Nama Produk",
            "motif": "Motif Batik",
            "category": "Kategori",
            "description": "Deskripsi Karya (opsional)",
            "material_source": "Sumber Kain Upcycle",
            "artisan_origin": "Pengrajin / Asal Daerah",
            "badge_status": "Label Badge (opsional)",
            "image_url": "URL Gambar Produk (opsional)",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "maxlength": 255,
                    "class": FIELD_CLASSES,
                    "placeholder": "Contoh: Tote Bag Parang Rusak",
                }
            ),
            "motif": forms.TextInput(
                attrs={
                    "maxlength": 150,
                    "class": FIELD_CLASSES,
                    "placeholder": "Contoh: Parang Rusak",
                }
            ),
            "category": forms.Select(
                attrs={"class": FIELD_CLASSES}
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "maxlength": DESCRIPTION_MAX_LENGTH,
                    "class": TEXTAREA_CLASSES,
                    "placeholder": "Ceritakan kisah kain bekas dan detail pengerjaan karya ini...",
                }
            ),
            "material_source": forms.TextInput(
                attrs={
                    "maxlength": 255,
                    "class": FIELD_CLASSES,
                    "placeholder": "Contoh: Kain sarung bekas dari Drop-off Solo",
                }
            ),
            "artisan_origin": forms.TextInput(
                attrs={
                    "maxlength": 150,
                    "class": FIELD_CLASSES,
                    "placeholder": "Contoh: Sanggar Laweyan, Surakarta",
                }
            ),
            "badge_status": forms.TextInput(
                attrs={
                    "maxlength": 50,
                    "class": FIELD_CLASSES,
                    "placeholder": "Contoh: Terlaris / Edisi Terbatas",
                }
            ),
            "image_url": forms.URLInput(
                attrs={
                    "maxlength": 500,
                    "class": FIELD_CLASSES,
                    "placeholder": "https://...",
                }
            ),
        }

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean_motif(self):
        return self.cleaned_data["motif"].strip()

    def clean_material_source(self):
        return self.cleaned_data["material_source"].strip()

    def clean_artisan_origin(self):
        return self.cleaned_data["artisan_origin"].strip()

    def clean_badge_status(self):
        value = (self.cleaned_data.get("badge_status") or "").strip()
        return value or None

    def clean_description(self):
        return (self.cleaned_data.get("description") or "").strip()

    def clean_image_url(self):
        url = (self.cleaned_data.get("image_url") or "").strip()
        if not url:
            return None

        parsed = urlparse(url)
        if parsed.scheme.lower() != "https" or not parsed.netloc:
            raise forms.ValidationError(
                "Masukkan URL gambar yang valid dengan protokol https://."
            )
        return url


# =====================================================
# CHECKOUT FORM (fitur dari main)
# =====================================================

class CheckoutForm(forms.ModelForm):
    def __init__(self, *args, product=None, **kwargs):
        self.product = product
        super().__init__(*args, **kwargs)

        self.fields["delivery_method"].choices = Order.DELIVERY_CHOICES
        self.fields["dropoff_point"].queryset = DropOffPoint.objects.all()
        self.fields["dropoff_point"].required = False
        self.fields["dropoff_point"].empty_label = (
            "Pilih titik Drop-off Point"
        )
        self.fields["address"].required = False

        max_qty = MAX_ORDER_QUANTITY
        if self.product is not None and self.product.stock > 0:
            max_qty = min(MAX_ORDER_QUANTITY, self.product.stock)

        self.fields["quantity"].widget.attrs["max"] = max_qty

    class Meta:
        model = Order
        fields = [
            "quantity",
            "delivery_method",
            "dropoff_point",
            "address",
            "whatsapp",
            "notes",
        ]
        labels = {
            "quantity": "Jumlah Produk",
            "delivery_method": "Metode Penerimaan Produk",
            "dropoff_point": "Lokasi Drop-off Point",
            "address": "Alamat Pengiriman Lengkap",
            "whatsapp": "Nomor WhatsApp",
            "notes": "Catatan Pesanan (opsional)",
        }
        error_messages = {
            "notes": {
                "max_length": (
                    f"Catatan maksimal {NOTES_MAX_LENGTH} karakter."
                )
            }
        }
        widgets = {
            "quantity": forms.NumberInput(
                attrs={
                    "min": 1,
                    "max": MAX_ORDER_QUANTITY,
                    "class": FIELD_CLASSES,
                }
            ),
            "delivery_method": forms.RadioSelect(
                attrs={"class": "sr-only"}
            ),
            "dropoff_point": forms.Select(
                attrs={"class": FIELD_CLASSES}
            ),
            "address": forms.TextInput(
                attrs={
                    "maxlength": 255,
                    "class": FIELD_CLASSES,
                    "placeholder": "Masukkan alamat lengkap penerima produk",
                }
            ),
            "whatsapp": forms.TextInput(
                attrs={
                    "type": "tel",
                    "class": FIELD_CLASSES,
                    "placeholder": "Contoh: +6281234567890",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "maxlength": NOTES_MAX_LENGTH,
                    "class": TEXTAREA_CLASSES,
                    "placeholder": "Contoh: bungkus sebagai hadiah atau jam pengambilan...",
                }
            ),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]

        if quantity < 1 or quantity > MAX_ORDER_QUANTITY:
            raise forms.ValidationError(
                f"Jumlah produk harus antara 1 dan {MAX_ORDER_QUANTITY}."
            )

        if self.product is not None:
            if self.product.stock <= 0:
                raise forms.ValidationError(
                    "Stok produk ini sedang habis."
                )

            if quantity > self.product.stock:
                raise forms.ValidationError(
                    f"Jumlah melebihi stok tersedia ({self.product.stock})."
                )

        return quantity

    def clean_whatsapp(self):
        return normalize_indonesian_whatsapp(
            self.cleaned_data["whatsapp"]
        )

    def clean(self):
        cleaned_data = super().clean()

        delivery_method = cleaned_data.get("delivery_method")
        dropoff_point = cleaned_data.get("dropoff_point")
        address = (cleaned_data.get("address") or "").strip()

        if delivery_method == Order.DeliveryMethod.DROP_OFF:
            if not dropoff_point:
                self.add_error(
                    "dropoff_point",
                    "Pilih lokasi Drop-off Point pengambilan produk.",
                )

            cleaned_data["address"] = ""

        elif delivery_method == Order.DeliveryMethod.KURIR:
            if not address:
                self.add_error(
                    "address",
                    "Masukkan alamat pengiriman produk.",
                )

            cleaned_data["address"] = address
            cleaned_data["dropoff_point"] = None

        return cleaned_data
