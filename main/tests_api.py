from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from main.models import Notification


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


    def test_logout_creates_notification(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(reverse("api_auth:logout"))
        self.assertTrue(
            Notification.objects.filter(user=self.user, notification_type="logout").exists()
        )

    def test_login_creates_notification_with_time(self):
        self.client.post(
            reverse("api_auth:login"),
            {"username": "budi", "password": "Pass-12345-xyz"}, format="json",
        )
        notif = Notification.objects.get(user=self.user, notification_type="login")
        self.assertIn("WIB", notif.message)


class NotificationAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="budi", password="Pass-12345-xyz")
        self.other = User.objects.create_user(username="siti", password="Pass-12345-xyz")
        self.n1 = Notification.objects.create(user=self.user, title="A", message="a")
        self.n2 = Notification.objects.create(user=self.user, title="B", message="b", is_read=True)
        self.foreign = Notification.objects.create(user=self.other, title="C", message="c")
        self.list_url = reverse("api_auth:notification-list")
        self.read_all_url = reverse("api_auth:notification-read-all")

    def test_requires_login(self):
        self.assertEqual(self.client.get(self.list_url).status_code, 403)
        self.assertEqual(self.client.post(self.read_all_url).status_code, 403)
        url = reverse("api_auth:notification-read", args=[self.n1.pk])
        self.assertEqual(self.client.post(url).status_code, 403)

    def test_list_only_own_notifications(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["unread_count"], 1)
        ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(ids, {self.n1.pk, self.n2.pk})

    def test_list_unread_filter(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {"unread": "true"})
        self.assertEqual([item["id"] for item in response.data["results"]], [self.n1.pk])

    def test_mark_read(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("api_auth:notification-read", args=[self.n1.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_read"])
        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)

    def test_cannot_mark_other_users_notification(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("api_auth:notification-read", args=[self.foreign.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.foreign.refresh_from_db()
        self.assertFalse(self.foreign.is_read)

    def test_mark_all_read(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.read_all_url)
        self.assertEqual(response.data, {"updated": 1, "unread_count": 0})
        self.foreign.refresh_from_db()
        self.assertFalse(self.foreign.is_read)

    def test_wrong_method(self):
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.post(self.list_url).status_code, 405)
        url = reverse("api_auth:notification-read", args=[self.n1.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
