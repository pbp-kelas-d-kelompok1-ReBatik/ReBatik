from base64 import b64decode
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    ArtisanProfile,
    ProductType,
    UpcyclingRequest,
    UpcyclingStatusHistory,
)


User = get_user_model()
REQUESTS_URL = "/api/v1/upcycling/requests/"
TINY_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"
)


class UpcyclingRequestAPITests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_directory = TemporaryDirectory()
        media_settings = override_settings(MEDIA_ROOT=cls.media_directory.name)
        media_settings.enable()
        cls.addClassCleanup(cls.media_directory.cleanup)
        cls.addClassCleanup(media_settings.disable)

    def setUp(self):
        self.user = User.objects.create_user(
            username="api-user",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="other-api-user",
            password="test-password",
        )

    def valid_payload(self):
        return {
            "fabric": "DENIM",
            "current_item_form": "PANTS",
            "has_batik_pattern": "NO",
            "category": "TAS",
            "product": "TOTE_BAG",
            "quantity": 1,
            "whatsapp": "+6281234567890",
            "fabric_photos": [
                SimpleUploadedFile(
                    "fabric.png",
                    TINY_PNG,
                    content_type="image/png",
                )
            ],
        }

    def make_request(self, user, request_status, **overrides):
        fields = {
            "user": user,
            "fabric": "DENIM",
            "category": "TAS",
            "product": "TOTE_BAG",
            "quantity": 1,
            "whatsapp": "+6281234567890",
            "status": request_status,
        }
        fields.update(overrides)
        return UpcyclingRequest.objects.create(**fields)

    def test_requests_require_authentication(self):
        response = self.client.get(REQUESTS_URL)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

        response = self.client.post(
            REQUESTS_URL,
            self.valid_payload(),
            format="multipart",
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
        self.assertEqual(UpcyclingRequest.objects.count(), 0)

    def test_list_and_detail_only_expose_the_authenticated_users_requests(self):
        own_request = UpcyclingRequest.objects.create(
            user=self.user,
            fabric="DENIM",
            category="TAS",
            product="TOTE_BAG",
            whatsapp="+6281234567890",
        )
        other_request = UpcyclingRequest.objects.create(
            user=self.other_user,
            fabric="COTTON",
            category="POUCH",
            product="POUCH",
            whatsapp="+6281234567890",
        )
        self.client.force_authenticate(user=self.user)

        list_response = self.client.get(REQUESTS_URL)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["id"], str(own_request.pk))

        own_detail = self.client.get(f"{REQUESTS_URL}{own_request.pk}/")
        self.assertEqual(own_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(own_detail.data["id"], str(own_request.pk))

        other_detail = self.client.get(f"{REQUESTS_URL}{other_request.pk}/")
        self.assertEqual(other_detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_request_saves_owner_photos_and_initial_status_history(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            REQUESTS_URL,
            self.valid_payload(),
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        created_request = UpcyclingRequest.objects.get(pk=response.data["id"])
        self.assertEqual(created_request.user, self.user)
        self.assertEqual(
            created_request.status,
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
        )
        self.assertTrue(created_request.fabric_photo)
        self.assertEqual(
            UpcyclingStatusHistory.objects.filter(request=created_request).count(),
            1,
        )
        self.assertEqual(response.data["quantity"], 1)
        self.assertEqual(len(response.data["fabric_photos"]), 1)

    def test_invalid_whatsapp_and_missing_quantity_are_rejected(self):
        self.client.force_authenticate(user=self.user)

        invalid_whatsapp = self.valid_payload()
        invalid_whatsapp["whatsapp"] = "123"
        response = self.client.post(
            REQUESTS_URL,
            invalid_whatsapp,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("whatsapp", response.data)

        missing_quantity = self.valid_payload()
        missing_quantity.pop("quantity")
        response = self.client.post(
            REQUESTS_URL,
            missing_quantity,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", response.data)
        self.assertEqual(UpcyclingRequest.objects.count(), 0)

    def test_create_rate_limit_returns_429_and_retry_after(self):
        self.client.force_authenticate(user=self.user)

        with patch(
            "upcycling.api_views.consume_upcycling_rate_limit",
            return_value=(False, 42),
        ) as mock_rate_limit:
            response = self.client.post(
                REQUESTS_URL,
                {},
                format="multipart",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
        self.assertEqual(response["Retry-After"], "42")
        mock_rate_limit.assert_called_once()
        self.assertEqual(UpcyclingRequest.objects.count(), 0)

    def test_user_can_patch_owned_request_while_waiting_for_assignment(self):
        upcycling_request = self.make_request(
            self.user,
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f"{REQUESTS_URL}{upcycling_request.pk}/",
            {"notes": "Tolong gunakan warna netral."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        upcycling_request.refresh_from_db()
        self.assertEqual(upcycling_request.notes, "Tolong gunakan warna netral.")
        self.assertEqual(
            upcycling_request.status,
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
        )

    def test_user_cannot_patch_another_users_or_non_pending_request(self):
        other_user_request = self.make_request(
            self.other_user,
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
        )
        later_status_request = self.make_request(
            self.user,
            UpcyclingRequest.Status.PENDING_REVIEW,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f"{REQUESTS_URL}{other_user_request.pk}/",
            {"notes": "Tidak boleh diedit."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.patch(
            f"{REQUESTS_URL}{later_status_request.pk}/",
            {"notes": "Sudah ditinjau."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_user_can_submit_fabric_handoff_only_for_owned_eligible_request(self):
        eligible = self.make_request(
            self.user,
            UpcyclingRequest.Status.AWAITING_FABRIC,
        )
        other_user_request = self.make_request(
            self.other_user,
            UpcyclingRequest.Status.AWAITING_FABRIC,
        )
        not_eligible = self.make_request(
            self.user,
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            f"{REQUESTS_URL}{eligible.pk}/fabric-handoff/",
            {
                "fabric_delivery_method": "SELF_SHIP",
                "fabric_delivery_location": "Kirim lewat kurir",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        eligible.refresh_from_db()
        self.assertEqual(
            eligible.fabric_delivery_method,
            UpcyclingRequest.FabricDeliveryMethod.SELF_SHIP,
        )
        self.assertEqual(eligible.status, UpcyclingRequest.Status.AWAITING_FABRIC)

        response = self.client.post(
            f"{REQUESTS_URL}{other_user_request.pk}/fabric-handoff/",
            {"fabric_delivery_method": "SELF_SHIP"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.post(
            f"{REQUESTS_URL}{not_eligible.pk}/fabric-handoff/",
            {"fabric_delivery_method": "SELF_SHIP"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_user_can_approve_quote_and_submit_product_delivery(self):
        upcycling_request = self.make_request(
            self.user,
            UpcyclingRequest.Status.AWAITING_APPROVAL,
            quoted_price="25000.00",
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            f"{REQUESTS_URL}{upcycling_request.pk}/approve-quote/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        upcycling_request.refresh_from_db()
        self.assertEqual(
            upcycling_request.status,
            UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS,
        )
        self.assertIsNotNone(upcycling_request.approved_at)

        response = self.client.post(
            f"{REQUESTS_URL}{upcycling_request.pk}/product-delivery/",
            {"delivery_method": "DROP_OFF", "address": "Depok"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        upcycling_request.refresh_from_db()
        self.assertEqual(upcycling_request.status, UpcyclingRequest.Status.IN_PROGRESS)
        self.assertEqual(upcycling_request.address, "Depok")
        self.assertEqual(
            UpcyclingStatusHistory.objects.filter(request=upcycling_request).count(),
            2,
        )

    def test_user_can_cancel_request_or_reject_pending_quote(self):
        cancellable = self.make_request(
            self.user,
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
        )
        quote = self.make_request(
            self.user,
            UpcyclingRequest.Status.AWAITING_APPROVAL,
            quoted_price="25000.00",
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            f"{REQUESTS_URL}{cancellable.pk}/cancel/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cancellable.refresh_from_db()
        self.assertEqual(cancellable.status, UpcyclingRequest.Status.CANCELLED)

        response = self.client.post(
            f"{REQUESTS_URL}{quote.pk}/cancel/",
            {"action": "reject_quote"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        quote.refresh_from_db()
        self.assertEqual(quote.status, UpcyclingRequest.Status.CANCELLED)
        self.assertEqual(
            quote.cancellation_reason,
            "Penawaran harga ditolak oleh user.",
        )

    def test_user_can_confirm_ready_request_and_receive_completion_points(self):
        upcycling_request = self.make_request(
            self.user,
            UpcyclingRequest.Status.READY,
        )
        self.client.force_authenticate(user=self.user)

        with patch("rewards.services.award_upcycling_completion") as award_points:
            response = self.client.post(
                f"{REQUESTS_URL}{upcycling_request.pk}/confirm-completion/",
                {},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        upcycling_request.refresh_from_db()
        self.assertEqual(
            upcycling_request.status,
            UpcyclingRequest.Status.COMPLETED,
        )
        self.assertEqual(upcycling_request.completed_by, self.user)
        award_points.assert_called_once_with(
            self.user,
            request_reference=str(upcycling_request.pk),
            upcycling_request=upcycling_request,
        )

    def test_artisan_can_list_assigned_requests_and_accept_review(self):
        artisan_user = User.objects.create_user(username="artisan-api")
        artisan_group, _ = Group.objects.get_or_create(name="Artisan")
        artisan_user.groups.add(artisan_group)
        artisan_profile = ArtisanProfile.objects.create(user=artisan_user)
        assigned = self.make_request(
            self.user,
            UpcyclingRequest.Status.PENDING_REVIEW,
            artisan=artisan_profile,
        )
        unassigned = self.make_request(
            self.other_user,
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
        )
        self.client.force_authenticate(user=artisan_user)

        list_response = self.client.get("/api/v1/upcycling/artisan/requests/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["id"], str(assigned.pk))

        response = self.client.post(
            f"{REQUESTS_URL}{assigned.pk}/artisan-action/",
            {"action": "review_accept", "notes": "Kain dapat diproses."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        assigned.refresh_from_db()
        self.assertEqual(assigned.status, UpcyclingRequest.Status.AWAITING_FABRIC)
        self.assertIsNotNone(assigned.fabric_deadline)
        self.assertEqual(
            UpcyclingStatusHistory.objects.filter(
                request=assigned,
                changed_by=artisan_user,
            ).count(),
            1,
        )

        response = self.client.post(
            f"{REQUESTS_URL}{unassigned.pk}/artisan-action/",
            {"action": "review_accept"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_artisan_inspection_pass_builds_quote_and_reject_requires_reason(self):
        artisan_user = User.objects.create_user(username="artisan-inspection")
        artisan_group, _ = Group.objects.get_or_create(name="Artisan")
        artisan_user.groups.add(artisan_group)
        artisan_profile = ArtisanProfile.objects.create(user=artisan_user)
        inspected = self.make_request(
            self.user,
            UpcyclingRequest.Status.INSPECTION,
            artisan=artisan_profile,
            wants_batik_accent=True,
        )
        rejected = self.make_request(
            self.other_user,
            UpcyclingRequest.Status.INSPECTION,
            artisan=artisan_profile,
        )
        self.client.force_authenticate(user=artisan_user)

        response = self.client.post(
            f"{REQUESTS_URL}{inspected.pk}/artisan-action/",
            {
                "action": "inspection_pass",
                "work_price": "25.000",
                "batik_material_price": "10.000",
                "additional_fee_type": "",
                "additional_fee_amount": "",
                "notes": "Kain layak diproses.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        inspected.refresh_from_db()
        self.assertEqual(inspected.quoted_price, 35000)
        self.assertEqual(
            inspected.status,
            UpcyclingRequest.Status.AWAITING_APPROVAL,
        )

        response = self.client.post(
            f"{REQUESTS_URL}{rejected.pk}/artisan-action/",
            {"action": "inspection_reject", "notes": "   "},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("notes", response.data)

    def test_non_artisan_cannot_access_artisan_api(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/upcycling/artisan/requests/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_and_assign_an_eligible_artisan(self):
        admin = User.objects.create_superuser(
            username="upcycling-admin",
            email="admin@example.com",
            password="test-password",
        )
        artisan_user = User.objects.create_user(username="eligible-artisan")
        artisan_group, _ = Group.objects.get_or_create(name="Artisan")
        artisan_user.groups.add(artisan_group)
        artisan_profile = ArtisanProfile.objects.create(user=artisan_user)
        product_type, _ = ProductType.objects.get_or_create(
            code="TOTE_BAG",
            defaults={"name": "Tote bag"},
        )
        artisan_profile.specializations.add(product_type)
        pending = self.make_request(
            self.user,
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
        )
        self.client.force_authenticate(user=admin)

        list_response = self.client.get("/api/v1/upcycling/admin/requests/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(
            list_response.data[0]["artisan_candidates"][0]["id"],
            artisan_profile.pk,
        )

        response = self.client.post(
            f"/api/v1/upcycling/admin/requests/{pending.pk}/assign-artisan/",
            {"artisan_id": artisan_profile.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        pending.refresh_from_db()
        self.assertEqual(pending.artisan, artisan_profile)
        self.assertEqual(pending.status, UpcyclingRequest.Status.PENDING_REVIEW)

    def test_non_staff_cannot_access_admin_api(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/upcycling/admin/requests/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_rejects_unsupported_methods(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(REQUESTS_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.post(
            f"{REQUESTS_URL}{uuid4()}/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
