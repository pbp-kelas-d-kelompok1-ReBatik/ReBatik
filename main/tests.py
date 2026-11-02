from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Notification

User = get_user_model()

class NavbarAndNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="navbar-user", password="test-pass-123")

    def test_search_suggestions_htmx_endpoint(self):
        response = self.client.get(reverse("main:navbar_search"), {"q": "par"}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "partials/navbar_search_results.html")

    def test_notification_list_is_private(self):
        url = reverse("main:notifications")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.user)
        Notification.objects.create(user=self.user, title="Tes", message="Notifikasi tes")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Notifikasi tes")

    def test_mark_notification_read_only_for_owner(self):
        notification = Notification.objects.create(user=self.user, title="Tes", message="Pesan")
        self.client.force_login(self.user)
        response = self.client.post(reverse("main:notification_mark_read", args=[notification.pk]))
        self.assertEqual(response.status_code, 302)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
