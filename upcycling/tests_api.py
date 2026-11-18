from base64 import b64decode
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import UpcyclingRequest, UpcyclingStatusHistory


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
