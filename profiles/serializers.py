from django.utils.html import strip_tags
from rest_framework import serializers

from config.api_utils import absolute_image_url
from profiles.models import UserProfile, UserSettings
from profiles.utils import get_user_role


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    role = serializers.SerializerMethodField()

    avatar = serializers.ImageField(
        write_only=True,
        required=False,
        allow_null=True,
    )

    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile

        fields = [
            "id",
            "username",
            "role",
            "display_name",
            "phone_number",
            "address",
            "bio",
            "avatar",
            "avatar_url",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "username",
            "role",
            "avatar_url",
            "created_at",
            "updated_at",
        ]

    def validate_display_name(self, value):
        value = strip_tags(value).strip()

        if not value:
            raise serializers.ValidationError(
                "Nama tampilan tidak boleh kosong."
            )

        return value

    def validate_phone_number(self, value):
        return strip_tags(value).strip()

    def validate_address(self, value):
        return strip_tags(value).strip()

    def validate_bio(self, value):
        return strip_tags(value).strip()

    def validate_avatar(self, value):
        if value and value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                "Ukuran foto profil maksimal 5 MB."
            )

        return value

    def get_role(self, obj):
        return get_user_role(obj.user)

    def get_avatar_url(self, obj):
        return absolute_image_url(
            self.context.get("request"),
            obj.avatar,
        )


class UserSettingsSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserSettings

        fields = [
            "order_notifications",
            "activity_notifications",
            "promotional_notifications",
            "email_notifications",
            "updated_at",
        ]

        read_only_fields = [
            "updated_at",
        ]