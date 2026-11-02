from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import BatikMotif

User = get_user_model()

class BatikStoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="story-user", password="test-pass-123")
        self.staff = User.objects.create_user(username="story-admin", password="test-pass-123", is_staff=True)
        self.motif = BatikMotif.objects.create(
            nama="Parang Rusak", asal="YOGYAKARTA",
            filosofi="Simbol perjuangan", deskripsi="Motif klasik dari Yogyakarta."
        )

    def test_story_page_shows_motif(self):
        response = self.client.get(reverse("batik_story:show_batik_story"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Parang Rusak")

    def test_story_search_filters_database(self):
        response = self.client.get(reverse("batik_story:show_batik_story"), {"q": "Parang"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Parang Rusak")
        response = self.client.get(reverse("batik_story:show_batik_story"), {"q": "tidak-ada"})
        self.assertNotContains(response, "Parang Rusak")

    def test_story_detail(self):
        response = self.client.get(reverse("batik_story:story_detail", args=[self.motif.id_story]))
        self.assertEqual(response.status_code, 200)

    def test_favorite_requires_login_and_post(self):
        url = reverse("batik_story:toggle_favorite", args=[self.motif.id_story])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.user)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_favorited"])
        response = self.client.post(url)
        self.assertFalse(response.json()["is_favorited"])

    def test_add_story_requires_staff(self):
        url = reverse("batik_story:add_batik")
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_staff_can_edit_story(self):
        self.client.force_login(self.staff)
        url = reverse("batik_story:story_edit", args=[self.motif.id_story])
        response = self.client.post(url, {
            "nama": "Parang Baru", "asal": "YOGYAKARTA",
            "filosofi": "Filosofi baru", "deskripsi": "Deskripsi baru",
        })
        self.assertRedirects(response, reverse("batik_story:show_batik_story"))
        self.motif.refresh_from_db()
        self.assertEqual(self.motif.nama, "Parang Baru")

    def test_staff_can_delete_story(self):
        self.client.force_login(self.staff)
        url = reverse("batik_story:delete_story", args=[self.motif.id_story])
        response = self.client.post(url)
        self.assertRedirects(response, reverse("batik_story:show_batik_story"))
        self.assertFalse(BatikMotif.objects.filter(pk=self.motif.pk).exists())
