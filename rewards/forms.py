from django import forms

from .models import Reward


class RewardAdminForm(forms.ModelForm):
    class Meta:
        model = Reward
        fields = "__all__"
        labels = {
            "name": "Nama voucher",
            "description": "Deskripsi",
            "reward_type": "Jenis reward",
            "points_required": "Poin untuk menukar",
            "stock": "Jumlah voucher tersedia",
            "is_active": "Tampilkan di katalog",
            "discount_value": "Nilai diskon (Rp)",
            "image": "Gambar voucher",
        }
        help_texts = {
            "name": "Gunakan nama singkat yang akan tampil di katalog.",
            "description": "Jelaskan syarat atau cara menggunakan voucher.",
            "points_required": "Jumlah poin yang harus dimiliki pengguna untuk menukar voucher ini.",
            "stock": "Voucher hanya tampil di katalog jika jumlahnya lebih dari 0.",
            "is_active": "Matikan opsi ini untuk menyembunyikan voucher dari katalog.",
            "discount_value": "Isi nominal potongan harga dalam rupiah.",
            "image": "Opsional. Unggah gambar kecil berbentuk JPG, PNG, atau WebP.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["reward_type"].initial = Reward.Type.VOUCHER
            self.fields["reward_type"].choices = [
                (value, label)
                for value, label in self.fields["reward_type"].choices
                if value == Reward.Type.VOUCHER
            ]

    def clean_reward_type(self):
        """Prevent changing the type of a reward that has been redeemed."""
        reward_type = self.cleaned_data["reward_type"]
        if self.instance.pk and self.instance.redemptions.exists() and reward_type != self.instance.reward_type:
            raise forms.ValidationError("Jenis reward tidak dapat diubah setelah pernah ditukar.")
        return reward_type

    def clean(self):
        cleaned = super().clean()
        reward_type = cleaned.get("reward_type")
        is_active = cleaned.get("is_active")
        discount_value = cleaned.get("discount_value")

        if reward_type == Reward.Type.PHYSICAL:
            if not self.instance.pk:
                self.add_error("reward_type", "Reward baru hanya dapat berupa voucher.")
            elif is_active:
                self.add_error(
                    "is_active",
                    "Reward fisik lama harus dinonaktifkan dan tidak dapat ditawarkan lagi.",
                )
        elif reward_type == Reward.Type.VOUCHER and is_active:
            if discount_value is None or discount_value <= 0:
                self.add_error(
                    "discount_value",
                    "Voucher aktif harus memiliki nilai diskon lebih dari nol.",
                )
        return cleaned
