import re
from decimal import Decimal

from rest_framework import serializers

from .models import (
    AdditionalFabricPhoto,
    AdditionalReferencePhoto,
    NOTES_MAX_LENGTH,
    UpcyclingRequest,
    UpcyclingStatusHistory,
)
from .services import eligible_artisans_for_request
from .views import _parse_quote_component


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
        fields = (
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
        )

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

        def current_value(field, default=""):
            if field in attrs:
                return attrs[field]
            if self.instance is not None:
                return getattr(self.instance, field)
            return default

        fabric = current_value("fabric")
        other_fabric = current_value("fabric_other_description").strip()
        if fabric == UpcyclingRequest.FabricType.OTHER and not other_fabric:
            raise serializers.ValidationError(
                {"fabric_other_description": "Sebutkan bahan lainnya."}
            )
        if (
            self.instance is None
            or "fabric" in attrs
            or "fabric_other_description" in attrs
        ):
            attrs["fabric_other_description"] = (
                other_fabric
                if fabric == UpcyclingRequest.FabricType.OTHER
                else ""
            )

        current_item_form = current_value("current_item_form")
        item_form_other = current_value("current_item_form_other").strip()
        if (
            current_item_form == UpcyclingRequest.CurrentItemForm.OTHER
            and not item_form_other
        ):
            raise serializers.ValidationError(
                {"current_item_form_other": "Sebutkan bentuk barang lainnya."}
            )
        if (
            self.instance is None
            or "current_item_form" in attrs
            or "current_item_form_other" in attrs
        ):
            attrs["current_item_form_other"] = (
                item_form_other
                if current_item_form == UpcyclingRequest.CurrentItemForm.OTHER
                else ""
            )

        product = current_value("product")
        custom_product = current_value("custom_product").strip()
        if product == "LAINNYA" and not custom_product:
            raise serializers.ValidationError(
                {"custom_product": "Tuliskan produk yang Anda inginkan."}
            )
        if (
            self.instance is None
            or "product" in attrs
            or "custom_product" in attrs
        ):
            attrs["custom_product"] = custom_product if product == "LAINNYA" else ""

        products_by_category = {
            "TAS": ("TOTE_BAG", "SLING_BAG", "BACKPACK", "SHOULDER_BAG", "LAINNYA"),
            "POUCH": ("POUCH", "PENCIL_CASE", "MAKEUP_POUCH", "LAPTOP_SLEEVE", "LAINNYA"),
            "PAKAIAN": ("KEMEJA", "OUTER", "ROK", "LAINNYA"),
            "AKSESORIS": ("AKSESORIS", "SCRUNCHIE", "BUCKET_HAT", "HEADBAND", "KEYCHAIN", "LAINNYA"),
            "RUMAH_TANGGA": ("SARUNG_BANTAL", "LAINNYA"),
            "LAINNYA": ("LAINNYA",),
        }
        category = current_value("category")
        if product not in products_by_category.get(category, ()):
            raise serializers.ValidationError(
                {"product": "Model produk tidak sesuai dengan kategori yang dipilih."}
            )

        wants_batik_accent = current_value("wants_batik_accent", False)
        if not wants_batik_accent:
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


class UpcyclingRequestUpdateSerializer(UpcyclingRequestCreateSerializer):
    """Validate partial edits and append photos without removing old uploads."""

    fabric_photos = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=3,
    )

    def validate_fabric_photos(self, photos):
        super().validate_fabric_photos(photos)
        existing_count = int(bool(self.instance.fabric_photo)) + (
            self.instance.additional_fabric_photos.count()
        )
        if existing_count + len(photos) > 3:
            raise serializers.ValidationError(
                "Jumlah foto barang atau kain maksimal 3. Foto yang sudah tersimpan tetap dihitung."
            )
        return photos

    def validate_reference_photos(self, photos):
        super().validate_reference_photos(photos)
        if self.instance.reference_photos.count() + len(photos) > 3:
            raise serializers.ValidationError("Foto referensi maksimal 3 gambar.")
        return photos

    def update(self, instance, validated_data):
        fabric_photos = validated_data.pop("fabric_photos", [])
        reference_photos = validated_data.pop("reference_photos", [])

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if fabric_photos:
            if not instance.fabric_photo:
                instance.fabric_photo = fabric_photos[0]
                instance.save(update_fields=("fabric_photo", "updated_at"))
                fabric_photos = fabric_photos[1:]
            AdditionalFabricPhoto.objects.bulk_create(
                [
                    AdditionalFabricPhoto(request=instance, image=photo)
                    for photo in fabric_photos
                ]
            )

        AdditionalReferencePhoto.objects.bulk_create(
            [
                AdditionalReferencePhoto(request=instance, image=photo)
                for photo in reference_photos
            ]
        )
        return instance


class FabricHandoffSerializer(serializers.Serializer):
    """Validate the owner's fabric delivery method and optional location note."""

    fabric_delivery_method = serializers.ChoiceField(
        choices=UpcyclingRequest.FabricDeliveryMethod.choices,
    )
    fabric_delivery_location = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )


class ProductDeliverySerializer(serializers.Serializer):
    """Validate the owner's chosen method and address for product delivery."""

    delivery_method = serializers.ChoiceField(
        choices=UpcyclingRequest.DELIVERY_CHOICES,
    )
    address = serializers.CharField(max_length=255)


class CancelUpcyclingRequestSerializer(serializers.Serializer):
    """Distinguish a normal cancellation from rejecting a pending quote."""

    action = serializers.ChoiceField(
        choices=("cancel", "reject_quote"),
        required=False,
        default="cancel",
    )


