
"""Form untuk membuat dan mengubah desain pola."""
from django import forms
from django.core.validators import RegexValidator

from .models import ColorPalette, RecommendedMotif, SavedDesign

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
