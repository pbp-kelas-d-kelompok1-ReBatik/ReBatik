from django import forms

from .models import UserProfile, UserSettings


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile

        fields = [
            "display_name",
            "phone_number",
            "address",
            "bio",
            "avatar",
        ]

        widgets = {
            "display_name": forms.TextInput(attrs={
                "class": "profile-input",
                "placeholder": "Nama yang ingin ditampilkan",
            }),
            "phone_number": forms.TextInput(attrs={
                "class": "profile-input",
                "placeholder": "Nomor telepon",
            }),
            "address": forms.Textarea(attrs={
                "class": "profile-input",
                "rows": 3,
                "placeholder": "Alamat kamu",
            }),
            "bio": forms.Textarea(attrs={
                "class": "profile-input",
                "rows": 3,
                "placeholder": "Ceritakan sedikit tentang dirimu",
            }),
            "avatar": forms.ClearableFileInput(attrs={
                "class": "profile-input",
                "accept": "image/*",
            }),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")

        if avatar and avatar.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "Ukuran foto profil maksimal 5 MB."
            )

        return avatar

class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = [
            "order_notifications",
            "activity_notifications",
            "promotional_notifications",
            "email_notifications",
        ]
        labels = {
            "order_notifications": "Pesanan dan pembayaran",
            "activity_notifications": "Aktivitas donasi dan upcycling",
            "promotional_notifications": "Promo dan informasi ReBatik",
            "email_notifications": "Kirim notifikasi melalui email",
        }
