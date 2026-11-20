import uuid

from django.contrib.auth.models import Group, User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from marketplace.models import DropOffPoint, Order, Product


class MarketplaceAPITestBase(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username="buyer", password="test-password")
        self.other = User.objects.create_user(username="other", password="test-password")
        self.artisan = User.objects.create_user(username="artisan", password="test-password")
        self.artisan.groups.add(Group.objects.get_or_create(name="Artisan")[0])

        self.product = Product.objects.create(
            name="Tas Perca Parang", motif="Parang", category=Product.Category.TAS,
            material_source="Kain perca batik", artisan_origin="Solo",
            price=150_000, stock=5, image_url="https://example.com/tas.jpg",
        )
        self.pouch = Product.objects.create(
            name="Pouch Kawung", motif="Kawung", category=Product.Category.POUCH,
            material_source="Sarung bekas", artisan_origin="Yogyakarta",
            price=50_000, stock=0,
        )
        self.hidden = Product.objects.create(
            name="Produk Tersembunyi", motif="Lasem", category=Product.Category.TAS,
            material_source="Kain", artisan_origin="Lasem", price=90_000, is_deleted=True,
        )
        self.point = DropOffPoint.objects.create(
            code="test-dpk-99", name="Drop-off Uji Depok", address="Jl. Margonda 1",
            city="Kota Uji", province="Jawa Barat", phone="081234567890",
            accepted_items="Kain Perca, Baju Batik",
        )

    def checkout_payload(self, **overrides):
        payload = {
            "product": self.product.pk,
            "quantity": 2,
            "delivery_method": Order.DeliveryMethod.DROP_OFF,
            "dropoff_point": self.point.pk,
            "whatsapp": "081234567890",
            "notes": "Bungkus kado",
        }
        payload.update(overrides)
        return payload


