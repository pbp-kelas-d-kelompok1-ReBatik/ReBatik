from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import StyleOptions, ColorPalette, FashionPreference, RecommendedMotif, SavedDesign, BatikOrder

User = get_user_model()

class BatikCustomFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="custom-user", password="test-pass-123")
        self.style = StyleOptions.objects.create(name="Elegant", description="Elegan", detail="Tampilan elegan", gender="women")
        self.palette = ColorPalette.objects.create(name="Earth Tone", description="Warna bumi", colors=["#875333", "#E8C99C"])
        self.preference = FashionPreference.objects.create(name="WOMEN")
        self.motif = RecommendedMotif.objects.create(name="Parang Modern", description="Motif modern")
        self.motif.styles.add(self.style)
        self.motif.palettes.add(self.palette)
        self.motif.fashion_preference.add(self.preference)

    def test_fashion_preference_page_is_responsive_template(self):
        response = self.client.get(reverse("batik_custom:fashion_preference"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "fashion-grid")
        self.assertContains(response, "women")

    def test_fashion_preference_post_saves_session_and_redirects(self):
        response = self.client.post(reverse("batik_custom:fashion_preference"), {"fashion_preference": "women"})
        self.assertRedirects(response, reverse("batik_custom:style_quiz"))
        self.assertEqual(self.client.session["fashion_preference"], "women")

    def test_invalid_fashion_preference_does_not_advance(self):
        response = self.client.post(reverse("batik_custom:fashion_preference"), {"fashion_preference": "invalid"})
        self.assertRedirects(response, reverse("batik_custom:fashion_preference"))

    def test_style_quiz_filters_by_gender(self):
        self.client.session["fashion_preference"] = "women"
        response = self.client.get(reverse("batik_custom:style_quiz"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Elegant")

    def test_recommendations_require_login_and_selected_preferences(self):
        url = reverse("batik_custom:recommended_motifs")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.user)
        session = self.client.session
        session["fashion_preference"] = "women"
        session["selected_style_id"] = self.style.pk
        session["selected_palette_id"] = self.palette.pk
        session.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Parang Modern")

    def test_saved_design_is_private_to_owner(self):
        design = SavedDesign.objects.create(user=self.user, title="Desain Saya", motif=self.motif, palette=self.palette)
        other = User.objects.create_user(username="other-user", password="test-pass-123")
        self.client.force_login(other)
        response = self.client.get(reverse("batik_custom:saved_design_detail", args=[design.pk]))
        self.assertEqual(response.status_code, 404)

    def test_saved_design_create_and_update_pages(self):
        self.client.force_login(self.user)
        create_url = reverse("batik_custom:saved_design_create")
        response = self.client.get(create_url, {"motif": self.motif.pk})
        self.assertEqual(response.status_code, 200)
        design = SavedDesign.objects.create(user=self.user, title="Draft", motif=self.motif, palette=self.palette)
        response = self.client.get(reverse("batik_custom:saved_design_update", args=[design.pk]))
        self.assertEqual(response.status_code, 200)

    def test_order_history_requires_login_and_is_available(self):
        url = reverse("batik_custom:order_history")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_order_status_change_creates_notification(self):
        order = BatikOrder.objects.create(
            user=self.user, motif=self.motif, product_type="fabric",
            material="Katun Premium", recipient_name="Pengguna Tes",
            phone="08123456789", address="Jalan Contoh",
            province="DKI Jakarta", city="Jakarta", postal_code="12345",
            payment_method="bank", quantity=2, unit="meter",
        )
        order.status = "confirmed"
        order.save()
        self.assertTrue(self.user.notifications.filter(
            notification_type="order_updated", message__contains=f"#{order.pk}"
        ).exists())
