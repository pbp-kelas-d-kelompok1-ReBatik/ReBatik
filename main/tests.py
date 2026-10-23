from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class LoginRedirectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="rezky",
            password="password123",
        )

    def test_login_returns_user_to_safe_next_url(self):
        response = self.client.post(
            reverse("main:login"),
            {
                "username": "rezky",
                "password": "password123",
                "next": "/upcycling/new/",
            },
        )

        self.assertRedirects(
            response,
            "/upcycling/new/",
            fetch_redirect_response=False,
        )

    def test_login_rejects_external_next_url(self):
        response = self.client.post(
            reverse("main:login"),
            {
                "username": "rezky",
                "password": "password123",
                "next": "https://malicious.example/",
            },
        )

        self.assertRedirects(
            response,
            reverse("main:show_home"),
            fetch_redirect_response=False,
        )