class ProductAPITest(MarketplaceAPITestBase):
    def test_public_list_hides_deleted_products(self):
        response = self.client.get(reverse("api_marketplace:product-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {item["name"] for item in response.data}
        self.assertEqual(names, {"Tas Perca Parang", "Pouch Kawung"})
        tas = next(item for item in response.data if item["id"] == self.product.pk)
        self.assertEqual(tas["category_display"], "Tas")
        self.assertTrue(tas["is_in_stock"])

    def test_filters_and_sort(self):
        url = reverse("api_marketplace:product-list")
        self.assertEqual(len(self.client.get(url, {"q": "kawung"}).data), 1)
        self.assertEqual(len(self.client.get(url, {"category": "pouch"}).data), 1)
        prices = [p["price"] for p in self.client.get(url, {"sort": "price_asc"}).data]
        self.assertEqual(prices, sorted(prices))

    def test_detail_and_hidden_product(self):
        ok = self.client.get(reverse("api_marketplace:product-detail", args=[self.product.pk]))
        self.assertEqual(ok.status_code, 200)
        hidden_url = reverse("api_marketplace:product-detail", args=[self.hidden.pk])
        self.assertEqual(self.client.get(hidden_url).status_code, 404)
        self.client.force_authenticate(self.artisan)
        self.assertEqual(self.client.get(hidden_url).status_code, 200)

    def test_categories(self):
        response = self.client.get(reverse("api_marketplace:category-list"))
        self.assertIn({"value": "TAS", "label": "Tas"}, response.data)

    def test_buyer_cannot_manage_products(self):
        self.client.force_authenticate(self.buyer)
        url = reverse("api_marketplace:product-detail", args=[self.product.pk])
        self.assertEqual(self.client.patch(url, {"price": 1000}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)

    def test_artisan_crud_with_form_validation(self):
        self.client.force_authenticate(self.artisan)
        list_url = reverse("api_marketplace:product-list")
        payload = {
            "name": "Kemeja Mega Mendung", "motif": "Mega Mendung", "category": "PAKAIAN",
            "material_source": "Kemeja bekas", "artisan_origin": "Cirebon",
            "price": 250_000, "stock": 3,
        }
        created = self.client.post(list_url, payload, format="json")
        self.assertEqual(created.status_code, 201)
        product = Product.objects.get(pk=created.data["id"])
        self.assertEqual(product.user, self.artisan)

        bad = self.client.post(list_url, {**payload, "price": 10}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertIn("price", bad.data)

        detail = reverse("api_marketplace:product-detail", args=[product.pk])
        patched = self.client.patch(detail, {"price": 199_000}, format="json")
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.data["price"], 199_000)
        self.assertEqual(patched.data["name"], "Kemeja Mega Mendung")

        self.assertEqual(self.client.delete(detail).status_code, 204)
        product.refresh_from_db()
        self.assertTrue(product.is_deleted)
        restore = reverse("api_marketplace:product-restore", args=[product.pk])
        self.assertEqual(self.client.post(restore).status_code, 200)
        product.refresh_from_db()
        self.assertFalse(product.is_deleted)


class DropOffAPITest(MarketplaceAPITestBase):
    def test_list_filter_and_detail(self):
        url = reverse("api_marketplace:dropoff-list")
        data = self.client.get(url, {"city": "kota uji"}).data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["accepted_items"], ["Kain Perca", "Baju Batik"])
        self.assertEqual(data[0]["whatsapp_url"], "https://wa.me/6281234567890")
        self.assertEqual(len(self.client.get(url, {"q": "Uji Depok"}).data), 1)

        detail = self.client.get(reverse("api_marketplace:dropoff-detail", args=[self.point.pk]))
        self.assertEqual(detail.data["code"], "test-dpk-99")
        cities = self.client.get(reverse("api_marketplace:dropoff-city-list")).data
        self.assertIn("Kota Uji", cities)


class OrderAPITest(MarketplaceAPITestBase):
    def test_guest_cannot_access_orders(self):
        self.assertEqual(self.client.get(reverse("api_marketplace:order-list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("api_marketplace:voucher-list")).status_code, 403)

    def test_checkout_reserves_stock_and_lists_order(self):
        self.client.force_authenticate(self.buyer)
        response = self.client.post(
            reverse("api_marketplace:order-list"), self.checkout_payload(), format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["total_price"], 300_000)
        self.assertEqual(response.data["whatsapp"], "+6281234567890")
        self.assertEqual(response.data["dropoff_point"]["id"], self.point.pk)
        self.assertTrue(response.data["can_cancel"])
        self.assertTrue(response.data["reference_code"].startswith("MP-"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

        orders = self.client.get(reverse("api_marketplace:order-list")).data
        self.assertEqual(len(orders), 1)

    def test_checkout_validation_errors(self):
        self.client.force_authenticate(self.buyer)
        url = reverse("api_marketplace:order-list")
        no_point = self.client.post(url, self.checkout_payload(dropoff_point=""), format="json")
        self.assertEqual(no_point.status_code, 400)
        self.assertIn("dropoff_point", no_point.data)

        too_many = self.client.post(url, self.checkout_payload(quantity=6), format="json")
        self.assertEqual(too_many.status_code, 400)
        self.assertIn("quantity", too_many.data)

        bad_product = self.client.post(url, self.checkout_payload(product="abc"), format="json")
        self.assertEqual(bad_product.status_code, 400)

        hidden = self.client.post(url, self.checkout_payload(product=self.hidden.pk), format="json")
        self.assertEqual(hidden.status_code, 404)

        bad_voucher = self.client.post(
            url, self.checkout_payload(voucher_code="NOPE123"), format="json",
        )
        self.assertEqual(bad_voucher.status_code, 400)
        self.assertIn("voucher_code", bad_voucher.data)

    def test_cancel_restores_stock_and_is_owner_only(self):
        self.client.force_authenticate(self.buyer)
        created = self.client.post(
            reverse("api_marketplace:order-list"), self.checkout_payload(), format="json",
        )
        order_id = created.data["id"]
        cancel_url = reverse("api_marketplace:order-cancel", args=[order_id])

        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(cancel_url).status_code, 404)
        detail_url = reverse("api_marketplace:order-detail", args=[order_id])
        self.assertEqual(self.client.get(detail_url).status_code, 404)

        self.client.force_authenticate(self.buyer)
        cancelled = self.client.post(cancel_url)
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.data["status"], "CANCELLED")
        self.assertEqual(len(cancelled.data["status_history"]), 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(self.client.post(cancel_url).status_code, 409)

    def test_missing_order(self):
        self.client.force_authenticate(self.buyer)
        url = reverse("api_marketplace:order-detail", args=[uuid.uuid4()])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_vouchers_empty_for_new_user(self):
        self.client.force_authenticate(self.buyer)
        self.assertEqual(self.client.get(reverse("api_marketplace:voucher-list")).data, [])
