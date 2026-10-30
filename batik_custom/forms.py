"""Form untuk membuat dan mengubah desain pola."""
from django import forms
from django.core.validators import RegexValidator

from .models import BatikOrder, ColorPalette, ProductDesignOption, RecommendedMotif, SavedDesign

FIELD = (
    "w-full rounded-lg border border-stone-300 bg-white "
    "px-3 py-2 focus:border-amber-800 focus:outline-none"
)
RANGE = "w-full accent-amber-900"
ROTATIONS = [
    (0, "0°"),
    (90, "90°"),
    (180, "180°"),
    (270, "270°"),
]


class DesignSettingsForm(forms.ModelForm):
    """Pengaturan desain untuk halaman edit."""

    scale = forms.IntegerField(
        label="Ukuran motif (%)",
        min_value=40,
        max_value=220,
        widget=forms.NumberInput(attrs={
            "type": "range",
            "min": 40,
            "max": 220,
            "step": 5,
            "class": RANGE,
        }),
    )

    rotation = forms.TypedChoiceField(
        label="Rotasi",
        choices=ROTATIONS,
        coerce=int,
        widget=forms.Select(attrs={"class": FIELD}),
    )

    gap = forms.IntegerField(
        label="Jarak antar motif (px)",
        min_value=0,
        max_value=60,
        widget=forms.NumberInput(attrs={
            "type": "range",
            "min": 0,
            "max": 60,
            "step": 2,
            "class": RANGE,
        }),
    )

    color = forms.CharField(
        label="Warna",
        max_length=7,
        validators=[
            RegexValidator(
                r"^#[0-9a-fA-F]{6}$",
                "Warna harus berformat #RRGGBB.",
            )
        ],
        widget=forms.TextInput(attrs={
            "type": "color",
            "class": "h-10 w-24 rounded border border-stone-300 bg-white",
        }),
    )

    tint = forms.IntegerField(
        label="Intensitas warna (%)",
        min_value=0,
        max_value=70,
        widget=forms.NumberInput(attrs={
            "type": "range",
            "min": 0,
            "max": 70,
            "step": 5,
            "class": RANGE,
        }),
    )

    class Meta:
        model = SavedDesign
        fields = [
            "title",
            "layout",
            "scale",
            "rotation",
            "gap",
            "color",
            "tint",
            "is_public",
        ]
        labels = {
            "title": "Judul desain",
            "layout": "Susunan",
            "is_public": "Boleh dilihat lewat tautan bagikan",
        }
        widgets = {
            "title": forms.TextInput(attrs={
                "class": FIELD,
                "placeholder": "Mis. Kawung untuk kemeja",
            }),
            "layout": forms.Select(attrs={"class": FIELD}),
            "is_public": forms.CheckboxInput(attrs={
                "class": "h-4 w-4 accent-amber-900",
            }),
        }


class DesignCreateForm(DesignSettingsForm):
    """Form untuk menyimpan desain melalui endpoint JSON."""

    motif = forms.ModelChoiceField(
        queryset=RecommendedMotif.objects.filter(is_active=True)
    )
    palette = forms.ModelChoiceField(
        queryset=ColorPalette.objects.filter(is_active=True),
        required=False,
    )

    class Meta(DesignSettingsForm.Meta):
        fields = DesignSettingsForm.Meta.fields + [
            "motif",
            "palette",
        ]


class DesignOptionSelect(forms.Select):
    """Select yang menambahkan data-product-type pada setiap <option>.

    Atribut ini dipakai JavaScript untuk menyaring model produk
    berdasarkan jenis produk yang dipilih.
    """

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex, attrs
        )
        instance = getattr(value, "instance", None)  # Django 3.1+
        if instance is not None:
            option["attrs"]["data-product-type"] = instance.product_type
        return option


