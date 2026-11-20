from django.utils.html import strip_tags
from rest_framework import serializers

from config.api_utils import absolute_image_url
from batik_story.models import BatikMotif


class BatikMotifSerializer(serializers.ModelSerializer):
    # Identitas publik motif adalah id_story (UUID), sama seperti URL di web.
    id = serializers.UUIDField(source="id_story", read_only=True)
    asal_display = serializers.CharField(source="get_asal_display", read_only=True)
    gambar_url = serializers.SerializerMethodField()
    favorite_count = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = BatikMotif
        fields = [
            "id", "nama", "asal", "asal_display", "deskripsi", "filosofi",
            "gambar_url", "favorite_count", "is_favorited",
        ]

    def validate_nama(self, value):
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Nama motif tidak boleh kosong.")
        return value

    def validate_deskripsi(self, value):
        return strip_tags(value).strip()

    def validate_filosofi(self, value):
        return strip_tags(value).strip()

    def get_gambar_url(self, obj):
        return absolute_image_url(self.context.get("request"), obj.gambar)

    def get_favorite_count(self, obj):
        return obj.favorited_by.count()

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        return request.user in obj.favorited_by.all()
