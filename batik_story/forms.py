from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .models import DonasiKain


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={
            "placeholder": "Masukkan username anda",
            "autocomplete": "username",
        })
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Masukkan password anda",
            "autocomplete": "current-password",
        })
    )


class SignUpForm(UserCreationForm):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={
            "placeholder": "Masukkan username anda",
            "autocomplete": "username",
        })
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Masukkan password anda",
            "autocomplete": "new-password",
        })
    )

    password2 = forms.CharField(
        label="Konfirmasi Password",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Masukkan kembali password anda",
            "autocomplete": "new-password",
        })
    )
from .models import BatikMotif

class BatikMotifForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "password1", "password2")





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
            "donor_name": forms.TextInput(
                attrs={"class": "donasi-input"}
            ),
            "whatsapp": forms.TextInput(
                attrs={"class": "donasi-input"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "donasi-input"}
            ),
            "address": forms.Textarea(
                attrs={"class": "donasi-input", "rows": 3}
            ),
            "city": forms.TextInput(
                attrs={"class": "donasi-input"}
            ),
            "item_name": forms.TextInput(
                attrs={"class": "donasi-input"}
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": "donasi-input",
                    "min": 1,
                    "step": 1,
                }
            ),
            "description": forms.Textarea(
                attrs={"class": "donasi-input", "rows": 4}
            ),
            "photo": forms.ClearableFileInput(
                attrs={"class": "donasi-file-input", "accept": "image/*"}
            ),
            "pickup_date": forms.DateInput(
                attrs={"class": "donasi-input", "type": "date"}
            ),
            "additional_notes": forms.Textarea(
                attrs={"class": "donasi-input", "rows": 3}
            ),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")

        if photo and photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "Ukuran foto maksimal 5 MB."
            )

        return photo
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
