from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from batik_custom.models import (
    BatikOrder, ColorPalette, FashionPreference, ProductDesignOption,
    RecommendedMotif, SavedDesign, StyleOptions,
)


class BatikCustomAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="test-password")
        self.other = User.objects.create_user(username="bob", password="test-password")

        self.style = StyleOptions.objects.create(
            name="API Elegant", description="d", detail="x", gender="women",
        )
        self.palette = ColorPalette.objects.create(
            name="API Retro", colors=["#111111", "#222222"],
        )
        self.pref, _ = FashionPreference.objects.get_or_create(name="WOMEN")
        self.motif = RecommendedMotif.objects.create(name="API Kawung")
        self.motif.styles.add(self.style)
        self.motif.palettes.add(self.palette)
        self.motif.fashion_preference.add(self.pref)
        self.option = ProductDesignOption.objects.create(
            product_type="shirt", name="API Kemeja", image="product_designs/x.webp",
        )
        self.fabric_option = ProductDesignOption.objects.create(
            product_type="fabric", name="API Kain", image="product_designs/y.webp",
        )

        self.design_payload = {
            "title": "Kawung kemeja", "motif": self.motif.pk, "palette": self.palette.pk,
            "layout": "grid", "scale": 100, "rotation": 90, "gap": 20,
            "color": "#874a29", "tint": 10, "is_public": False,
        }
        self.order_payload = {
            "motif": self.motif.pk, "palette": self.palette.pk,
            "product_type": "shirt", "design_option": self.option.pk,
            "material": "Katun Premium", "size": "M", "quantity": 2, "unit": "pcs",
            "recipient_name": "Alice", "phone": "081234567890",
            "address": "Jl. Mawar 1", "province": "DKI Jakarta",
            "city": "Jakarta Barat", "postal_code": "11630",
            "payment_method": "qris",
        }

    # ---- katalog publik --------------------------------------------------
    def test_public_catalog(self):
        r = self.client.get(reverse("api_custom:style-list"), {"gender": "women"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.style.pk, [item["id"] for item in r.data])
        r = self.client.get(reverse("api_custom:palette-list"))
        self.assertEqual(r.status_code, 200)
        r = self.client.get(reverse("api_custom:product-option-list"), {"product_type": "shirt"})
        self.assertEqual([o["name"] for o in r.data], ["API Kemeja"])
        self.assertEqual(r.data[0]["price"], 350000)

    def test_motif_filters(self):
        url = reverse("api_custom:motif-list")
        r = self.client.get(url, {
            "style": self.style.pk, "palette": self.palette.pk, "preference": "women",
        })
        self.assertEqual([m["name"] for m in r.data], ["API Kawung"])
        self.assertEqual(self.client.get(url, {"style": 999999}).data, [])
        self.assertEqual(self.client.get(url, {"style": "abc"}).status_code, 400)
        detail = reverse("api_custom:motif-detail", args=[self.motif.pk])
        self.assertEqual(self.client.get(detail).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("api_custom:motif-detail", args=[999999])).status_code, 404,
        )

    def test_catalog_is_read_only(self):
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.post(reverse("api_custom:style-list"), {}, format="json").status_code, 405)

    # ---- desain tersimpan -----------------------------------------------
    def test_designs_require_login(self):
        url = reverse("api_custom:design-list")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, self.design_payload, format="json").status_code, 403)

    def test_design_crud_and_ownership(self):
        url = reverse("api_custom:design-list")
        self.client.force_authenticate(user=self.user)
        r = self.client.post(url, self.design_payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        design = SavedDesign.objects.get(pk=r.data["id"])
        self.assertEqual(design.user, self.user)
        detail = reverse("api_custom:design-detail", args=[design.pk])

        r = self.client.patch(detail, {"title": "Baru", "scale": 150}, format="json")
        self.assertEqual(r.status_code, 200)
        design.refresh_from_db()
        self.assertEqual((design.title, design.scale, design.gap), ("Baru", 150, 20))

        self.client.force_authenticate(user=self.other)
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertEqual(self.client.delete(detail).status_code, 404)
        self.assertEqual(self.client.get(url).data, [])

        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.delete(detail).status_code, 204)
        self.assertFalse(SavedDesign.objects.filter(pk=design.pk).exists())

    def test_design_validation(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("api_custom:design-list")
        for changes, field in [
            ({"title": "  "}, "title"),
            ({"scale": 10}, "scale"),
            ({"rotation": 45}, "rotation"),
            ({"gap": 99}, "gap"),
            ({"tint": 71}, "tint"),
            ({"color": "red"}, "color"),
            ({"layout": "spiral"}, "layout"),
            ({"motif": 999999}, "motif"),
        ]:
            r = self.client.post(url, {**self.design_payload, **changes}, format="json")
            self.assertEqual(r.status_code, 400, changes)
            self.assertIn(field, r.data)
        self.assertEqual(SavedDesign.objects.count(), 0)

    def test_design_search(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("api_custom:design-list")
        self.client.post(url, self.design_payload, format="json")
        self.assertEqual(len(self.client.get(url, {"q": "kawung"}).data), 1)
        self.assertEqual(self.client.get(url, {"q": "tidak-ada"}).data, [])
        self.assertEqual(self.client.get(url, {"layout": "mirror"}).data, [])

    def test_design_motif_cannot_change(self):
        self.client.force_authenticate(user=self.user)
        r = self.client.post(reverse("api_custom:design-list"), self.design_payload, format="json")
        other_motif = RecommendedMotif.objects.create(name="Lain")
        detail = reverse("api_custom:design-detail", args=[r.data["id"]])
        r = self.client.patch(detail, {"motif": other_motif.pk}, format="json")
        self.assertEqual(r.status_code, 400)

    # ---- pesanan --------------------------------------------------------
    def test_orders_require_login(self):
        self.assertEqual(self.client.get(reverse("api_custom:order-list")).status_code, 403)

    def test_create_order_price_is_server_side(self):
        self.client.force_authenticate(user=self.user)
        r = self.client.post(
            reverse("api_custom:order-list"),
            {**self.order_payload, "unit_price": 1, "total_price": 1, "status": "completed"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["unit_price"], 350000)
        self.assertEqual(r.data["total_price"], 700000)
        self.assertEqual(r.data["status"], "pending")
        self.assertEqual(BatikOrder.objects.get(pk=r.data["id"]).user, self.user)

    def test_order_validation(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("api_custom:order-list")
        for changes, field in [
            ({"design_option": self.fabric_option.pk}, "design_option"),
            ({"quantity": 0}, "quantity"),
            ({"quantity": 101}, "quantity"),
            ({"material": "Sutra"}, "material"),
            ({"phone": "abc"}, "phone"),
            ({"postal_code": "ab"}, "postal_code"),
            ({"payment_method": "cash"}, "payment_method"),
            ({"motif": 999999}, "motif"),
        ]:
            r = self.client.post(url, {**self.order_payload, **changes}, format="json")
            self.assertEqual(r.status_code, 400, changes)
            self.assertIn(field, r.data)
        self.assertEqual(BatikOrder.objects.count(), 0)

    def test_orders_are_private(self):
        self.client.force_authenticate(user=self.user)
        r = self.client.post(reverse("api_custom:order-list"), self.order_payload, format="json")
        detail = reverse("api_custom:order-detail", args=[r.data["id"]])
        self.assertEqual(self.client.get(detail).status_code, 200)
        self.assertEqual(len(self.client.get(reverse("api_custom:order-list")).data), 1)
        self.client.force_authenticate(user=self.other)
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertEqual(self.client.get(reverse("api_custom:order-list")).data, [])
        self.assertEqual(self.client.delete(detail).status_code, 405)

    def test_session_write_without_csrf_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertTrue(client.login(username="alice", password="test-password"))
        r = client.post(reverse("api_custom:design-list"), self.design_payload, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(SavedDesign.objects.count(), 0)