class BatikOrderForm(forms.Form):
    """Form pemesanan produk batik custom."""

    product_type = forms.ChoiceField(
        label="Jenis Produk",
        choices=ProductDesignOption.PRODUCT_CHOICES,
        widget=forms.Select(attrs={
            "class": FIELD,
            "id": "id_product_type",
        }),
    )

    design_option = forms.ModelChoiceField(
        label="Model Produk",
        queryset=ProductDesignOption.objects.none(),
        empty_label="Pilih model produk",
        widget=DesignOptionSelect(attrs={
            "class": FIELD,
            "id": "id_design_option",
        }),
    )

    material = forms.ChoiceField(
        label="Bahan",
        choices=[
            ("Katun Premium", "Katun Premium"),
            ("Katun Poplin", "Katun Poplin"),
            ("Rayon", "Rayon"),
            ("Satin", "Satin"),
        ],
        widget=forms.Select(attrs={"class": FIELD}),
    )

    size = forms.ChoiceField(
        label="Ukuran",
        required=False,
        choices=[
            ("", "Pilih ukuran"),
            ("S", "S"),
            ("M", "M"),
            ("L", "L"),
            ("XL", "XL"),
            ("XXL", "XXL"),
        ],
        widget=forms.Select(attrs={"class": FIELD}),
    )

    sleeve_type = forms.ChoiceField(
        label="Model Lengan",
        required=False,
        choices=[
            ("", "Tidak berlaku"),
            ("short", "Lengan pendek"),
            ("long", "Lengan panjang"),
            ("sleeveless", "Tanpa lengan"),
        ],
        widget=forms.Select(attrs={"class": FIELD}),
    )

    fit_type = forms.ChoiceField(
        label="Potongan Pakaian",
        required=False,
        choices=[
            ("", "Pilih potongan"),
            ("regular", "Regular fit"),
            ("slim", "Slim fit"),
            ("oversized", "Oversized"),
            ("loose", "Loose fit"),
        ],
        widget=forms.Select(attrs={"class": FIELD}),
    )

    motif_placement = forms.ChoiceField(
        label="Posisi Motif",
        required=False,
        choices=[
            ("", "Pilih posisi motif"),
            ("all_over", "Seluruh permukaan"),
            ("front", "Bagian depan"),
            ("back", "Bagian belakang"),
            ("sleeve", "Bagian lengan"),
            ("border", "Bagian tepi"),
        ],
        widget=forms.Select(attrs={"class": FIELD}),
    )

    custom_requirements = forms.CharField(
        label="Detail Custom",
        required=False,
        widget=forms.Textarea(attrs={
            "class": FIELD,
            "rows": 3,
            "placeholder": (
                "Tuliskan detail desain yang diinginkan, "
                "misalnya warna, ukuran khusus, atau perubahan motif."
            ),
        }),
    )

    quantity = forms.IntegerField(
        label="Jumlah",
        min_value=1,
        max_value=100,
        initial=1,
        widget=forms.NumberInput(attrs={
            "class": FIELD,
            "min": 1,
            "max": 100,
        }),
    )

    unit = forms.ChoiceField(
        label="Satuan",
        choices=[
            ("pcs", "Pcs"),
            ("meter", "Meter"),
        ],
        initial="pcs",
        widget=forms.Select(attrs={"class": FIELD}),
    )

    notes = forms.CharField(
        label="Catatan Tambahan",
        required=False,
        widget=forms.Textarea(attrs={
            "class": FIELD,
            "rows": 3,
            "placeholder": "Catatan tambahan untuk pesanan kamu...",
        }),
    )

    recipient_name = forms.CharField(
        label="Nama Penerima",
        max_length=120,
        widget=forms.TextInput(attrs={
            "class": FIELD,
            "placeholder": "Nama lengkap penerima",
            "autocomplete": "name",
        }),
    )

    phone = forms.CharField(
        label="Nomor Telepon",
        max_length=30,
        widget=forms.TextInput(attrs={
            "class": FIELD,
            "type": "tel",
            "placeholder": "Contoh: 081234567890",
            "autocomplete": "tel",
        }),
    )

    address = forms.CharField(
        label="Alamat Lengkap",
        widget=forms.Textarea(attrs={
            "class": FIELD,
            "rows": 3,
            "placeholder": "Jalan, nomor rumah, RT/RW, kelurahan...",
            "autocomplete": "street-address",
        }),
    )

    province = forms.CharField(
        label="Provinsi",
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": FIELD,
            "placeholder": "Contoh: DKI Jakarta",
            "autocomplete": "address-level1",
        }),
    )

    city = forms.CharField(
        label="Kota/Kabupaten",
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": FIELD,
            "placeholder": "Contoh: Jakarta Barat",
            "autocomplete": "address-level2",
        }),
    )

    district = forms.CharField(
        label="Kecamatan",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": FIELD,
            "placeholder": "Nama kecamatan",
        }),
    )

    postal_code = forms.CharField(
        label="Kode Pos",
        max_length=10,
        widget=forms.TextInput(attrs={
            "class": FIELD,
            "inputmode": "numeric",
            "placeholder": "Contoh: 11630",
            "autocomplete": "postal-code",
        }),
    )

    payment_method = forms.ChoiceField(
        label="Metode Pembayaran",
        choices=BatikOrder.PAYMENT_CHOICES,
        widget=forms.Select(attrs={"class": FIELD}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Semua model aktif dirender; JavaScript menyaringnya per jenis
        # produk, dan clean() memvalidasi kecocokannya di server.
        self.fields["design_option"].queryset = (
            ProductDesignOption.objects.filter(is_active=True)
        )

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", FIELD)

    def clean(self):
        cleaned_data = super().clean()

        product_type = cleaned_data.get("product_type")
        design_option = cleaned_data.get("design_option")

        if design_option and product_type:
            if design_option.product_type != product_type:
                self.add_error(
                    "design_option",
                    "Pilih model yang sesuai dengan jenis produk.",
                )

        return cleaned_data