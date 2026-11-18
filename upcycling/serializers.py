import re

from rest_framework import serializers

from .models import (
    AdditionalFabricPhoto,
    AdditionalReferencePhoto,
    NOTES_MAX_LENGTH,
    UpcyclingRequest,
    UpcyclingStatusHistory,
)


class UpcyclingRequestCreateSerializer(serializers.ModelSerializer):
    """Validate client input and create an upcycling request through DRF."""

    # The website form marks these fields as required even though the model
    # allows defaults or blank values for some of them.
    current_item_form = serializers.ChoiceField(
        choices=UpcyclingRequest.CurrentItemForm.choices,
        required=True,
    )
    has_batik_pattern = serializers.ChoiceField(
        choices=UpcyclingRequest.BatikPatternStatus.choices,
        required=True,
    )
    quantity = serializers.IntegerField(
        min_value=1,
        max_value=20,
        required=True,
    )

    # ListField reads repeated multipart fields such as fabric_photos=file1,
    # fabric_photos=file2, which is how Postman sends multiple uploaded files.
    fabric_photos = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        allow_empty=False,
        min_length=1,
        max_length=3,
    )
    reference_photos = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        default=list,
        max_length=3,
    )

    class Meta:
        model = UpcyclingRequest
        fields = [
            "fabric",
            "fabric_other_description",
            "current_item_form",
            "current_item_form_other",
            "has_batik_pattern",
            "fabric_condition",
            "fabric_dimensions",
            "category",
            "product",
            "custom_product",
            "wants_batik_accent",
            "batik_motif",
            "motif_placement",
            "quantity",
            "notes",
            "whatsapp",
            "fabric_photos",
            "reference_photos",
        ]

    def validate_fabric_photos(self, photos):
        for photo in photos:
            if photo.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    "Ukuran setiap foto barang atau kain maksimal 5 MB."
                )
        return photos

    def validate_reference_photos(self, photos):
        for photo in photos:
            if photo.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    "Ukuran setiap foto referensi maksimal 5 MB."
                )
        return photos

    def validate_whatsapp(self, value):
        normalized = re.sub(r"[\s().-]", "", value)
        if not re.fullmatch(r"(?:0|\+?62)8[1-9][0-9]{7,10}", normalized):
            raise serializers.ValidationError(
                "Masukkan nomor HP Indonesia yang valid, misalnya +6281234567890."
            )

        if normalized.startswith("0"):
            return f"+62{normalized[1:]}"
        if normalized.startswith("62"):
            return f"+{normalized}"
        return normalized

    def validate(self, attrs):
        # These values are also used by the website form; keep its limits.
        if len(attrs.get("notes", "")) > NOTES_MAX_LENGTH:
            raise serializers.ValidationError(
                {"notes": f"Catatan maksimal {NOTES_MAX_LENGTH} karakter."}
            )

        fabric = attrs.get("fabric")
        other_fabric = attrs.get("fabric_other_description", "").strip()
        if fabric == UpcyclingRequest.FabricType.OTHER and not other_fabric:
            raise serializers.ValidationError(
                {"fabric_other_description": "Sebutkan bahan lainnya."}
            )
        attrs["fabric_other_description"] = (
            other_fabric
            if fabric == UpcyclingRequest.FabricType.OTHER
            else ""
        )

        item_form_other = attrs.get("current_item_form_other", "").strip()
        if (
            attrs.get("current_item_form") == UpcyclingRequest.CurrentItemForm.OTHER
            and not item_form_other
        ):
            raise serializers.ValidationError(
                {"current_item_form_other": "Sebutkan bentuk barang lainnya."}
            )
        attrs["current_item_form_other"] = (
            item_form_other
            if attrs.get("current_item_form") == UpcyclingRequest.CurrentItemForm.OTHER
            else ""
        )

        custom_product = attrs.get("custom_product", "").strip()
        if attrs.get("product") == "LAINNYA" and not custom_product:
            raise serializers.ValidationError(
                {"custom_product": "Tuliskan produk yang Anda inginkan."}
            )
        attrs["custom_product"] = (
            custom_product if attrs.get("product") == "LAINNYA" else ""
        )

        products_by_category = {
            "TAS": ("TOTE_BAG", "SLING_BAG", "BACKPACK", "SHOULDER_BAG", "LAINNYA"),
            "POUCH": ("POUCH", "PENCIL_CASE", "MAKEUP_POUCH", "LAPTOP_SLEEVE", "LAINNYA"),
            "PAKAIAN": ("KEMEJA", "OUTER", "ROK", "LAINNYA"),
            "AKSESORIS": ("AKSESORIS", "SCRUNCHIE", "BUCKET_HAT", "HEADBAND", "KEYCHAIN", "LAINNYA"),
            "RUMAH_TANGGA": ("SARUNG_BANTAL", "LAINNYA"),
            "LAINNYA": ("LAINNYA",),
        }
        if attrs.get("product") not in products_by_category.get(attrs.get("category"), ()):
            raise serializers.ValidationError(
                {"product": "Model produk tidak sesuai dengan kategori yang dipilih."}
            )

        if not attrs.get("wants_batik_accent"):
            attrs["batik_motif"] = ""
            attrs["motif_placement"] = ""

        return attrs

    def create(self, validated_data):
        user = validated_data.pop("user")
        fabric_photos = validated_data.pop("fabric_photos")
        reference_photos = validated_data.pop("reference_photos", [])
        upcycling_request = UpcyclingRequest.objects.create(
            user=user,
            status=UpcyclingRequest.Status.PENDING_ASSIGNMENT,
            **validated_data,
        )

        if fabric_photos:
            upcycling_request.fabric_photo = fabric_photos[0]
            upcycling_request.save(update_fields=("fabric_photo", "updated_at"))

            AdditionalFabricPhoto.objects.bulk_create(
                [
                    AdditionalFabricPhoto(request=upcycling_request, image=photo)
                    for photo in fabric_photos[1:]
                ]
            )

        AdditionalReferencePhoto.objects.bulk_create(
            [
                AdditionalReferencePhoto(request=upcycling_request, image=photo)
                for photo in reference_photos
            ]
        )

        UpcyclingStatusHistory.objects.create(
            request=upcycling_request,
            to_status=upcycling_request.status,
            changed_by=user,
        )
        return upcycling_request

