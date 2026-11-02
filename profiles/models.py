from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    display_name = models.CharField(
        max_length=100,
        verbose_name="Nama tampilan",
    )

    phone_number = models.CharField(
        max_length=25,
        blank=True,
        verbose_name="Nomor telepon",
    )

    address = models.TextField(
        blank=True,
        verbose_name="Alamat",
    )

    bio = models.TextField(
        max_length=300,
        blank=True,
        verbose_name="Tentang saya",
    )

    avatar = models.ImageField(
        upload_to="profiles/avatars/",
        blank=True,
        null=True,
        verbose_name="Foto profil",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Profil pengguna"
        verbose_name_plural = "Profil pengguna"
        ordering = ["display_name"]

    def __str__(self):
        return f"{self.display_name} ({self.user.username})"