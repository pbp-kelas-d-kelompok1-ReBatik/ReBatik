
from django.db import models
from django.conf import settings


class StyleOptions(models.Model):
    GENDER_CHOICES = [
        ("women", "Women"),
        ("men", "Men"),
        ("unisex", "Unisex"),
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
    image = models.ImageField(upload_to="style_options/", blank=True)
    is_active = models.BooleanField(default=True)

    @property
    def static_image_path(self):
        if self.image and self.image.name.startswith("img/catalog/"):
            return self.image.name
        return ""

    def __str__(self):
        return f"{self.name} ({self.get_gender_display()})"


class ColorPalette(models.Model):
    name = models.CharField(max_length=70, unique=True)
    description = models.CharField(max_length=150, blank=True)
    colors = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

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


class FashionPreference(models.Model):
    name = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Fashion preference"
        verbose_name_plural = "Fashion preferences"

    def __str__(self):
        return self.name


class RecommendedMotif(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="recommended_motifs/",
        blank=True,
        null=True,
    )
    styles = models.ManyToManyField(
        StyleOptions,
        blank=True,
        related_name="recommended_motifs",
    )
    palettes = models.ManyToManyField(
        ColorPalette,
        blank=True,
        related_name="recommended_motifs",
    )
    fashion_preference = models.ManyToManyField(
        FashionPreference,
        blank=True,
        related_name="recommended_motifs",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Recommended motif"
        verbose_name_plural = "Recommended motifs"

    @property
    def static_image_path(self):
        if self.image and self.image.name.startswith("img/catalog/"):
            return self.image.name
        return ""

    def __str__(self):
        return self.name

