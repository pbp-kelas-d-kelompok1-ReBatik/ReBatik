from django import forms

from .models import BatikMotif


class BatikMotifForm(forms.ModelForm):
    class Meta:
        model = BatikMotif
        fields = [
            "nama",
            "asal",
            "gambar",
            "deskripsi",
            "filosofi",
        ]

        labels = {
            "nama": "Nama Motif Batik",
            "asal": "Asal Daerah",
            "gambar": "Foto Motif Batik",
            "deskripsi": "Deskripsi Singkat",
            "filosofi": "Filosofi dan Makna",
        }

        widgets = {
            "nama": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Contoh: Batik Kawung",
            }),
            "asal": forms.Select(attrs={
                "class": "form-input",
            }),
            "gambar": forms.ClearableFileInput(attrs={
                "class": "form-input",
                "accept": "image/*",
            }),
            "deskripsi": forms.Textarea(attrs={
                "class": "form-input",
                "placeholder": "Ceritakan deskripsi motif batik...",
                "rows": 3,
            }),
            "filosofi": forms.Textarea(attrs={
                "class": "form-input",
                "placeholder": "Jelaskan filosofi dan makna motif...",
                "rows": 5,
            }),
        }
