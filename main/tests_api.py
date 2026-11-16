from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase


class AuthAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="budi", password="Pass-12345-xyz")

    def test_csrf_endpoint(self):
        response = self.client.get(reverse("api_auth:csrf"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["csrfToken"])

    def test_login_success_and_me(self):
        response = self.client.post(
            reverse("api_auth:login"),
            {"username": "budi", "password": "Pass-12345-xyz"}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["username"], "budi")
        me = self.client.get(reverse("api_auth:me"))
        self.assertTrue(me.data["is_authenticated"])

    def test_login_wrong_password(self):
        response = self.client.post(
            reverse("api_auth:login"),
            {"username": "budi", "password": "salah"}, format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_me_anonymous(self):
        self.assertFalse(self.client.get(reverse("api_auth:me")).data["is_authenticated"])

    def test_register(self):
        response = self.client.post(reverse("api_auth:register"), {
            "username": "siti", "password1": "Rahasia-9876-abc", "password2": "Rahasia-9876-abc",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="siti").exists())

    def test_register_validation(self):
        response = self.client.post(reverse("api_auth:register"), {
            "username": "siti", "password1": "abc", "password2": "xyz",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password2", response.data)

    def test_logout_requires_csrf_when_session(self):
        client = APIClient(enforce_csrf_checks=True)
        client.login(username="budi", password="Pass-12345-xyz")
        self.assertEqual(client.post(reverse("api_auth:logout")).status_code, 403)

    def test_logout(self):
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.post(reverse("api_auth:logout")).status_code, 200)
