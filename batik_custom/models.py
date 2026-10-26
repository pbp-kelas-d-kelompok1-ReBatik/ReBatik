from django.db import models
from django.conf import settings

# Create your models here.

class StyleOptions(models.Model):
    GENDER_CHOICES = [
        ("women", "Women"),
        ("men", "Men"),
        ("unisex","Unisex")
    ]

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    detail = models.CharField(max_length=400)
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        default="women",
    )
    icon = models.CharField(max_length=50, blank=True)
    image = models.ImageField(
        upload_to="style_options/",
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_gender_display()})"
    
class ColorPalette(models.Model):
    name=models.CharField(max_length=70, unique=True)
    description=models.CharField(max_length=150, blank=True)
    colors=models.JSONField(default=list)
    is_active=models.BooleanField(default=True)

    def __str__(self):
        return self.name


class StyleProfile(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="batik_style_profiles",
    )

    style = models.ForeignKey(
        StyleOptions,
        on_delete=models.PROTECT,
        related_name="profiles",
    )

    palette = models.ForeignKey(
        ColorPalette,
        on_delete=models.PROTECT,
        related_name="profiles",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.style.name}"