class ArtisanRequestActionSerializer(serializers.Serializer):
    """Validate artisan workflow actions and inspection quote components."""

    action = serializers.ChoiceField(
        choices=(
            "review_accept",
            "review_reject",
            "receive_fabric",
            "inspection_pass",
            "inspection_reject",
            "mark_ready",
        )
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    work_price = serializers.CharField(required=False, allow_blank=True)
    batik_material_price = serializers.CharField(required=False, allow_blank=True)
    additional_fee_type = serializers.CharField(required=False, allow_blank=True)
    additional_fee_amount = serializers.CharField(required=False, allow_blank=True)

    def validate_notes(self, value):
        return value.strip()[:NOTES_MAX_LENGTH]

    def validate(self, attrs):
        action = attrs["action"]
        notes = attrs.get("notes", "")
        if action in {"review_reject", "inspection_reject"} and not notes:
            message = (
                "Masukkan alasan penolakan."
                if action == "review_reject"
                else "Masukkan alasan kain tidak layak."
            )
            raise serializers.ValidationError({"notes": message})

        if action != "inspection_pass":
            return attrs

        upcycling_request = self.context["upcycling_request"]
        try:
            work_price = _parse_quote_component(
                attrs.get("work_price"),
                "harga pengerjaan",
                required=True,
            )
            batik_material_price = (
                _parse_quote_component(
                    attrs.get("batik_material_price"),
                    "biaya kain batik tambahan",
                    required=True,
                    allow_zero=True,
                )
                if upcycling_request.wants_batik_accent
                else Decimal("0")
            )
            fee_type = attrs.get("additional_fee_type", "").strip()[:120]
            fee_raw = attrs.get("additional_fee_amount", "").strip()
            if bool(fee_type) != bool(fee_raw):
                raise ValueError(
                    "Isi jenis dan nominal biaya tambahan lain secara bersamaan."
                )
            fee_amount = (
                _parse_quote_component(
                    fee_raw,
                    "biaya tambahan lain",
                    required=True,
                )
                if fee_raw
                else Decimal("0")
            )
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc

        total_price = work_price + batik_material_price + fee_amount
        if total_price > Decimal("99999999"):
            raise serializers.ValidationError(
                {"detail": "Total penawaran tidak boleh melebihi Rp99.999.999."}
            )

        attrs.update(
            {
                "work_price": work_price,
                "batik_material_price": batik_material_price,
                "additional_fee_type": fee_type,
                "additional_fee_amount": fee_amount,
                "quoted_price": total_price,
            }
        )
        return attrs


class ArtisanAssignmentSerializer(serializers.Serializer):
    """Validate the ID of an artisan profile selected by staff."""

    artisan_id = serializers.IntegerField(min_value=1)

class UpcyclingRequestListSerializer(serializers.ModelSerializer):
    """Serialize customer-visible summary fields for request lists."""

    reference_code = serializers.CharField(read_only=True)
    fabric_label = serializers.CharField(source="get_fabric_display", read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    product_name = serializers.CharField(source="get_product_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = UpcyclingRequest
        fields = (
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
            "fabric_photo",
        )

class UpcyclingRequestDetailSerializer(serializers.ModelSerializer):
    """Serialize the owner's request details, photos, labels, and timeline."""

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
        fields = (
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
            "fabric_condition",
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
        )

    def _file_url(self, file_field):
        """Return an absolute URL for an uploaded file when request context exists."""
        if not file_field:
            return None

        url = file_field.url
        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(url)

        return url

    def get_fabric_photos(self, obj):
        """Return the primary and additional fabric photo URLs."""
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
        """Return uploaded reference photo URLs."""
        return [
            self._file_url(photo.image)
            for photo in obj.reference_photos.all()
            if photo.image
        ]

    def get_status_timeline(self, obj):
        """Build completed, current, and upcoming steps from status history."""
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


class ArtisanUpcyclingRequestSerializer(UpcyclingRequestDetailSerializer):
    """Extend request details with fields visible to the assigned artisan."""

    class Meta(UpcyclingRequestDetailSerializer.Meta):
        fields = UpcyclingRequestDetailSerializer.Meta.fields + (
            "whatsapp",
            "review_approved_at",
            "fabric_receipt_notes",
            "inspection_notes",
            "rejection_stage",
            "return_method",
            "return_cost_bearer",
            "return_notes",
            "ready_at",
            "completed_at",
        )


class AdminQueueRowSerializer(serializers.Serializer):
    """Serialize an admin queue row with eligible artisan candidates."""

    request = ArtisanUpcyclingRequestSerializer(source="*")
    artisan_candidates = serializers.SerializerMethodField()

    def get_artisan_candidates(self, upcycling_request):
        """List candidates only while an unassigned request awaits assignment."""
        if (
            upcycling_request.status != UpcyclingRequest.Status.PENDING_ASSIGNMENT
            or upcycling_request.artisan_id is not None
        ):
            return []
        candidates_by_request = self.context.get(
            "artisan_candidates_by_request"
        )
        if candidates_by_request is None:
            candidates = eligible_artisans_for_request(upcycling_request)
        else:
            candidates = candidates_by_request.get(upcycling_request.pk, [])

        return [
            {
                "id": artisan.pk,
                "username": artisan.user.get_username(),
                "display_name": artisan.user.get_full_name(),
                "active_requests": artisan.eligible_active_request_count,
                "max_active_requests": artisan.max_active_requests,
            }
            for artisan in candidates
        ]
