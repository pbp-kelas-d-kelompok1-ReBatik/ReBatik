from django.contrib import admin
from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .admin import OrderAdmin, OrderAdminForm
from .forms import CheckoutForm, ProductForm
from .models import (
    DropOffPoint,
    Order,
    OrderStatusHistory,
    Product,
)
from .services import OrderTransitionNotAllowed, OutOfStock, cancel_order, place_order

User = get_user_model()


class ProductFormTests(TestCase):
    valid_data = {
        "name": "  Tote Bag Parang Rusak  ",
        "motif": "  Parang Rusak ",
        "category": Product.Category.TAS,
        "description": "  Tas jinjing dari kain sarung bekas.  ",
        "material_source": "  Sarung bekas Solo ",
        "artisan_origin": "  Sanggar Laweyan ",
        "badge_status": "  Terlaris ",
        "price": 185000,
        "stock": 4,
        "image_url": "https://example.com/totebag.webp",
    }

    def test_valid_product_form_strips_fields(self):
        form = ProductForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["name"], "Tote Bag Parang Rusak")
        self.assertEqual(form.cleaned_data["motif"], "Parang Rusak")
        self.assertEqual(form.cleaned_data["badge_status"], "Terlaris")

    def test_rejects_price_outside_supported_range(self):
        for invalid_price in (0, 500, 100_000_001):
            with self.subTest(price=invalid_price):
                data = {**self.valid_data, "price": invalid_price}
                form = ProductForm(data=data)
                self.assertFalse(form.is_valid())
                self.assertIn("price", form.errors)

    def test_rejects_non_https_image_url_and_allows_blank(self):
        insecure = {**self.valid_data, "image_url": "http://example.com/a.jpg"}
        form = ProductForm(data=insecure)
        self.assertFalse(form.is_valid())
        self.assertIn("image_url", form.errors)

        blank_url = {**self.valid_data, "image_url": ""}
        form_blank = ProductForm(data=blank_url)
        self.assertTrue(form_blank.is_valid(), form_blank.errors)
        self.assertIsNone(form_blank.cleaned_data["image_url"])


class CheckoutFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(
            name="Pouch Kawung Mini",
            motif="Kawung",
            category=Product.Category.POUCH,
            material_source="Kain perca kemeja",
            artisan_origin="Batik Giriloyo",
            price=65000,
            stock=5,
        )
        cls.dropoff = DropOffPoint.objects.create(
            name="Galeri ReBatik Depok",
            address="Jl. Margonda Raya No. 10",
            city="Depok",
        )

    def test_normalizes_indonesian_whatsapp_numbers(self):
        for raw in (
            "081234567890",
            "6281234567890",
            "+6281234567890",
            "+62 812-3456-7890",
        ):
            with self.subTest(raw=raw):
                form = CheckoutForm(
                    data={
                        "quantity": 2,
                        "delivery_method": Order.DeliveryMethod.DROP_OFF,
                        "dropoff_point": self.dropoff.pk,
                        "address": "Akan dihapus",
                        "whatsapp": raw,
                        "notes": "",
                    },
                    product=self.product,
                )
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data["whatsapp"], "+6281234567890")
                self.assertEqual(form.cleaned_data["address"], "")

    def test_validates_delivery_method_specific_fields(self):
        missing_dropoff = CheckoutForm(
            data={
                "quantity": 1,
                "delivery_method": Order.DeliveryMethod.DROP_OFF,
                "whatsapp": "081234567890",
            },
            product=self.product,
        )
        self.assertFalse(missing_dropoff.is_valid())
        self.assertIn("dropoff_point", missing_dropoff.errors)

        missing_address = CheckoutForm(
            data={
                "quantity": 1,
                "delivery_method": Order.DeliveryMethod.KURIR,
                "dropoff_point": self.dropoff.pk,
                "address": "   ",
                "whatsapp": "081234567890",
            },
            product=self.product,
        )
        self.assertFalse(missing_address.is_valid())
        self.assertIn("address", missing_address.errors)

        valid_kurir = CheckoutForm(
            data={
                "quantity": 1,
                "delivery_method": Order.DeliveryMethod.KURIR,
                "dropoff_point": self.dropoff.pk,
                "address": "Jl. Akses UI No. 5, Depok",
                "whatsapp": "081234567890",
            },
            product=self.product,
        )
        self.assertTrue(valid_kurir.is_valid(), valid_kurir.errors)
        self.assertIsNone(valid_kurir.cleaned_data["dropoff_point"])

    def test_rejects_quantity_above_available_stock(self):
        form = CheckoutForm(
            data={
                "quantity": 6,
                "delivery_method": Order.DeliveryMethod.DROP_OFF,
                "dropoff_point": self.dropoff.pk,
                "whatsapp": "081234567890",
            },
            product=self.product,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("quantity", form.errors)


class MarketplaceCatalogueViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.p1 = Product.objects.create(
            name="Tote Bag Parang",
            motif="Parang",
            category=Product.Category.TAS,
            material_source="Sarung bekas",
            artisan_origin="Solo",
            price=180000,
            stock=3,
        )
        cls.p2 = Product.objects.create(
            name="Kemeja Mega Mendung",
            motif="Mega Mendung",
            category=Product.Category.PAKAIAN,
            material_source="Kain katun perca",
            artisan_origin="Cirebon",
            price=320000,
            stock=2,
        )
        cls.p3 = Product.objects.create(
            name="Scrunchie Truntum",
            motif="Truntum",
            category=Product.Category.AKSESORIS,
            material_source="Potongan kebaya",
            artisan_origin="Depok",
            price=25000,
            stock=10,
        )
        cls.hidden_product = Product.objects.create(
            name="Produk Tersembunyi",
            motif="Kawung",
            category=Product.Category.POUCH,
            material_source="Sisa kain",
            artisan_origin="Yogyakarta",
            price=50000,
            stock=1,
            is_deleted=True,
        )
        cls.drop_depok = DropOffPoint.objects.create(
            name="Titik Depok",
            address="Margonda",
            city="Depok",
        )
        cls.drop_bandung = DropOffPoint.objects.create(
            name="Titik Bandung",
            address="Dago",
            city="Bandung",
        )

    def test_catalogue_hides_deleted_products_and_supports_filters(self):
        response = self.client.get(reverse("marketplace:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.p1.name)
        self.assertNotContains(response, self.hidden_product.name)

        cat_response = self.client.get(
            reverse("marketplace:home"),
            {"category": "PAKAIAN", "q": "Cirebon", "sort": "price_asc"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(cat_response.status_code, 200)
        self.assertEqual(list(cat_response.context["products"]), [self.p2])

    def test_catalogue_ignores_invalid_filter_parameters_and_sorts_by_price(self):
        response = self.client.get(
            reverse("marketplace:home"),
            {"category": "INVALID", "sort": "price_asc"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_category"], "")
        self.assertEqual(
            list(response.context["products"]),
            [self.p3, self.p1, self.p2],
        )

    def test_product_detail_returns_404_for_hidden_product(self):
        ok_resp = self.client.get(
            reverse("marketplace:product_detail", kwargs={"pk": self.p1.pk})
        )
        self.assertEqual(ok_resp.status_code, 200)

        hidden_resp = self.client.get(
            reverse(
                "marketplace:product_detail",
                kwargs={"pk": self.hidden_product.pk},
            )
        )
        self.assertEqual(hidden_resp.status_code, 404)

    def test_dropoff_list_filters_by_city_and_search(self):
        response = self.client.get(
            reverse("marketplace:dropoff"),
            {"city": "Depok", "q": "Margonda"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["drop_points"]), [self.drop_depok])


class CheckoutAndOrderViewTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            username="buyer",
            password="password123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="password123",
        )
        self.product = Product.objects.create(
            name="Tote Bag Parang Rusak",
            motif="Parang Rusak",
            category=Product.Category.TAS,
            material_source="Sarung bekas",
            artisan_origin="Sanggar Laweyan",
            price=185000,
            stock=3,
        )
        self.dropoff = DropOffPoint.objects.create(
            name="Galeri Depok",
            address="Jl. Margonda",
            city="Depok",
        )

    def test_checkout_requires_authentication(self):
        url = reverse("marketplace:checkout", kwargs={"pk": self.product.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_checkout_reserves_stock_snapshots_price_and_creates_history(self):
        self.client.force_login(self.buyer)
        url = reverse("marketplace:checkout", kwargs={"pk": self.product.pk})
        response = self.client.post(
            url,
            data={
                "quantity": 2,
                "delivery_method": Order.DeliveryMethod.DROP_OFF,
                "dropoff_point": self.dropoff.pk,
                "whatsapp": "081234567890",
                "notes": "Ambil sore hari",
            },
        )
        order = Order.objects.get(user=self.buyer)
        self.assertRedirects(
            response,
            reverse("marketplace:order_success", kwargs={"pk": order.pk}),
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
        self.assertEqual(order.product_name, "Tote Bag Parang Rusak")
        self.assertEqual(order.unit_price, 185000)
        self.assertEqual(order.total_price, 370000)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertTrue(order.reference_code.startswith("MP-"))
        self.assertEqual(order.status_history.count(), 1)

        # Updating product price later must not alter historical order snapshot
        self.product.price = 250000
        self.product.save()
        order.refresh_from_db()
        self.assertEqual(order.unit_price, 185000)
        self.assertEqual(order.total_price, 370000)

    def test_service_raises_out_of_stock_when_stock_is_insufficient(self):
        with self.assertRaises(OutOfStock):
            place_order(
                self.buyer,
                self.product.pk,
                quantity=5,
                delivery_method=Order.DeliveryMethod.KURIR,
                address="Jl. UI Depok",
                whatsapp="+6281234567890",
            )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_owner_isolation_and_cancellation_restores_stock(self):
        order = place_order(
            self.buyer,
            self.product.pk,
            quantity=2,
            delivery_method=Order.DeliveryMethod.DROP_OFF,
            dropoff_point=self.dropoff,
            whatsapp="+6281234567890",
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

        # Other user cannot view or cancel buyer's order
        self.client.force_login(self.other_user)
        detail_url = reverse("marketplace:order_detail", kwargs={"pk": order.pk})
        cancel_url = reverse("marketplace:order_cancel", kwargs={"pk": order.pk})
        self.assertEqual(self.client.get(detail_url).status_code, 404)
        self.assertEqual(self.client.post(cancel_url).status_code, 404)

        # Owner GET renders confirmation without cancelling
        self.client.force_login(self.buyer)
        get_resp = self.client.get(cancel_url)
        self.assertEqual(get_resp.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

        # Owner POST cancels and restores stock
        post_resp = self.client.post(cancel_url)
        self.assertRedirects(post_resp, detail_url)
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(order.status_history.count(), 2)

        # Cancelling again is rejected
        with self.assertRaises(OrderTransitionNotAllowed):
            cancel_order(order.pk, by_user=self.buyer, require_owner=True)


class StaffProductManagementViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staffuser",
            password="password123",
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username="member",
            password="password123",
            is_staff=False,
        )
        self.product = Product.objects.create(
            name="Sling Bag Kawung",
            motif="Kawung",
            category=Product.Category.TAS,
            material_source="Selendang bekas",
            artisan_origin="Yogyakarta",
            price=150000,
            stock=2,
        )

    def test_staff_views_reject_anonymous_and_non_staff_users(self):
        manage_url = reverse("marketplace:manage_product_list")
        anon_resp = self.client.get(manage_url)
        self.assertEqual(anon_resp.status_code, 302)

        self.client.force_login(self.member)
        member_resp = self.client.get(manage_url)
        self.assertEqual(member_resp.status_code, 403)

    def test_staff_can_create_update_hide_and_restore_product(self):
        self.client.force_login(self.staff)
        create_resp = self.client.post(
            reverse("marketplace:manage_product_create"),
            data={
                "name": "Outer Parang",
                "motif": "Parang",
                "category": Product.Category.PAKAIAN,
                "description": "Outer dari kain jarik.",
                "material_source": "Jarik bekas",
                "artisan_origin": "Solo",
                "badge_status": "Baru",
                "price": 275000,
                "stock": 3,
                "image_url": "https://example.com/outer.webp",
            },
        )
        self.assertRedirects(
            create_resp,
            reverse("marketplace:manage_product_list"),
        )
        created = Product.objects.get(name="Outer Parang")
        self.assertEqual(created.user, self.staff)

        update_resp = self.client.post(
            reverse(
                "marketplace:manage_product_update",
                kwargs={"pk": self.product.pk},
            ),
            data={
                "name": "Sling Bag Kawung Spesial",
                "motif": "Kawung",
                "category": Product.Category.TAS,
                "description": "Diperbarui",
                "material_source": "Selendang bekas",
                "artisan_origin": "Yogyakarta",
                "badge_status": "",
                "price": 160000,
                "stock": 5,
                "image_url": "",
            },
        )
        self.assertRedirects(
            update_resp,
            reverse("marketplace:manage_product_list"),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Sling Bag Kawung Spesial")
        self.assertEqual(self.product.stock, 5)

        delete_resp = self.client.post(
            reverse(
                "marketplace:manage_product_delete",
                kwargs={"pk": self.product.pk},
            )
        )
        self.assertRedirects(
            delete_resp,
            reverse("marketplace:manage_product_list"),
        )
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_deleted)

        restore_resp = self.client.post(
            reverse(
                "marketplace:manage_product_restore",
                kwargs={"pk": self.product.pk},
            )
        )
        self.assertRedirects(
            restore_resp,
            reverse("marketplace:manage_product_list"),
        )
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_deleted)


class MarketplaceAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password123",
        )
        self.buyer = User.objects.create_user(
            username="buyer",
            password="password123",
        )
        self.product = Product.objects.create(
            name="Pouch Kawung",
            motif="Kawung",
            category=Product.Category.POUCH,
            material_source="Perca",
            artisan_origin="Yogyakarta",
            price=65000,
            stock=4,
        )
        self.order = place_order(
            self.buyer,
            self.product.pk,
            quantity=2,
            delivery_method=Order.DeliveryMethod.KURIR,
            address="Jl. Margonda, Depok",
            whatsapp="+6281234567890",
        )

    def test_order_admin_form_enforces_workflow_transitions(self):
        base_data = model_to_dict(self.order)
        form_invalid = OrderAdminForm(
            instance=self.order,
            data={
                **base_data,
                "status": Order.Status.COMPLETED,
            },
        )
        self.assertFalse(form_invalid.is_valid())
        self.assertIn("status", form_invalid.errors)

        form_valid = OrderAdminForm(
            instance=self.order,
            data={
                **base_data,
                "status": Order.Status.PROCESSING,
            },
        )
        self.assertTrue(form_valid.is_valid(), form_valid.errors)

    def test_order_admin_save_model_restores_stock_and_logs_history_on_cancel(self):
        order_admin = OrderAdmin(Order, admin.site)
        request = RequestFactory().post("/admin/marketplace/order/")
        request.user = self.admin_user

        base_data = model_to_dict(self.order)
        form = OrderAdminForm(
            instance=self.order,
            data={
                **base_data,
                "status": Order.Status.CANCELLED,
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        updated_order = form.save(commit=False)
        order_admin.save_model(request, updated_order, form, change=True)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)
        self.assertEqual(
            OrderStatusHistory.objects.filter(order=self.order).count(),
            2,
        )

User = get_user_model()


class ProductFormTests(TestCase):
    valid_data = {
        "name": "  Tote Bag Parang Rusak  ",
        "motif": "  Parang Rusak ",
        "category": Product.Category.TAS,
        "description": "  Tas jinjing dari kain sarung bekas.  ",
        "material_source": "  Sarung bekas Solo ",
        "artisan_origin": "  Sanggar Laweyan ",
        "badge_status": "  Terlaris ",
        "price": 185000,
        "stock": 4,
        "image_url": "https://example.com/totebag.webp",
    }

    def test_valid_product_form_strips_fields(self):
        form = ProductForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["name"], "Tote Bag Parang Rusak")
        self.assertEqual(form.cleaned_data["motif"], "Parang Rusak")
        self.assertEqual(form.cleaned_data["badge_status"], "Terlaris")

    def test_rejects_price_outside_supported_range(self):
        for invalid_price in (0, 500, 100_000_001):
            with self.subTest(price=invalid_price):
                data = {**self.valid_data, "price": invalid_price}
                form = ProductForm(data=data)
                self.assertFalse(form.is_valid())
                self.assertIn("price", form.errors)

    def test_rejects_non_https_image_url_and_allows_blank(self):
        insecure = {**self.valid_data, "image_url": "http://example.com/a.jpg"}
        form = ProductForm(data=insecure)
        self.assertFalse(form.is_valid())
        self.assertIn("image_url", form.errors)

        blank_url = {**self.valid_data, "image_url": ""}
        form_blank = ProductForm(data=blank_url)
        self.assertTrue(form_blank.is_valid(), form_blank.errors)
        self.assertIsNone(form_blank.cleaned_data["image_url"])


class CheckoutFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(
            name="Pouch Kawung Mini",
            motif="Kawung",
            category=Product.Category.POUCH,
            material_source="Kain perca kemeja",
            artisan_origin="Batik Giriloyo",
            price=65000,
            stock=5,
        )
        cls.dropoff = DropOffPoint.objects.create(
            name="Galeri ReBatik Depok",
            address="Jl. Margonda Raya No. 10",
            city="Depok",
        )

    def test_normalizes_indonesian_whatsapp_numbers(self):
        for raw in (
            "081234567890",
            "6281234567890",
            "+6281234567890",
            "+62 812-3456-7890",
        ):
            with self.subTest(raw=raw):
                form = CheckoutForm(
                    data={
                        "quantity": 2,
                        "delivery_method": Order.DeliveryMethod.DROP_OFF,
                        "dropoff_point": self.dropoff.pk,
                        "address": "Akan dihapus",
                        "whatsapp": raw,
                        "notes": "",
                    },
                    product=self.product,
                )
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data["whatsapp"], "+6281234567890")
                self.assertEqual(form.cleaned_data["address"], "")

    def test_validates_delivery_method_specific_fields(self):
        missing_dropoff = CheckoutForm(
            data={
                "quantity": 1,
                "delivery_method": Order.DeliveryMethod.DROP_OFF,
                "whatsapp": "081234567890",
            },
            product=self.product,
        )
        self.assertFalse(missing_dropoff.is_valid())
        self.assertIn("dropoff_point", missing_dropoff.errors)

        missing_address = CheckoutForm(
            data={
                "quantity": 1,
                "delivery_method": Order.DeliveryMethod.KURIR,
                "dropoff_point": self.dropoff.pk,
                "address": "   ",
                "whatsapp": "081234567890",
            },
            product=self.product,
        )
        self.assertFalse(missing_address.is_valid())
        self.assertIn("address", missing_address.errors)

        valid_kurir = CheckoutForm(
            data={
                "quantity": 1,
                "delivery_method": Order.DeliveryMethod.KURIR,
                "dropoff_point": self.dropoff.pk,
                "address": "Jl. Akses UI No. 5, Depok",
                "whatsapp": "081234567890",
            },
            product=self.product,
        )
        self.assertTrue(valid_kurir.is_valid(), valid_kurir.errors)
        self.assertIsNone(valid_kurir.cleaned_data["dropoff_point"])

    def test_rejects_quantity_above_available_stock(self):
        form = CheckoutForm(
            data={
                "quantity": 6,
                "delivery_method": Order.DeliveryMethod.DROP_OFF,
                "dropoff_point": self.dropoff.pk,
                "whatsapp": "081234567890",
            },
            product=self.product,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("quantity", form.errors)


class MarketplaceCatalogueViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.p1 = Product.objects.create(
            name="Tote Bag Parang",
            motif="Parang",
            category=Product.Category.TAS,
            material_source="Sarung bekas",
            artisan_origin="Solo",
            price=180000,
            stock=3,
        )
        cls.p2 = Product.objects.create(
            name="Kemeja Mega Mendung",
            motif="Mega Mendung",
            category=Product.Category.PAKAIAN,
            material_source="Kain katun perca",
            artisan_origin="Cirebon",
            price=320000,
            stock=2,
        )
        cls.p3 = Product.objects.create(
            name="Scrunchie Truntum",
            motif="Truntum",
            category=Product.Category.AKSESORIS,
            material_source="Potongan kebaya",
            artisan_origin="Depok",
            price=25000,
            stock=10,
        )
        cls.hidden_product = Product.objects.create(
            name="Produk Tersembunyi",
            motif="Kawung",
            category=Product.Category.POUCH,
            material_source="Sisa kain",
            artisan_origin="Yogyakarta",
            price=50000,
            stock=1,
            is_deleted=True,
        )
        cls.drop_depok = DropOffPoint.objects.create(
            name="Titik Depok",
            address="Margonda",
            city="Depok",
        )
        cls.drop_bandung = DropOffPoint.objects.create(
            name="Titik Bandung",
            address="Dago",
            city="Bandung",
        )

    def test_catalogue_hides_deleted_products_and_supports_filters(self):
        response = self.client.get(reverse("marketplace:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.p1.name)
        self.assertNotContains(response, self.hidden_product.name)

        cat_response = self.client.get(
            reverse("marketplace:home"),
            {"category": "PAKAIAN", "q": "Cirebon", "sort": "price_asc"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(cat_response.status_code, 200)
        self.assertEqual(list(cat_response.context["products"]), [self.p2])

    def test_catalogue_ignores_invalid_filter_parameters_and_sorts_by_price(self):
        response = self.client.get(
            reverse("marketplace:home"),
            {"category": "INVALID", "sort": "price_asc"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_category"], "")
        self.assertEqual(
            list(response.context["products"]),
            [self.p3, self.p1, self.p2],
        )

    def test_product_detail_returns_404_for_hidden_product(self):
        ok_resp = self.client.get(
            reverse("marketplace:product_detail", kwargs={"pk": self.p1.pk})
        )
        self.assertEqual(ok_resp.status_code, 200)

        hidden_resp = self.client.get(
            reverse(
                "marketplace:product_detail",
                kwargs={"pk": self.hidden_product.pk},
            )
        )
        self.assertEqual(hidden_resp.status_code, 404)

    def test_dropoff_list_filters_by_city_and_search(self):
        response = self.client.get(
            reverse("marketplace:dropoff"),
            {"city": "Depok", "q": "Margonda"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["drop_points"]), [self.drop_depok])


class CheckoutAndOrderViewTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            username="buyer",
            password="password123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="password123",
        )
        self.product = Product.objects.create(
            name="Tote Bag Parang Rusak",
            motif="Parang Rusak",
            category=Product.Category.TAS,
            material_source="Sarung bekas",
            artisan_origin="Sanggar Laweyan",
            price=185000,
            stock=3,
        )
        self.dropoff = DropOffPoint.objects.create(
            name="Galeri Depok",
            address="Jl. Margonda",
            city="Depok",
        )

    def test_checkout_requires_authentication(self):
        url = reverse("marketplace:checkout", kwargs={"pk": self.product.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_checkout_reserves_stock_snapshots_price_and_creates_history(self):
        self.client.force_login(self.buyer)
        url = reverse("marketplace:checkout", kwargs={"pk": self.product.pk})
        response = self.client.post(
            url,
            data={
                "quantity": 2,
                "delivery_method": Order.DeliveryMethod.DROP_OFF,
                "dropoff_point": self.dropoff.pk,
                "whatsapp": "081234567890",
                "notes": "Ambil sore hari",
            },
        )
        order = Order.objects.get(user=self.buyer)
        self.assertRedirects(
            response,
            reverse("marketplace:order_success", kwargs={"pk": order.pk}),
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
        self.assertEqual(order.product_name, "Tote Bag Parang Rusak")
        self.assertEqual(order.unit_price, 185000)
        self.assertEqual(order.total_price, 370000)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertTrue(order.reference_code.startswith("MP-"))
        self.assertEqual(order.status_history.count(), 1)

        # Updating product price later must not alter historical order snapshot
        self.product.price = 250000
        self.product.save()
        order.refresh_from_db()
        self.assertEqual(order.unit_price, 185000)
        self.assertEqual(order.total_price, 370000)

    def test_service_raises_out_of_stock_when_stock_is_insufficient(self):
        with self.assertRaises(OutOfStock):
            place_order(
                self.buyer,
                self.product.pk,
                quantity=5,
                delivery_method=Order.DeliveryMethod.KURIR,
                address="Jl. UI Depok",
                whatsapp="+6281234567890",
            )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_owner_isolation_and_cancellation_restores_stock(self):
        order = place_order(
            self.buyer,
            self.product.pk,
            quantity=2,
            delivery_method=Order.DeliveryMethod.DROP_OFF,
            dropoff_point=self.dropoff,
            whatsapp="+6281234567890",
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

        # Other user cannot view or cancel buyer's order
        self.client.force_login(self.other_user)
        detail_url = reverse("marketplace:order_detail", kwargs={"pk": order.pk})
        cancel_url = reverse("marketplace:order_cancel", kwargs={"pk": order.pk})
        self.assertEqual(self.client.get(detail_url).status_code, 404)
        self.assertEqual(self.client.post(cancel_url).status_code, 404)

        # Owner GET renders confirmation without cancelling
        self.client.force_login(self.buyer)
        get_resp = self.client.get(cancel_url)
        self.assertEqual(get_resp.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

        # Owner POST cancels and restores stock
        post_resp = self.client.post(cancel_url)
        self.assertRedirects(post_resp, detail_url)
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(order.status_history.count(), 2)

        # Cancelling again is rejected
        with self.assertRaises(OrderTransitionNotAllowed):
            cancel_order(order.pk, by_user=self.buyer, require_owner=True)


class StaffProductManagementViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staffuser",
            password="password123",
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username="member",
            password="password123",
            is_staff=False,
        )
        self.product = Product.objects.create(
            name="Sling Bag Kawung",
            motif="Kawung",
            category=Product.Category.TAS,
            material_source="Selendang bekas",
            artisan_origin="Yogyakarta",
            price=150000,
            stock=2,
        )

    def test_staff_views_reject_anonymous_and_non_staff_users(self):
        manage_url = reverse("marketplace:manage_product_list")
        anon_resp = self.client.get(manage_url)
        self.assertEqual(anon_resp.status_code, 302)

        self.client.force_login(self.member)
        member_resp = self.client.get(manage_url)
        self.assertEqual(member_resp.status_code, 403)

    def test_staff_can_create_update_hide_and_restore_product(self):
        self.client.force_login(self.staff)
        create_resp = self.client.post(
            reverse("marketplace:manage_product_create"),
            data={
                "name": "Outer Parang",
                "motif": "Parang",
                "category": Product.Category.PAKAIAN,
                "description": "Outer dari kain jarik.",
                "material_source": "Jarik bekas",
                "artisan_origin": "Solo",
                "badge_status": "Baru",
                "price": 275000,
                "stock": 3,
                "image_url": "https://example.com/outer.webp",
            },
        )
        self.assertRedirects(
            create_resp,
            reverse("marketplace:manage_product_list"),
        )
        created = Product.objects.get(name="Outer Parang")
        self.assertEqual(created.user, self.staff)

        update_resp = self.client.post(
            reverse(
                "marketplace:manage_product_update",
                kwargs={"pk": self.product.pk},
            ),
            data={
                "name": "Sling Bag Kawung Spesial",
                "motif": "Kawung",
                "category": Product.Category.TAS,
                "description": "Diperbarui",
                "material_source": "Selendang bekas",
                "artisan_origin": "Yogyakarta",
                "badge_status": "",
                "price": 160000,
                "stock": 5,
                "image_url": "",
            },
        )
        self.assertRedirects(
            update_resp,
            reverse("marketplace:manage_product_list"),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Sling Bag Kawung Spesial")
        self.assertEqual(self.product.stock, 5)

        delete_resp = self.client.post(
            reverse(
                "marketplace:manage_product_delete",
                kwargs={"pk": self.product.pk},
            )
        )
        self.assertRedirects(
            delete_resp,
            reverse("marketplace:manage_product_list"),
        )
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_deleted)

        restore_resp = self.client.post(
            reverse(
                "marketplace:manage_product_restore",
                kwargs={"pk": self.product.pk},
            )
        )
        self.assertRedirects(
            restore_resp,
            reverse("marketplace:manage_product_list"),
        )
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_deleted)


class MarketplaceAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password123",
        )
        self.buyer = User.objects.create_user(
            username="buyer",
            password="password123",
        )
        self.product = Product.objects.create(
            name="Pouch Kawung",
            motif="Kawung",
            category=Product.Category.POUCH,
            material_source="Perca",
            artisan_origin="Yogyakarta",
            price=65000,
            stock=4,
        )
        self.order = place_order(
            self.buyer,
            self.product.pk,
            quantity=2,
            delivery_method=Order.DeliveryMethod.KURIR,
            address="Jl. Margonda, Depok",
            whatsapp="+6281234567890",
        )

    def test_order_admin_form_enforces_workflow_transitions(self):
        base_data = model_to_dict(self.order)
        form_invalid = OrderAdminForm(
            instance=self.order,
            data={
                **base_data,
                "status": Order.Status.COMPLETED,
            },
        )
        self.assertFalse(form_invalid.is_valid())
        self.assertIn("status", form_invalid.errors)

        form_valid = OrderAdminForm(
            instance=self.order,
            data={
                **base_data,
                "status": Order.Status.PROCESSING,
            },
        )
        self.assertTrue(form_valid.is_valid(), form_valid.errors)

    def test_order_admin_save_model_restores_stock_and_logs_history_on_cancel(self):
        order_admin = OrderAdmin(Order, admin.site)
        request = RequestFactory().post("/admin/marketplace/order/")
        request.user = self.admin_user

        base_data = model_to_dict(self.order)
        form = OrderAdminForm(
            instance=self.order,
            data={
                **base_data,
                "status": Order.Status.CANCELLED,
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        updated_order = form.save(commit=False)
        order_admin.save_model(request, updated_order, form, change=True)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)
        self.assertEqual(
            OrderStatusHistory.objects.filter(order=self.order).count(),
            2,
        )

