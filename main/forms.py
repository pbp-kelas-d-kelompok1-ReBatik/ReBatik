from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


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

    class Meta:
        model = User
        fields = ("username", "password1", "password2")