class UpcyclingRequestListSerializer(serializers.ModelSerializer):
    reference_code = serializers.CharField(read_only=True)
    fabric_label = serializers.CharField(source="get_fabric_display", read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    product_name = serializers.CharField(source="get_product_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = UpcyclingRequest
        fields = [
            "id",
            "reference_code",
            "fabric",
            "fabric_label",
            "category",
            "category_label",
            "product",
            "product_name",
            "quantity",
            "status",
            "status_label",
            "created_at",
            "updated_at",
            "fabric_photo"
        ]

class UpcyclingRequestDetailSerializer(serializers.ModelSerializer):
    reference_code = serializers.CharField(read_only=True)
    product_name = serializers.CharField(
        source="get_product_name",
        read_only=True,
    )

    fabric_label = serializers.CharField(
        source="get_fabric_display",
        read_only=True,
    )
    current_item_form_label = serializers.CharField(
        source="get_current_item_form_display",
        read_only=True,
    )
    has_batik_pattern_label = serializers.CharField(
        source="get_has_batik_pattern_display",
        read_only=True,
    )
    category_label = serializers.CharField(
        source="get_category_display",
        read_only=True,
    )
    status_label = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    delivery_method_label = serializers.CharField(
        source="get_delivery_method_display",
        read_only=True,
    )
    fabric_delivery_method_label = serializers.CharField(
        source="get_fabric_delivery_method_display",
        read_only=True,
    )
    return_status_label = serializers.CharField(
        source="get_return_status_display",
        read_only=True,
    )

    fabric_photos = serializers.SerializerMethodField()
    reference_photos = serializers.SerializerMethodField()
    status_timeline = serializers.SerializerMethodField()

    class Meta:
        model = UpcyclingRequest
        fields = [
            "id",
            "reference_code",
            "product_name",
            "created_at",
            "status",
            "status_label",
            "status_timeline",
            "fabric_photos",
            "reference_photos",
            "fabric",
            "fabric_label",
            "fabric_other_description",
            "current_item_form",
            "current_item_form_label",
            "current_item_form_other",
            "has_batik_pattern",
            "has_batik_pattern_label",
            "fabric_composition",
            "wants_batik_accent",
            "batik_motif",
            "motif_placement",
            "design_notes",
            "fabric_dimensions",
            "quoted_price",
            "work_price",
            "batik_material_price",
            "additional_fee_type",
            "additional_fee_amount",
            "quotation_notes",
            "review_notes",
            "delivery_proof",
            "fabric_deadline",
            "return_status",
            "return_status_label",
            "fabric_delivery_method",
            "fabric_delivery_method_label",
            "fabric_delivery_location",
            "cancellation_reason",
            "category",
            "category_label",
            "product",
            "quantity",
            "delivery_method",
            "delivery_method_label",
            "address",
            "notes",
            "rejection_reason",
            "fabric_received_at",
            "approved_at",
        ]

    def _file_url(self, file_field):
        if not file_field:
            return None

        url = file_field.url
        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(url)

        return url

    def get_fabric_photos(self, obj):
        photos = []

        if obj.fabric_photo:
            photos.append(obj.fabric_photo)

        photos.extend(
            photo.image
            for photo in obj.additional_fabric_photos.all()
        )

        return [
            self._file_url(photo)
            for photo in photos
            if photo
        ]

    def get_reference_photos(self, obj):
        return [
            self._file_url(photo.image)
            for photo in obj.reference_photos.all()
            if photo.image
        ]

    def get_status_timeline(self, obj):
        status_dates = {
            item.to_status: item.changed_at
            for item in obj.status_history.all()
        }

        progression = [
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
            UpcyclingRequest.Status.PENDING_REVIEW,
            UpcyclingRequest.Status.AWAITING_FABRIC,
            UpcyclingRequest.Status.INSPECTION,
            UpcyclingRequest.Status.AWAITING_APPROVAL,
            UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS,
            UpcyclingRequest.Status.IN_PROGRESS,
            UpcyclingRequest.Status.READY,
            UpcyclingRequest.Status.COMPLETED,
        ]

        timeline = [
            {
                "label": "Diajukan",
                "created_at": obj.created_at,
                "state": "done",
            }
        ]

        if obj.status in progression:
            current_index = progression.index(obj.status)

            for index, status in enumerate(progression):
                timeline.append(
                    {
                        "label": UpcyclingRequest.Status(status).label,
                        "status": status,
                        "state": (
                            "done"
                            if (
                                obj.status == UpcyclingRequest.Status.COMPLETED
                                or index < current_index
                            )
                            else "current"
                            if index == current_index
                            else "upcoming"
                        ),
                        "created_at": status_dates.get(status),
                    }
                )
        else:
            timeline.append(
                {
                    "label": obj.get_status_display(),
                    "status": obj.status,
                    "created_at": status_dates.get(obj.status),
                    "state": "cancelled",
                }
            )

        return timeline
