from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from .forms import UpcyclingRequestForm
from .models import UpcyclingRequest

User = get_user_model()

class UpcyclingRequestFormTests(SimpleTestCase):
    def setUp(self):
        self.valid_data = {
            "fabric": "PARANG",
            "category": "TAS",
            "product": "TOTE_BAG",
            "quantity": 1,
            "notes": "",
            "delivery_method": "DROP_OFF",
            "address": "Depok",
            "whatsapp": "081234567890",
        }

    def test_valid_request_form(self):
        form = UpcyclingRequestForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_product_outside_category(self):
        data = self.valid_data.copy()
        data["product"] = "KEMEJA"

        form = UpcyclingRequestForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("product", form.errors)

    def test_rejects_quantity_over_20(self):
        data = self.valid_data.copy()
        data["quantity"] = 21

        form = UpcyclingRequestForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("quantity", form.errors)

class UpcyclingRequestViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="rezky",
            password="password123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="password123",
        )
        self.form_data = {
            "fabric": "PARANG",
            "category": "TAS",
            "product": "TOTE_BAG",
            "quantity": 1,
            "notes": "",
            "delivery_method": "DROP_OFF",
            "address": "Depok",
            "whatsapp": "081234567890",
        }

    def make_request(self, user):
        return UpcyclingRequest.objects.create(
            user=user,
            fabric="PARANG",
            category="TAS",
            product="TOTE_BAG",
            quantity=1,
            notes="",
            delivery_method="DROP_OFF",
            address="Depok",
            whatsapp="081234567890",
        )

    def test_user_can_create_request(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("upcycling:request_create"),
            self.form_data,
        )

        self.assertRedirects(
            response,
            reverse("upcycling:request_list"),
        )
        self.assertTrue(
            UpcyclingRequest.objects.filter(user=self.user).exists()
        )

    def test_user_sees_only_own_requests(self):
        own_request = self.make_request(self.user)
        other_request = self.make_request(self.other_user)
        self.client.force_login(self.user)

        response = self.client.get(reverse("upcycling:request_list"))

        self.assertEqual(
            list(response.context["requests"]),
            [own_request],
        )
        self.assertNotIn(other_request, response.context["requests"])

    def test_user_cannot_open_another_users_request(self):
        other_request = self.make_request(self.other_user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "upcycling:request_detail",
                args=[other_request.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_user_can_update_own_request(self):
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)
        data = self.form_data.copy()
        data["quantity"] = 2

        response = self.client.post(
            reverse(
                "upcycling:request_update",
                args=[upcycling_request.pk],
            ),
            data,
        )

        upcycling_request.refresh_from_db()
        self.assertEqual(upcycling_request.quantity, 2)
        self.assertEqual(response.status_code, 302)

    def test_user_can_delete_own_request(self):
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "upcycling:request_delete",
                args=[upcycling_request.pk],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            UpcyclingRequest.objects.filter(pk=upcycling_request.pk).exists()
        )