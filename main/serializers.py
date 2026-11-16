from rest_framework import serializers

from main.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Representasi notifikasi untuk klien (Flutter). Semua field hanya-baca."""

    class Meta:
        model = Notification
        fields = [
            "id", "title", "message", "notification_type",
            "target_url", "is_read", "created_at",
        ]
        read_only_fields = fields
