from datetime import datetime, timezone as datetime_timezone

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .admin import UpcyclingRequestAdminForm
from .forms import UpcyclingRequestForm
from .models import UpcyclingRequest


User = get_user_model()


class UpcyclingRequestFormTests(SimpleTestCase):
    valid_data = {
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

    def test_normalizes_supported_indonesian_whatsapp_formats(self):
        for phone_number in (
            "081234567890",
            "6281234567890",
            "+6281234567890",
            "+62 812-3456-7890",
        ):
            with self.subTest(phone_number=phone_number):
                data = self.valid_data.copy()
                data["whatsapp"] = phone_number
                form = UpcyclingRequestForm(data=data)

                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(
                    form.cleaned_data["whatsapp"],
                    "+6281234567890",
                )

    def test_rejects_invalid_indonesian_whatsapp_number(self):
        data = self.valid_data.copy()
        data["whatsapp"] = "+621234567890"
        form = UpcyclingRequestForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("whatsapp", form.errors)

    def test_requires_custom_product_name_for_other_product(self):
        data = self.valid_data.copy()
        data["product"] = "LAINNYA"

        form = UpcyclingRequestForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("custom_product", form.errors)

    def test_accepts_and_displays_custom_product_name(self):
        data = self.valid_data.copy()
        data.update(product="LAINNYA", custom_product="Sarung bantal")
        form = UpcyclingRequestForm(data=data)

        self.assertTrue(form.is_valid(), form.errors)
        request = form.save(commit=False)
        self.assertEqual(request.get_product_name(), "Sarung bantal")

    def test_clears_custom_product_for_standard_product(self):
        data = self.valid_data.copy()
        data["custom_product"] = "Nama lama"
        form = UpcyclingRequestForm(data=data)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["custom_product"], "")

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

    def test_rejects_quantity_below_1(self):
        data = self.valid_data.copy()
        data["quantity"] = 0

        form = UpcyclingRequestForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("quantity", form.errors)

    def test_rejects_notes_longer_than_model_limit(self):
        data = self.valid_data.copy()
        data["notes"] = "x" * 2001

        form = UpcyclingRequestForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("notes", form.errors)
        self.assertEqual(
            form.errors["notes"],
            ["Catatan maksimal 2000 karakter."],
        )


class UpcyclingRequestAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="admin-form-user")

    def test_request_model_is_registered_in_admin(self):
        self.assertIn(UpcyclingRequest, admin.site._registry)

    def make_form(self, current_status, new_status):
        upcycling_request = UpcyclingRequest.objects.create(
            user=self.user,
            fabric="PARANG",
            category="TAS",
            product="TOTE_BAG",
            quantity=1,
            delivery_method="DROP_OFF",
            address="Depok",
            whatsapp="+6281234567890",
            status=current_status,
        )
        form_data = model_to_dict(upcycling_request)
        form_data["status"] = new_status
        return UpcyclingRequestAdminForm(
            data=form_data,
            instance=upcycling_request,
        )

    def test_admin_form_accepts_pending_to_processing(self):
        form = self.make_form(
            UpcyclingRequest.Status.PENDING,
            UpcyclingRequest.Status.PROCESSING,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_admin_form_accepts_processing_to_completed(self):
        form = self.make_form(
            UpcyclingRequest.Status.PROCESSING,
            UpcyclingRequest.Status.COMPLETED,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_admin_form_rejects_pending_to_completed(self):
        form = self.make_form(
            UpcyclingRequest.Status.PENDING,
            UpcyclingRequest.Status.COMPLETED,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("status", form.errors)

    def test_admin_form_rejects_changes_from_terminal_statuses(self):
        for terminal_status in (
            UpcyclingRequest.Status.COMPLETED,
            UpcyclingRequest.Status.CANCELLED,
        ):
            with self.subTest(status=terminal_status):
                form = self.make_form(
                    terminal_status,
                    UpcyclingRequest.Status.PENDING,
                )

                self.assertFalse(form.is_valid())
                self.assertIn("status", form.errors)


class UpcyclingRequestViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="rezky",
            password="password123",
        )
        cls.other_user = User.objects.create_user(
            username="other",
            password="password123",
        )

    form_data = {
        "fabric": "PARANG",
        "category": "TAS",
        "product": "TOTE_BAG",
        "quantity": 1,
        "notes": "",
        "delivery_method": "DROP_OFF",
        "address": "Depok",
        "whatsapp": "081234567890",
    }

    def make_request(self, user, **overrides):
        data = {
            "fabric": "PARANG",
            "category": "TAS",
            "product": "TOTE_BAG",
            "quantity": 1,
            "notes": "",
            "delivery_method": "DROP_OFF",
            "address": "Depok",
            "whatsapp": "081234567890",
        }
        data.update(overrides)
        return UpcyclingRequest.objects.create(user=user, **data)

    def test_request_list_paginates_25_requests_and_preserves_status_filter(self):
        for _ in range(25):
            self.make_request(self.user, status=UpcyclingRequest.Status.COMPLETED)
        self.client.force_login(self.user)

        first_page = self.client.get(
            reverse("upcycling:request_list"),
            {"status": "COMPLETED"},
        )
        self.assertEqual(len(first_page.context["requests"]), 10)
        self.assertEqual(first_page.content.count(b"<article"), 10)
        self.assertContains(first_page, "?status=COMPLETED&amp;page=2")

        second_page = self.client.get(
            reverse("upcycling:request_list"),
            {"status": "COMPLETED", "page": 2},
        )
        self.assertEqual(len(second_page.context["requests"]), 10)
        self.assertEqual(second_page.content.count(b"<article"), 10)

        third_page = self.client.get(
            reverse("upcycling:request_list"),
            {"status": "COMPLETED", "page": 3},
        )
        self.assertEqual(len(third_page.context["requests"]), 5)
        self.assertEqual(third_page.content.count(b"<article"), 5)

    def test_request_list_invalid_and_out_of_range_pages_are_normalized(self):
        for _ in range(25):
            self.make_request(self.user)
        self.client.force_login(self.user)
        url = reverse("upcycling:request_list")

        out_of_range = self.client.get(url, {"page": 999})
        self.assertEqual(out_of_range.context["page_obj"].number, 3)
        self.assertEqual(len(out_of_range.context["requests"]), 5)

        invalid_page = self.client.get(url, {"page": "abc"})
        self.assertEqual(invalid_page.context["page_obj"].number, 1)
        self.assertEqual(len(invalid_page.context["requests"]), 10)

    def test_user_can_create_request_and_is_redirected_to_success_page(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("upcycling:request_create"),
            self.form_data,
        )
        upcycling_request = UpcyclingRequest.objects.get(user=self.user)

        self.assertRedirects(
            response,
            reverse("upcycling:request_success", args=[upcycling_request.pk]),
        )
        self.assertEqual(upcycling_request.status, "PENDING")

    def test_create_ignores_posted_user_and_status(self):
        self.client.force_login(self.user)
        data = self.form_data | {
            "user": self.other_user.pk,
            "status": "PROCESSING",
        }

        response = self.client.post(reverse("upcycling:request_create"), data)

        self.assertEqual(response.status_code, 302)
        created_request = UpcyclingRequest.objects.get(user=self.user)
        self.assertEqual(created_request.status, "PENDING")
        self.assertFalse(
            UpcyclingRequest.objects.filter(user=self.other_user).exists()
        )

    def test_user_cannot_create_more_than_ten_pending_requests(self):
        for _ in range(10):
            self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("upcycling:request_create"),
            self.form_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            UpcyclingRequest.objects.filter(
                user=self.user,
                status="PENDING",
            ).count(),
            10,
        )
        self.assertContains(response, "sudah memiliki 10 permintaan")

    def test_create_page_redirects_when_user_has_ten_pending_requests(self):
        for _ in range(10):
            self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_create"),
            follow=True,
        )

        self.assertRedirects(response, reverse("upcycling:request_list"))
        self.assertContains(response, "sudah memiliki 10 permintaan")

    def test_incomplete_form_renders_error_summary(self):
        self.client.force_login(self.user)
        incomplete_data = self.form_data.copy()
        incomplete_data.pop("fabric")

        response = self.client.post(
            reverse("upcycling:request_create"),
            incomplete_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="form-error-summary"')
        self.assertContains(response, 'href="#pilih-kain"')

    def test_user_can_view_success_page_for_own_request(self):
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_success", args=[upcycling_request.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["upcycling_request"],
            upcycling_request,
        )
        self.assertEqual(
            response.context["reference_code"],
            f"RB-{str(upcycling_request.pk).split('-')[0].upper()}",
        )

    def test_user_cannot_view_another_users_success_page(self):
        other_request = self.make_request(self.other_user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_success", args=[other_request.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_user_sees_only_own_requests(self):
        own_request = self.make_request(self.user)
        other_request = self.make_request(self.other_user)
        self.client.force_login(self.user)

        response = self.client.get(reverse("upcycling:request_list"))

        self.assertEqual(list(response.context["requests"]), [own_request])
        self.assertNotIn(other_request, response.context["requests"])

    def test_user_can_filter_requests_by_status_and_category(self):
        self.make_request(self.user, status="PENDING")
        matching_request = self.make_request(
            self.user,
            status="COMPLETED",
            category="POUCH",
            product="POUCH",
        )
        self.make_request(self.user, status="PROCESSING", category="TAS")
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_list"),
            {"status": "COMPLETED", "category": "POUCH"},
        )

        self.assertEqual(list(response.context["requests"]), [matching_request])
        self.assertEqual(response.context["selected_status"], "COMPLETED")
        self.assertEqual(response.context["selected_category"], "POUCH")

    def test_user_can_filter_ongoing_requests(self):
        pending_request = self.make_request(self.user, status="PENDING")
        processing_request = self.make_request(self.user, status="PROCESSING")
        self.make_request(self.user, status="COMPLETED")
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_list"),
            {"status": "ONGOING"},
        )

        self.assertCountEqual(
            response.context["requests"],
            [pending_request, processing_request],
        )

    def test_invalid_list_filters_are_ignored(self):
        first_request = self.make_request(self.user)
        second_request = self.make_request(self.user, category="POUCH", product="POUCH")
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_list"),
            {"status": "INVALID", "category": "INVALID"},
        )

        self.assertCountEqual(
            response.context["requests"],
            [first_request, second_request],
        )
        self.assertEqual(response.context["selected_status"], "")
        self.assertEqual(response.context["selected_category"], "")

    def test_user_cannot_open_another_users_request(self):
        other_request = self.make_request(self.other_user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_detail", args=[other_request.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_detail_timeline_matches_each_request_status(self):
        self.client.force_login(self.user)
        expected_states = {
            "PENDING": ["done", "current", "upcoming", "upcoming"],
            "PROCESSING": ["done", "done", "current", "upcoming"],
            "COMPLETED": ["done", "done", "done", "done"],
            "CANCELLED": ["done", "cancelled"],
        }

        for status, expected in expected_states.items():
            with self.subTest(status=status):
                upcycling_request = self.make_request(self.user, status=status)
                response = self.client.get(
                    reverse("upcycling:request_detail", args=[upcycling_request.pk])
                )
                states = [step["state"] for step in response.context["timeline_steps"]]

                self.assertEqual(response.status_code, 200)
                self.assertEqual(states, expected)

    def test_detail_formats_submission_date_in_jakarta_timezone(self):
        upcycling_request = self.make_request(self.user)
        UpcyclingRequest.objects.filter(pk=upcycling_request.pk).update(
            created_at=datetime(
                2026,
                10,
                22,
                18,
                30,
                tzinfo=datetime_timezone.utc,
            )
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )

        self.assertContains(response, "23/10/2026")

    def test_user_can_update_own_pending_request_and_sees_toast(self):
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)
        data = self.form_data.copy()
        data["quantity"] = 2

        response = self.client.post(
            reverse("upcycling:request_update", args=[upcycling_request.pk]),
            data,
            follow=True,
        )

        upcycling_request.refresh_from_db()
        self.assertEqual(upcycling_request.quantity, 2)
        self.assertContains(response, "Permintaan berhasil diperbarui.")

    def test_update_does_not_accept_posted_user_or_status(self):
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)
        data = self.form_data | {
            "user": self.other_user.pk,
            "status": "PROCESSING",
        }

        response = self.client.post(
            reverse("upcycling:request_update", args=[upcycling_request.pk]),
            data,
        )

        self.assertEqual(response.status_code, 302)
        upcycling_request.refresh_from_db()
        self.assertEqual(upcycling_request.user, self.user)
        self.assertEqual(upcycling_request.status, "PENDING")

    def test_user_can_open_edit_form_for_own_pending_request(self):
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_update", args=[upcycling_request.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_update"])
        self.assertEqual(response.context["form"].instance, upcycling_request)

    def test_user_cannot_update_request_after_review_begins(self):
        upcycling_request = self.make_request(self.user, status="PROCESSING")
        self.client.force_login(self.user)
        data = self.form_data.copy()
        data["quantity"] = 2

        response = self.client.post(
            reverse("upcycling:request_update", args=[upcycling_request.pk]),
            data,
            follow=True,
        )

        upcycling_request.refresh_from_db()
        self.assertEqual(upcycling_request.quantity, 1)
        self.assertContains(
            response,
            "Permintaan hanya bisa diedit saat masih menunggu tinjauan.",
        )

    def test_user_cannot_update_another_users_request(self):
        other_request = self.make_request(self.other_user)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("upcycling:request_update", args=[other_request.pk]),
            self.form_data,
        )

        self.assertEqual(response.status_code, 404)

    def test_user_can_delete_own_pending_request_and_sees_toast(self):
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("upcycling:request_delete", args=[upcycling_request.pk]),
            follow=True,
        )

        self.assertFalse(
            UpcyclingRequest.objects.filter(pk=upcycling_request.pk).exists()
        )
        self.assertContains(response, "Permintaan berhasil dihapus.")

    def test_user_can_open_delete_confirmation_for_own_pending_request(self):
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_delete", args=[upcycling_request.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["upcycling_request"], upcycling_request)

    def test_user_cannot_delete_request_after_review_begins(self):
        upcycling_request = self.make_request(self.user, status="PROCESSING")
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("upcycling:request_delete", args=[upcycling_request.pk]),
            follow=True,
        )

        self.assertTrue(
            UpcyclingRequest.objects.filter(pk=upcycling_request.pk).exists()
        )
        self.assertContains(
            response,
            "Permintaan hanya bisa dihapus saat masih menunggu tinjauan.",
        )

    def test_user_cannot_delete_another_users_request(self):
        other_request = self.make_request(self.other_user)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("upcycling:request_delete", args=[other_request.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_request_form_embeds_product_options_for_each_category(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_create")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["product_options_by_category"]["TAS"],
            [
                {"value": "TOTE_BAG", "label": "Tote Bag"},
                {"value": "SLING_BAG", "label": "Sling Bag"},
                {"value": "LAINNYA", "label": "Lainnya"},
            ],
        )
        self.assertContains(response, 'id="product-options-data"')
