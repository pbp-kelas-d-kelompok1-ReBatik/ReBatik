import uuid

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from batik_story.models import BatikMotif


class BatikStoryAPITest(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="test-password", is_staff=True,
        )
        self.visitor = User.objects.create_user(
            username="visitor", password="test-password",
        )
        self.motif = BatikMotif.objects.create(
            nama="Parang Rusak", asal="YOGYAKARTA",
            filosofi="Simbol perjuangan", deskripsi="Motif klasik.",
        )
        self.list_url = reverse("api_story:motif-list")
        self.detail_url = reverse("api_story:motif-detail", args=[self.motif.id_story])
        self.favorite_url = reverse("api_story:motif-favorite", args=[self.motif.id_story])
        self.payload = {
            "nama": "Kawung", "asal": "SOLO",
            "filosofi": "Kesucian dan keadilan", "deskripsi": "Motif bulatan.",
        }

    def test_public_list_and_detail(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], str(self.motif.id_story))
        self.assertEqual(response.data[0]["asal_display"], "Yogyakarta")
        self.assertFalse(response.data[0]["is_favorited"])
        self.assertEqual(self.client.get(self.detail_url).status_code, 200)

    def test_search_filter_sort(self):
        BatikMotif.objects.create(
            nama="Mega Mendung", asal="CIREBON", filosofi="Hujan", deskripsi="Awan",
        )
        self.assertEqual(len(self.client.get(self.list_url, {"q": "PARANG"}).data), 1)
        self.assertEqual(self.client.get(self.list_url, {"q": "tidak-ada"}).data, [])
        self.assertEqual(len(self.client.get(self.list_url, {"asal": "CIREBON"}).data), 1)
        names = [m["nama"] for m in self.client.get(self.list_url, {"sort": "nama_desc"}).data]
        self.assertEqual(names, sorted(names, reverse=True))

    def test_missing_motif(self):
        url = reverse("api_story:motif-detail", args=[uuid.uuid4()])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_guest_and_visitor_cannot_write(self):
        for user in (None, self.visitor):
            self.client.force_authenticate(user=user)
            self.assertEqual(self.client.post(self.list_url, self.payload, format="json").status_code, 403)
            self.assertEqual(self.client.patch(self.detail_url, {"nama": "X"}, format="json").status_code, 403)
            self.assertEqual(self.client.delete(self.detail_url).status_code, 403)
        self.assertEqual(BatikMotif.objects.count(), 1)

    def test_staff_create_validation_patch_delete(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        for changes, field in [
            ({"nama": " "}, "nama"),
            ({"nama": "<b></b>"}, "nama"),
            ({"asal": "ATLANTIS"}, "asal"),
        ]:
            response = self.client.post(self.list_url, {**self.payload, **changes}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn(field, response.data)

        response = self.client.patch(self.detail_url, {"nama": "Parang Baru"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.motif.refresh_from_db()
        self.assertEqual(self.motif.nama, "Parang Baru")
        self.assertEqual(self.motif.deskripsi, "Motif klasik.")

        response = self.client.put(self.detail_url, {"nama": "Incomplete"}, format="json")
        self.assertEqual(response.status_code, 400)

        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_favorite_requires_login_and_toggles(self):
        self.assertEqual(self.client.post(self.favorite_url).status_code, 403)
        self.client.force_authenticate(user=self.visitor)
        response = self.client.post(self.favorite_url)
        self.assertTrue(response.data["is_favorited"])
        self.assertEqual(response.data["favorite_count"], 1)
        response = self.client.post(self.favorite_url)
        self.assertFalse(response.data["is_favorited"])
        self.assertEqual(self.client.get(self.favorite_url).status_code, 405)

    def test_computed_fields_are_read_only(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(self.list_url, {
            **self.payload, "favorite_count": 99, "is_favorited": True,
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["favorite_count"], 0)

    def test_origins(self):
        response = self.client.get(reverse("api_story:origin-list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn({"value": "SOLO", "label": "Solo"}, response.data)

    def test_session_write_without_csrf_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertTrue(client.login(username="staff", password="test-password"))
        response = client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, 403)
