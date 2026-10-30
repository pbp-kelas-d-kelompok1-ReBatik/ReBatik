from datetime import datetime, timedelta, timezone as datetime_timezone
from base64 import b64decode
from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.forms.models import model_to_dict
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from .admin import UpcyclingRequestAdminForm
from .forms import FabricHandoffForm, UpcyclingRequestForm
from .forms import ProductDeliveryForm
from .models import (
    AdditionalFabricPhoto,
    AdditionalReferencePhoto,
    ArtisanProfile,
    ProductType,
    UpcyclingRateLimitBucket,
    UpcyclingRequest,
    UpcyclingStatusHistory,
)
from .security import consume_upcycling_rate_limit
from .templatetags.upcycling_format import rupiah


User = get_user_model()
TINY_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"
)


class UpcyclingPriceFormatTests(SimpleTestCase):
    def test_rupiah_uses_indonesian_thousands_separator(self):
        self.assertEqual(rupiah(Decimal("95000.00")), "95.000")


class UpcyclingRequestFormTests(SimpleTestCase):
    valid_data = {
        "fabric": "DENIM",
        "current_item_form": "PANTS",
        "has_batik_pattern": "NO",
        "category": "TAS",
        "product": "TOTE_BAG",
        "quantity": 1,
        "notes": "",
        "whatsapp": "081234567890",
        "fabric_condition": "GOOD",
        "fabric_dimensions": "1 celana",
    }

    def form(self, data):
        return UpcyclingRequestForm(
            data=data,
            files={"fabric_photos": [SimpleUploadedFile("fabric.png", TINY_PNG, content_type="image/png")]},
        )

    def test_valid_request_form(self):
        """Test behavior: valid request form."""
        form = self.form(self.valid_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("fabric_composition", form.fields)
        self.assertNotIn("design_notes", form.fields)

    def test_batik_pattern_requires_an_explicit_choice_on_new_request(self):
        empty_form = UpcyclingRequestForm()
        form = UpcyclingRequestForm(
            data={**self.valid_data, "has_batik_pattern": ""}
        )

        self.assertEqual(empty_form.fields["has_batik_pattern"].initial, "")
        self.assertTrue(form.fields["has_batik_pattern"].required)
        self.assertFalse(form.is_valid())
        self.assertIn("has_batik_pattern", form.errors)

    def test_fabric_upload_accepts_up_to_three_images(self):
        files = [
            SimpleUploadedFile(f"fabric-{index}.png", TINY_PNG, content_type="image/png")
            for index in range(3)
        ]
        form = UpcyclingRequestForm(
            data=self.valid_data,
            files={"fabric_photos": files},
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data["fabric_photos"]), 3)

    def test_fabric_upload_rejects_more_than_three_images(self):
        files = [
            SimpleUploadedFile(f"fabric-{index}.png", TINY_PNG, content_type="image/png")
            for index in range(4)
        ]
        form = UpcyclingRequestForm(
            data=self.valid_data,
            files={"fabric_photos": files},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("fabric_photos", form.errors)

    def test_reference_photos_are_optional_and_limited_to_three_images(self):
        no_references = UpcyclingRequestForm(
            data=self.valid_data,
            files={"fabric_photos": [SimpleUploadedFile("fabric.png", TINY_PNG, content_type="image/png")]},
        )
        self.assertTrue(no_references.is_valid(), no_references.errors)

        files = [
            SimpleUploadedFile(f"reference-{index}.png", TINY_PNG, content_type="image/png")
            for index in range(3)
        ]
        valid_form = UpcyclingRequestForm(
            data=self.valid_data,
            files={"fabric_photos": [SimpleUploadedFile("fabric.png", TINY_PNG, content_type="image/png")] , "reference_photos": files},
        )
        self.assertTrue(valid_form.is_valid(), valid_form.errors)
        self.assertEqual(len(valid_form.cleaned_data["reference_photos"]), 3)

        too_many = UpcyclingRequestForm(
            data=self.valid_data,
            files={
                "fabric_photos": [SimpleUploadedFile("fabric.png", TINY_PNG, content_type="image/png")],
                "reference_photos": [
                    SimpleUploadedFile(f"reference-{index}.png", TINY_PNG, content_type="image/png")
                    for index in range(4)
                ],
            },
        )
        self.assertFalse(too_many.is_valid())
        self.assertIn("reference_photos", too_many.errors)

    def test_photo_inputs_are_preserved_across_htmx_validation_swaps(self):
        form = UpcyclingRequestForm()

        self.assertIn("hx-preserve", form.fields["fabric_photos"].widget.attrs)
        self.assertIn("hx-preserve", form.fields["reference_photos"].widget.attrs)

    def test_fabric_upload_rejects_non_images_and_files_over_five_mb(self):
        invalid_files = [
            SimpleUploadedFile("fabric.txt", b"not an image", content_type="text/plain"),
            SimpleUploadedFile("large.png", b"0" * (5 * 1024 * 1024 + 1), content_type="image/png"),
        ]

        for photo in invalid_files:
            with self.subTest(name=photo.name):
                form = UpcyclingRequestForm(
                    data=self.valid_data,
                    files={"fabric_photos": [photo]},
                )

                self.assertFalse(form.is_valid())
                self.assertIn("fabric_photos", form.errors)

    def test_material_choices_remain_without_technical_composition_field(self):
        form = self.form(self.valid_data)

        self.assertNotIn("fabric_composition", form.fields)
        self.assertEqual(
            form.fields["fabric"].label,
            "Jenis bahan utama yang akan diolah",
        )
        self.assertEqual(
            dict(form.fields["fabric"].choices)["DENIM"],
            "Denim/jeans",
        )
        self.assertEqual(
            dict(form.fields["fabric"].choices)["SYNTHETIC"],
            "Sintetis (misalnya polyester)",
        )
        self.assertIn("UNKNOWN", dict(form.fields["fabric"].choices))
        self.assertNotIn("BATIK", dict(form.fields["fabric"].choices))

    def test_batik_pattern_question_is_separate_from_material_and_optional_addition(self):
        form = self.form({**self.valid_data, "has_batik_pattern": "YES"})

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["has_batik_pattern"], "YES")
        self.assertFalse(form.cleaned_data["wants_batik_accent"])
        self.assertEqual(
            {value for value, _ in form.fields["has_batik_pattern"].choices if value},
            {"YES", "NO", "UNSURE"},
        )
        self.assertTrue(form.fields["current_item_form"].required)

    def test_current_item_form_is_a_separate_required_choice_with_other_details(self):
        form = self.form({**self.valid_data, "current_item_form": "OTHER"})

        self.assertFalse(form.is_valid())
        self.assertIn("current_item_form_other", form.errors)
        self.assertEqual(
            {value for value, _ in form.fields["current_item_form"].choices},
            {"PANTS", "TOP", "JACKET", "FABRIC", "OTHER"},
        )

        form = self.form({
            **self.valid_data,
            "current_item_form": "OTHER",
            "current_item_form_other": "Tas kain lama",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["current_item_form_other"], "Tas kain lama")

    def test_current_item_form_must_be_selected(self):
        form = self.form({**self.valid_data, "current_item_form": ""})

        self.assertFalse(form.is_valid())
        self.assertIn("current_item_form", form.errors)

    def test_unknown_material_does_not_require_other_material_description(self):
        form = self.form(
            {**self.valid_data, "fabric": "UNKNOWN", "fabric_other_description": ""}
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["fabric_other_description"], "")

    def test_batik_addition_preferences_are_optional_and_cleared_when_not_requested(self):
        data = {
            **self.valid_data,
            "batik_motif": "Parang",
            "motif_placement": "Bagian depan",
        }
        form = self.form(data)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data["wants_batik_accent"])
        self.assertEqual(form.cleaned_data["batik_motif"], "")
        self.assertEqual(form.cleaned_data["motif_placement"], "")
        self.assertNotIn("design_notes", form.fields)

    def test_user_can_request_an_optional_batik_accent(self):
        data = {
            **self.valid_data,
            "wants_batik_accent": "on",
            "batik_motif": "Mega Mendung",
            "motif_placement": "Bagian depan tote bag",
        }
        form = self.form(data)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.cleaned_data["wants_batik_accent"])
        self.assertEqual(form.cleaned_data["batik_motif"], "Mega Mendung")
        self.assertEqual(
            form.cleaned_data["motif_placement"],
            "Bagian depan tote bag",
        )

    def test_fabric_condition_select_uses_a_clear_optional_prompt(self):
        """Test behavior: fabric condition has no ambiguous dash option."""
        form = UpcyclingRequestForm()

        self.assertEqual(
            form.fields["fabric_condition"].choices[0],
            ("", "Pilih kondisi (opsional)"),
        )

    def test_request_form_defers_fabric_handoff_details_until_review_approval(self):
        """Test behavior: initial request asks for fabric details, not handoff logistics."""
        form = self.form(self.valid_data)

        self.assertNotIn("fabric_delivery_method", form.fields)
        self.assertNotIn("fabric_delivery_location", form.fields)
        self.assertNotIn("delivery_method", form.fields)
        self.assertNotIn("address", form.fields)

        handoff_form = FabricHandoffForm(instance=UpcyclingRequest())
        self.assertIn("fabric_delivery_method", handoff_form.fields)
        self.assertIn("fabric_delivery_location", handoff_form.fields)
        self.assertFalse(handoff_form.fields["fabric_delivery_location"].required)
        self.assertEqual(
            handoff_form.fields["fabric_delivery_location"].label,
            "Catatan penyerahan (opsional)",
        )
        self.assertEqual(
            handoff_form["fabric_delivery_method"].value(),
            "",
        )

    def test_product_delivery_form_requires_method_and_address_after_quote(self):
        form = ProductDeliveryForm()

        self.assertTrue(form.fields["delivery_method"].required)
        self.assertTrue(form.fields["address"].required)
        self.assertIn("delivery_method", form.fields)
        self.assertIn("address", form.fields)

    def test_normalizes_supported_indonesian_whatsapp_formats(self):
        """Test behavior: normalizes supported indonesian whatsapp formats."""
        for phone_number in (
            "081234567890",
            "6281234567890",
            "+6281234567890",
            "+62 812-3456-7890",
        ):
            with self.subTest(phone_number=phone_number):
                data = self.valid_data.copy()
                data["whatsapp"] = phone_number
                form = self.form(data)

                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(
                    form.cleaned_data["whatsapp"],
                    "+6281234567890",
                )

    def test_rejects_invalid_indonesian_whatsapp_number(self):
        """Test behavior: rejects invalid indonesian whatsapp number."""
        data = self.valid_data.copy()
        data["whatsapp"] = "+621234567890"
        form = self.form(data)

        self.assertFalse(form.is_valid())
        self.assertIn("whatsapp", form.errors)

    def test_requires_custom_product_name_for_other_product(self):
        """Test behavior: requires custom product name for other product."""
        data = self.valid_data.copy()
        data["product"] = "LAINNYA"

        form = self.form(data)

        self.assertFalse(form.is_valid())
        self.assertIn("custom_product", form.errors)

    def test_accepts_and_displays_custom_product_name(self):
        """Test behavior: accepts and displays custom product name."""
        data = self.valid_data.copy()
        data.update(product="LAINNYA", custom_product="Sarung bantal")
        form = self.form(data)

        self.assertTrue(form.is_valid(), form.errors)
        request = form.save(commit=False)
        self.assertEqual(request.get_product_name(), "Sarung bantal")

    def test_clears_custom_product_for_standard_product(self):
        """Test behavior: clears custom product for standard product."""
        data = self.valid_data.copy()
        data["custom_product"] = "Nama lama"
        form = self.form(data)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["custom_product"], "")

    def test_rejects_product_outside_category(self):
        """Test behavior: rejects product outside category."""
        data = self.valid_data.copy()
        data["product"] = "KEMEJA"

        form = self.form(data)

        self.assertFalse(form.is_valid())
        self.assertIn("product", form.errors)

    def test_rejects_quantity_over_20(self):
        """Test behavior: rejects quantity over 20."""
        data = self.valid_data.copy()
        data["quantity"] = 21

        form = self.form(data)

        self.assertFalse(form.is_valid())
        self.assertIn("quantity", form.errors)

    def test_rejects_quantity_below_1(self):
        """Test behavior: rejects quantity below 1."""
        data = self.valid_data.copy()
        data["quantity"] = 0

        form = self.form(data)

        self.assertFalse(form.is_valid())
        self.assertIn("quantity", form.errors)

    def test_rejects_notes_longer_than_model_limit(self):
        """Test behavior: rejects notes longer than model limit."""
        data = self.valid_data.copy()
        data["notes"] = "x" * 2001

        form = self.form(data)

        self.assertFalse(form.is_valid())
        self.assertIn("notes", form.errors)
        self.assertEqual(
            form.errors["notes"],
            ["Catatan maksimal 2000 karakter."],
        )


class UpcyclingRequestAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Prepare shared database records for the test class."""
        cls.user = User.objects.create_user(username="admin-form-user")
        product_type, _ = ProductType.objects.get_or_create(
            code="TOTE_BAG", defaults={"name": "Tote Bag"}
        )
        cls.artisan_user = User.objects.create_user(username="admin-form-artisan")
        artisan_group, _ = Group.objects.get_or_create(name="Artisan")
        cls.artisan_user.groups.add(artisan_group)
        cls.artisan = ArtisanProfile.objects.create(user=cls.artisan_user)
        cls.artisan.specializations.add(product_type)

    def test_request_model_is_registered_in_admin(self):
        """Test behavior: request model is registered in admin."""
        self.assertIn(UpcyclingRequest, admin.site._registry)

    def make_form(self, current_status, new_status):
        """Build a request form for the supplied status transition."""
        upcycling_request = UpcyclingRequest.objects.create(
            user=self.user,
            fabric="DENIM",
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
        if current_status == UpcyclingRequest.Status.PENDING_ASSIGNMENT:
            form_data["artisan"] = self.artisan.pk
        elif current_status != UpcyclingRequest.Status.PENDING_ASSIGNMENT:
            upcycling_request.artisan = self.artisan
            upcycling_request.save(update_fields=("artisan",))
            form_data["artisan"] = self.artisan.pk
        return UpcyclingRequestAdminForm(
            data=form_data,
            instance=upcycling_request,
        )

    def test_admin_form_accepts_pending_to_processing(self):
        """Test behavior: admin form accepts pending to processing."""
        form = self.make_form(
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
            UpcyclingRequest.Status.PENDING_REVIEW,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_admin_form_prevents_artisan_from_handling_own_request(self):
        upcycling_request = UpcyclingRequest.objects.create(
            user=self.artisan_user,
            fabric="DENIM",
            category="TAS",
            product="TOTE_BAG",
            quantity=1,
            delivery_method="DROP_OFF",
            address="Depok",
            whatsapp="081234567890",
        )
        form_data = model_to_dict(upcycling_request)
        form_data["status"] = UpcyclingRequest.Status.PENDING_REVIEW
        form_data["artisan"] = self.artisan.pk

        form = UpcyclingRequestAdminForm(
            data=form_data,
            instance=upcycling_request,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("artisan", form.errors)

    def test_admin_form_rejects_skipping_ready_before_completed(self):
        """Completion must follow READY and include handoff evidence."""
        form = self.make_form(
            UpcyclingRequest.Status.IN_PROGRESS,
            UpcyclingRequest.Status.COMPLETED,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("status", form.errors)

    def test_admin_form_rejects_pending_to_completed(self):
        """Test behavior: admin form rejects pending to completed."""
        form = self.make_form(
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
            UpcyclingRequest.Status.COMPLETED,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("status", form.errors)

    def test_admin_form_rejects_changes_from_terminal_statuses(self):
        """Test behavior: admin form rejects changes from terminal statuses."""
        for terminal_status in (
            UpcyclingRequest.Status.COMPLETED,
            UpcyclingRequest.Status.CANCELLED,
        ):
            with self.subTest(status=terminal_status):
                form = self.make_form(
                    terminal_status,
                    UpcyclingRequest.Status.PENDING_ASSIGNMENT,
                )

                self.assertFalse(form.is_valid())
                self.assertIn("status", form.errors)

    def test_admin_status_change_is_recorded_with_actor_and_previous_status(self):
        """Test behavior: admin status change is recorded with actor and previous status."""
        upcycling_request = UpcyclingRequest.objects.create(
            user=self.user,
            fabric="DENIM",
            category="TAS",
            product="TOTE_BAG",
            quantity=1,
            delivery_method="DROP_OFF",
            address="Depok",
            whatsapp="+6281234567890",
        )
        form_data = model_to_dict(upcycling_request)
        form_data["status"] = UpcyclingRequest.Status.PENDING_REVIEW
        form_data["artisan"] = self.artisan.pk
        form = UpcyclingRequestAdminForm(
            data=form_data,
            instance=upcycling_request,
        )
        self.assertTrue(form.is_valid(), form.errors)

        request = RequestFactory().post("/admin/upcycling/upcyclingrequest/")
        request.user = self.user
        admin.site._registry[UpcyclingRequest].save_model(
            request,
            upcycling_request,
            form,
            change=True,
        )

        history = UpcyclingStatusHistory.objects.get(request=upcycling_request)
        self.assertEqual(history.from_status, UpcyclingRequest.Status.PENDING_ASSIGNMENT)
        self.assertEqual(history.to_status, UpcyclingRequest.Status.PENDING_REVIEW)
        self.assertEqual(history.changed_by, self.user)

    def test_admin_manual_completion_requires_evidence(self):
        """Admin cannot complete a ready request without receipt evidence."""
        upcycling_request = UpcyclingRequest.objects.create(
            user=self.user,
            fabric="DENIM",
            category="TAS",
            product="TOTE_BAG",
            quantity=1,
            delivery_method="DROP_OFF",
            address="Depok",
            whatsapp="+6281234567890",
            status=UpcyclingRequest.Status.READY,
            artisan=self.artisan,
        )
        form_data = model_to_dict(upcycling_request)
        form_data["status"] = UpcyclingRequest.Status.COMPLETED
        form = UpcyclingRequestAdminForm(
            data=form_data,
            instance=upcycling_request,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("delivery_proof", form.errors)
        self.assertIn("completion_notes", form.errors)

    def test_admin_save_without_status_change_does_not_add_history(self):
        """Test behavior: admin save without status change does not add history."""
        upcycling_request = UpcyclingRequest.objects.create(
            user=self.user,
            fabric="DENIM",
            category="TAS",
            product="TOTE_BAG",
            quantity=1,
            delivery_method="DROP_OFF",
            address="Depok",
            whatsapp="+6281234567890",
        )
        form_data = model_to_dict(upcycling_request)
        form = UpcyclingRequestAdminForm(
            data=form_data,
            instance=upcycling_request,
        )
        self.assertTrue(form.is_valid(), form.errors)

        request = RequestFactory().post("/admin/upcycling/upcyclingrequest/")
        request.user = self.user
        admin.site._registry[UpcyclingRequest].save_model(
            request,
            upcycling_request,
            form,
            change=True,
        )

        self.assertFalse(
            UpcyclingStatusHistory.objects.filter(request=upcycling_request).exists()
        )


class UpcyclingRequestViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Prepare shared database records for the test class."""
        cls.user = User.objects.create_user(
            username="rezky",
            password="password123",
        )
        cls.other_user = User.objects.create_user(
            username="other",
            password="password123",
        )

    form_data = {
        "fabric": "DENIM",
        "current_item_form": "PANTS",
        "has_batik_pattern": "NO",
        "fabric_condition": "GOOD",
        "fabric_dimensions": "1 celana jeans",
        "wants_batik_accent": "on",
        "batik_motif": "Mega Mendung",
        "motif_placement": "Bagian depan tote bag",
        "category": "TAS",
        "product": "TOTE_BAG",
        "quantity": 1,
        "notes": "",
        "delivery_method": "DROP_OFF",
        "address": "Depok",
        "whatsapp": "081234567890",
    }

    def make_request(self, user, **overrides):
        """Create a request fixture with optional field overrides."""
        data = {
            "fabric": "DENIM",
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

    def post_form(self, url, data=None, **kwargs):
        payload = (data or self.form_data).copy()
        payload["fabric_photos"] = [
            SimpleUploadedFile("fabric.png", TINY_PNG, content_type="image/png")
        ]
        return self.client.post(url, payload, **kwargs)

    def test_request_list_paginates_25_requests_and_preserves_status_filter(self):
        """Test behavior: request list paginates 25 requests and preserves status filter."""
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
        """Test behavior: request list invalid and out of range pages are normalized."""
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
        """Test behavior: user can create request and is redirected to success page."""
        self.client.force_login(self.user)

        response = self.post_form(
            reverse("upcycling:request_create"),
            self.form_data,
        )
        upcycling_request = UpcyclingRequest.objects.get(user=self.user)

        self.assertRedirects(
            response,
            reverse("upcycling:request_success", args=[upcycling_request.pk]),
        )
        self.assertEqual(upcycling_request.status, "PENDING_ASSIGNMENT")
        self.assertEqual(upcycling_request.fabric_composition, "")
        self.assertEqual(upcycling_request.has_batik_pattern, "NO")
        self.assertEqual(upcycling_request.current_item_form, "PANTS")
        self.assertTrue(upcycling_request.wants_batik_accent)
        self.assertEqual(upcycling_request.batik_motif, "Mega Mendung")
        self.assertEqual(
            upcycling_request.motif_placement,
            "Bagian depan tote bag",
        )

    def test_request_detail_shows_batik_addition_preferences(self):
        upcycling_request = self.make_request(
            self.user,
            wants_batik_accent=True,
            batik_motif="Mega Mendung",
            motif_placement="Bagian depan tote bag",
            design_notes="Aksen kecil berwarna biru muda",
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )

        self.assertContains(response, "Tambahan batik dari ReBatik")
        self.assertContains(response, "Mega Mendung")
        self.assertContains(response, "Bagian depan tote bag")
        self.assertContains(response, "Aksen kecil berwarna biru muda")

    def test_create_form_renders_an_expanded_fabric_photo_upload_area(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("upcycling:request_create"))

        self.assertContains(response, 'id="fabric-photo-upload"')
        self.assertContains(response, 'class="upcycling-photo-input"')
        self.assertContains(response, "Tambah foto barang atau kain")
        self.assertContains(response, 'id="fabric-photo-previews"')
        self.assertContains(response, 'data-existing-photo-count="0"')
        self.assertContains(response, 'src="/static/img/mascot/pointing.webp"')
        self.assertContains(response, 'class="upcycling-photo-add"')
        self.assertContains(response, 'name="fabric_photos"')
        self.assertContains(response, "Pilih 1–3 foto")
        self.assertContains(response, 'id="reference-photo-upload"')
        self.assertContains(response, 'id="reference-photo-previews"')
        self.assertContains(response, 'data-existing-photo-count="0"')
        self.assertContains(response, 'name="reference_photos"')
        self.assertContains(response, "Foto contoh hasil yang Anda inginkan (opsional)")

    def test_edit_form_previews_all_existing_fabric_photos(self):
        request_obj = self.make_request(
            self.user,
            status=UpcyclingRequest.Status.PENDING_ASSIGNMENT,
            fabric_photo=SimpleUploadedFile(
                "fabric-first.png", TINY_PNG, content_type="image/png"
            ),
        )
        for index in range(2):
            AdditionalFabricPhoto.objects.create(
                request=request_obj,
                image=SimpleUploadedFile(
                    f"fabric-extra-{index}.png", TINY_PNG, content_type="image/png"
                ),
            )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_update", args=[request_obj.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="fabric-photo-previews"')
        self.assertContains(response, 'data-existing-photo-count="3"')
        self.assertEqual(response.content.count(b'alt="Pratinjau foto barang atau kain'), 3)
        self.assertContains(response, "3 foto tersimpan")

    def test_edit_form_previews_all_existing_reference_photos(self):
        request_obj = self.make_request(
            self.user,
            status=UpcyclingRequest.Status.PENDING_ASSIGNMENT,
        )
        for index in range(2):
            AdditionalReferencePhoto.objects.create(
                request=request_obj,
                image=SimpleUploadedFile(
                    f"reference-existing-{index}.png",
                    TINY_PNG,
                    content_type="image/png",
                ),
            )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_update", args=[request_obj.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="reference-photo-previews"')
        self.assertContains(response, 'data-existing-photo-count="2"')
        self.assertEqual(
            response.content.count(b'alt="Pratinjau foto contoh hasil'), 2
        )

    def test_create_request_saves_each_uploaded_fabric_photo(self):
        self.client.force_login(self.user)
        payload = self.form_data.copy()
        payload["fabric_photos"] = [
            SimpleUploadedFile(f"fabric-{index}.png", TINY_PNG, content_type="image/png")
            for index in range(3)
        ]
        response = self.client.post(
            reverse("upcycling:request_create"),
            payload,
        )

        self.assertEqual(response.status_code, 302)
        upcycling_request = UpcyclingRequest.objects.get(user=self.user)
        self.assertTrue(upcycling_request.fabric_photo)
        self.assertEqual(upcycling_request.additional_fabric_photos.count(), 2)
        detail_response = self.client.get(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )
        self.assertEqual(len(detail_response.context["fabric_photos"]), 3)

    def test_create_request_saves_and_displays_reference_photos_separately(self):
        self.client.force_login(self.user)
        payload = self.form_data.copy()
        payload["fabric_photos"] = [
            SimpleUploadedFile("fabric.png", TINY_PNG, content_type="image/png")
        ]
        payload["reference_photos"] = [
            SimpleUploadedFile(f"reference-{index}.png", TINY_PNG, content_type="image/png")
            for index in range(2)
        ]

        response = self.client.post(reverse("upcycling:request_create"), payload)

        self.assertEqual(response.status_code, 302)
        upcycling_request = UpcyclingRequest.objects.get(user=self.user)
        self.assertEqual(upcycling_request.reference_photos.count(), 2)
        detail_response = self.client.get(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )
        self.assertEqual(len(detail_response.context["reference_photos"]), 2)
        self.assertContains(detail_response, "Foto referensi produk/desain")
        self.assertEqual(
            detail_response.content.count(
                b'class="aspect-[1.4] w-full rounded-xl bg-[var(--upcycling-soft)] object-cover"'
            ),
            3,
        )
        self.assertNotContains(detail_response, "aspect-square")

    def test_edit_request_can_add_photos_only_up_to_three_total(self):
        upcycling_request = self.make_request(
            self.user,
            fabric_photo=SimpleUploadedFile(
                "existing.png", TINY_PNG, content_type="image/png"
            ),
        )
        self.client.force_login(self.user)
        edit_url = reverse("upcycling:request_update", args=[upcycling_request.pk])

        payload = self.form_data.copy()
        payload["fabric_photos"] = [
            SimpleUploadedFile(f"extra-{index}.png", TINY_PNG, content_type="image/png")
            for index in range(2)
        ]
        response = self.client.post(edit_url, payload)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(upcycling_request.additional_fabric_photos.count(), 2)

        payload["fabric_photos"] = [
            SimpleUploadedFile("too-many.png", TINY_PNG, content_type="image/png")
        ]
        response = self.client.post(edit_url, payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jumlah foto barang atau kain maksimal 3")

    def test_form_keeps_batik_preferences_visible_after_validation_error(self):
        self.client.force_login(self.user)
        data = {
            **self.form_data,
            "wants_batik_accent": "on",
            "batik_motif": "Parang",
            "whatsapp": "nomor-tidak-valid",
        }

        response = self.post_form(reverse("upcycling:request_create"), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_wants_batik_accent" checked')
        self.assertContains(response, "class=\"grid gap-4 sm:grid-cols-2\"")
        self.assertContains(response, "Parang")

    def test_create_rate_limit_returns_429_after_five_posts(self):
        """Test behavior: create rate limit returns 429 after five posts."""
        self.client.force_login(self.user)
        url = reverse("upcycling:request_create")

        for _ in range(5):
            response = self.post_form(url)
            self.assertEqual(response.status_code, 302)

        limited_response = self.post_form(url)

        self.assertEqual(limited_response.status_code, 429)
        self.assertEqual(limited_response["Retry-After"], "60")
        self.assertEqual(UpcyclingRequest.objects.filter(user=self.user).count(), 5)
        self.assertContains(
            limited_response,
            "Batas sementara untuk aksi",
            status_code=429,
        )

    def test_rate_limit_window_resets_after_sixty_seconds(self):
        """Test behavior: rate limit window resets after sixty seconds."""
        now = datetime(2026, 10, 25, 12, 0, tzinfo=datetime_timezone.utc)
        action = UpcyclingRateLimitBucket.Action.CREATE

        with patch("upcycling.security.timezone.now", return_value=now):
            for _ in range(5):
                allowed, retry_after = consume_upcycling_rate_limit(
                    self.user,
                    action,
                    limit=5,
                    window_seconds=60,
                )
                self.assertTrue(allowed)
                self.assertEqual(retry_after, 0)

            allowed, retry_after = consume_upcycling_rate_limit(
                self.user,
                action,
                limit=5,
                window_seconds=60,
            )
            self.assertFalse(allowed)
            self.assertEqual(retry_after, 60)

        with patch(
            "upcycling.security.timezone.now",
            return_value=now + timedelta(seconds=61),
        ):
            allowed, retry_after = consume_upcycling_rate_limit(
                self.user,
                action,
                limit=5,
                window_seconds=60,
            )

        self.assertTrue(allowed)
        self.assertEqual(retry_after, 0)

    def test_update_rate_limit_returns_429_after_ten_posts(self):
        """Test behavior: update rate limit returns 429 after ten posts."""
        upcycling_request = self.make_request(
            self.user,
            fabric_photo=SimpleUploadedFile(
                "existing.png", TINY_PNG, content_type="image/png"
            ),
        )
        self.client.force_login(self.user)
        url = reverse("upcycling:request_update", args=[upcycling_request.pk])

        for _ in range(10):
            response = self.client.post(url, self.form_data)
            self.assertEqual(response.status_code, 302)

        limited_response = self.client.post(url, self.form_data)

        self.assertEqual(limited_response.status_code, 429)
        self.assertEqual(limited_response["Retry-After"], "60")

    def test_legacy_delete_endpoint_never_removes_submitted_requests(self):
        """Test behavior: repeated legacy delete attempts preserve requests."""
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)

        for _ in range(11):
            response = self.client.post(
                reverse("upcycling:request_delete", args=[upcycling_request.pk]),
                follow=True,
            )
            self.assertContains(response, "Permintaan yang sudah diajukan tidak dapat dihapus")
        self.assertTrue(
            UpcyclingRequest.objects.filter(pk=upcycling_request.pk).exists()
        )

    def test_create_ignores_posted_user_and_status(self):
        """Test behavior: create ignores posted user and status."""
        self.client.force_login(self.user)
        data = self.form_data | {
            "user": self.other_user.pk,
            "status": "IN_PROGRESS",
        }

        response = self.post_form(reverse("upcycling:request_create"), data)

        self.assertEqual(response.status_code, 302)
        created_request = UpcyclingRequest.objects.get(user=self.user)
        self.assertEqual(created_request.status, "PENDING_ASSIGNMENT")
        self.assertFalse(
            UpcyclingRequest.objects.filter(user=self.other_user).exists()
        )

    def test_user_cannot_create_more_than_ten_pending_requests(self):
        """Test behavior: user cannot create more than ten pending requests."""
        for _ in range(10):
            self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.post_form(
            reverse("upcycling:request_create"),
            self.form_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            UpcyclingRequest.objects.filter(
                user=self.user,
                status="PENDING_ASSIGNMENT",
            ).count(),
            10,
        )
        self.assertContains(response, "sudah memiliki 10 permintaan")

    def test_create_page_redirects_when_user_has_ten_pending_requests(self):
        """Test behavior: create page redirects when user has ten pending requests."""
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
        """Test behavior: incomplete form renders error summary."""
        self.client.force_login(self.user)
        incomplete_data = self.form_data.copy()
        incomplete_data.pop("fabric")

        response = self.post_form(
            reverse("upcycling:request_create"),
            incomplete_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="form-error-summary"')
        self.assertContains(response, 'href="#pilih-kain"')

    def test_user_can_view_success_page_for_own_request(self):
        """Test behavior: user can view success page for own request."""
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
        """Test behavior: user cannot view another users success page."""
        other_request = self.make_request(self.other_user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_success", args=[other_request.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_user_sees_only_own_requests(self):
        """Test behavior: user sees only own requests."""
        own_request = self.make_request(self.user)
        other_request = self.make_request(self.other_user)
        self.client.force_login(self.user)

        response = self.client.get(reverse("upcycling:request_list"))

        self.assertEqual(list(response.context["requests"]), [own_request])
        self.assertNotIn(other_request, response.context["requests"])

    def test_user_can_filter_requests_by_status_and_category(self):
        """Test behavior: user can filter requests by status and category."""
        self.make_request(self.user, status="PENDING_ASSIGNMENT")
        matching_request = self.make_request(
            self.user,
            status="COMPLETED",
            category="POUCH",
            product="POUCH",
        )
        self.make_request(self.user, status="IN_PROGRESS", category="TAS")
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_list"),
            {"status": "COMPLETED", "category": "POUCH"},
        )

        self.assertEqual(list(response.context["requests"]), [matching_request])
        self.assertEqual(response.context["selected_status"], "COMPLETED")
        self.assertEqual(response.context["selected_category"], "POUCH")

    def test_request_search_matches_product_and_fabric_labels(self):
        """Test behavior: request search matches product and fabric labels."""
        matching_request = self.make_request(
            self.user,
            product="TOTE_BAG",
            fabric="UNKNOWN",
            has_batik_pattern="YES",
        )
        self.make_request(self.user, product="POUCH", fabric="COTTON")
        self.client.force_login(self.user)
        url = reverse("upcycling:request_list")

        product_response = self.client.get(url, {"q": "tote bag"})
        fabric_response = self.client.get(url, {"q": "batik"})

        self.assertEqual(list(product_response.context["requests"]), [matching_request])
        self.assertEqual(list(fabric_response.context["requests"]), [matching_request])

    def test_request_search_matches_notes_and_combines_with_category(self):
        """Test behavior: request search matches notes and combines with category."""
        matching_request = self.make_request(
            self.user,
            category="POUCH",
            product="POUCH",
            notes="Warna biru dan motif pilihan",
        )
        self.make_request(
            self.user,
            category="TAS",
            product="TOTE_BAG",
            notes="Warna biru",
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_list"),
            {"q": "biru", "category": "POUCH"},
        )

        self.assertEqual(list(response.context["requests"]), [matching_request])

    def test_request_list_filters_inclusive_date_range_and_orders_by_quantity(self):
        """Test behavior: request list filters inclusive date range and orders by quantity."""
        earlier_request = self.make_request(self.user, quantity=2)
        later_request = self.make_request(self.user, quantity=5)
        UpcyclingRequest.objects.filter(pk=earlier_request.pk).update(
            created_at=datetime(2026, 5, 10, 12, tzinfo=datetime_timezone.utc)
        )
        UpcyclingRequest.objects.filter(pk=later_request.pk).update(
            created_at=datetime(2026, 5, 11, 12, tzinfo=datetime_timezone.utc)
        )
        self.client.force_login(self.user)

        date_response = self.client.get(
            reverse("upcycling:request_list"),
            {"from": "2026-05-10", "to": "2026-05-10"},
        )
        order_response = self.client.get(
            reverse("upcycling:request_list"),
            {"order": "quantity"},
        )

        self.assertEqual(list(date_response.context["requests"]), [earlier_request])
        self.assertEqual(
            list(order_response.context["requests"]),
            [later_request, earlier_request],
        )

    def test_empty_search_keeps_filter_panel_available(self):
        """Test behavior: empty search keeps filter panel available."""
        self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_list"),
            {"q": "tidak-ada-hasil"},
        )

        self.assertContains(response, 'id="upcycling-extra-filters"')
        self.assertContains(response, 'id="filter-query"')
        self.assertContains(response, "Tidak ada permintaan yang cocok")

    def test_create_records_initial_status_history(self):
        """Test behavior: create records initial status history."""
        self.client.force_login(self.user)

        response = self.post_form(
            reverse("upcycling:request_create"),
            self.form_data,
        )

        self.assertEqual(response.status_code, 302)
        upcycling_request = UpcyclingRequest.objects.get(user=self.user)
        history = UpcyclingStatusHistory.objects.get(request=upcycling_request)
        self.assertEqual(history.from_status, "")
        self.assertEqual(history.to_status, UpcyclingRequest.Status.PENDING_ASSIGNMENT)
        self.assertEqual(history.changed_by, self.user)

    def test_htmx_create_returns_location_header_without_full_redirect(self):
        """Test behavior: htmx create returns location header without full redirect."""
        self.client.force_login(self.user)

        response = self.post_form(
            reverse("upcycling:request_create"),
            self.form_data,
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertIn("HX-Location", response)
        self.assertIn("/submitted/", response["HX-Location"])

    def test_user_can_filter_ongoing_requests(self):
        """Test behavior: user can filter ongoing requests."""
        pending_request = self.make_request(self.user, status="PENDING_ASSIGNMENT")
        processing_request = self.make_request(self.user, status="IN_PROGRESS")
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

    def test_all_status_tab_clears_completed_filter_explicitly(self):
        """Test behavior: all status tab clears completed filter explicitly."""
        pending_request = self.make_request(self.user, status="PENDING_ASSIGNMENT")
        processing_request = self.make_request(self.user, status="IN_PROGRESS")
        completed_request = self.make_request(self.user, status="COMPLETED")
        self.client.force_login(self.user)

        completed_page = self.client.get(
            reverse("upcycling:request_list"),
            {"status": "COMPLETED"},
        )
        self.assertContains(completed_page, "status=")

        all_page = self.client.get(
            reverse("upcycling:request_list"),
            {"status": ""},
        )
        self.assertCountEqual(
            all_page.context["requests"],
            [pending_request, processing_request, completed_request],
        )

    def test_invalid_list_filters_are_ignored(self):
        """Test behavior: invalid list filters are ignored."""
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

    def test_invalid_calendar_dates_are_ignored(self):
        """Test behavior: invalid calendar dates are ignored."""
        request = self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_list"),
            {"from": "2026-02-30", "to": "2026-13-01"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["requests"]), [request])
        self.assertEqual(response.context["selected_from"], "")
        self.assertEqual(response.context["selected_to"], "")

    def test_status_timeline_does_not_expose_history_actor_details(self):
        """Test behavior: simplified timeline does not expose actor usernames."""
        staff_user = get_user_model().objects.create_user(
            username="staff-secret",
            password="staff-password",
        )
        upcycling_request = self.make_request(self.user)
        UpcyclingStatusHistory.objects.create(
            request=upcycling_request,
            from_status=UpcyclingRequest.Status.PENDING_ASSIGNMENT,
            to_status=UpcyclingRequest.Status.IN_PROGRESS,
            changed_by=staff_user,
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )

        self.assertNotContains(response, "staff-secret")

    def test_status_tabs_include_current_filters_and_share_sync_target(self):
        """Test behavior: status tabs include current filters and share sync target."""
        self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_list"),
            {"q": "Denim", "category": "TAS", "from": "2026-01-01"},
        )

        self.assertContains(response, 'hx-sync="#request-results:replace"')
        self.assertContains(response, 'data-status-filter="ONGOING"')

    def test_user_cannot_open_another_users_request(self):
        """Test behavior: user cannot open another users request."""
        other_request = self.make_request(self.other_user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_detail", args=[other_request.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_detail_timeline_matches_each_request_status(self):
        """Test behavior: detail timeline matches each request status."""
        self.client.force_login(self.user)
        expected_states = {
            "PENDING_ASSIGNMENT": ["done", "current"] + ["upcoming"] * 8,
            "AWAITING_DELIVERY_DETAILS": ["done"] * 6 + ["current", "upcoming", "upcoming", "upcoming"],
            "IN_PROGRESS": ["done"] * 7 + ["current", "upcoming", "upcoming"],
            "COMPLETED": ["done"] * 10,
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

    def test_detail_timeline_keeps_fabric_deadline_without_status_description(self):
        """Test behavior: the fabric deadline remains visible without repeated status copy."""
        deadline = datetime(2026, 11, 5, 12, 0, tzinfo=datetime_timezone.utc)
        upcycling_request = self.make_request(
            self.user,
            status=UpcyclingRequest.Status.AWAITING_FABRIC,
            fabric_deadline=deadline,
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )

        current_step = next(
            step for step in response.context["timeline_steps"]
            if step["state"] == "current"
        )
        self.assertNotIn("description", current_step)
        self.assertContains(response, "Menunggu kain diserahkan")
        self.assertContains(response, "05 Nov 2026")
        self.assertNotContains(response, "Serahkan kain sesuai rencana sebelum tenggat")

    def test_user_submits_fabric_handoff_details_after_review_approval(self):
        """Test behavior: approved requests collect handoff logistics from the owner."""
        upcycling_request = self.make_request(
            self.user,
            status=UpcyclingRequest.Status.AWAITING_FABRIC,
            fabric_deadline=datetime(2026, 11, 5, 12, tzinfo=datetime_timezone.utc),
        )
        self.client.force_login(self.user)

        detail_response = self.client.get(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )
        self.assertIsNotNone(detail_response.context["fabric_handoff_form"])
        self.assertContains(detail_response, "Cara menyerahkan kain")
        self.assertContains(detail_response, "Catatan penyerahan (opsional)")
        self.assertContains(detail_response, "admin akan mengoordinasikan lokasi drop-off")
        self.assertEqual(
            detail_response.context["fabric_handoff_form"][
                "fabric_delivery_method"
            ].value(),
            "",
        )

        response = self.client.post(
            reverse("upcycling:submit_fabric_handoff", args=[upcycling_request.pk]),
            {
                "fabric_delivery_method": UpcyclingRequest.FabricDeliveryMethod.SELF_SHIP,
                "fabric_delivery_location": "Jl. Melati 10, Depok",
            },
            follow=True,
        )

        upcycling_request.refresh_from_db()
        self.assertEqual(
            upcycling_request.fabric_delivery_method,
            UpcyclingRequest.FabricDeliveryMethod.SELF_SHIP,
        )
        self.assertEqual(
            upcycling_request.fabric_delivery_location,
            "Jl. Melati 10, Depok",
        )
        self.assertContains(response, "Rencana penyerahan kain berhasil disimpan.")

    def test_user_can_save_handoff_method_before_dropoff_module_is_ready(self):
        """Drop-off handoff can be recorded while admin coordinates location manually."""
        upcycling_request = self.make_request(
            self.user,
            status=UpcyclingRequest.Status.AWAITING_FABRIC,
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("upcycling:submit_fabric_handoff", args=[upcycling_request.pk]),
            {"fabric_delivery_method": UpcyclingRequest.FabricDeliveryMethod.DROP_OFF},
            follow=True,
        )

        upcycling_request.refresh_from_db()
        self.assertEqual(
            upcycling_request.fabric_delivery_method,
            UpcyclingRequest.FabricDeliveryMethod.DROP_OFF,
        )
        self.assertEqual(upcycling_request.fabric_delivery_location, "")
        self.assertContains(response, "Rencana penyerahan kain berhasil disimpan.")

    def test_request_detail_shows_optional_fabric_composition(self):
        upcycling_request = self.make_request(
            self.user,
            fabric_composition="Katun 95%, elastane 5%",
            current_item_form="TOP",
            has_batik_pattern="YES",
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )

        self.assertContains(response, "Komposisi bahan")
        self.assertContains(response, "Katun 95%, elastane 5%")
        self.assertContains(response, "Kaos / Kemeja")
        self.assertContains(response, "Ya, bermotif batik")

    def test_detail_timeline_shows_when_completed_steps_changed(self):
        """Test behavior: completed timeline steps show their status dates."""
        upcycling_request = self.make_request(
            self.user, status=UpcyclingRequest.Status.PENDING_REVIEW
        )
        changed_at = datetime(2026, 10, 20, 8, 30, tzinfo=datetime_timezone.utc)
        UpcyclingStatusHistory.objects.create(
            request=upcycling_request,
            from_status="",
            to_status=UpcyclingRequest.Status.PENDING_ASSIGNMENT,
        )
        UpcyclingStatusHistory.objects.filter(request=upcycling_request).update(
            changed_at=changed_at
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )

        self.assertEqual(response.context["timeline_steps"][1]["created_at"], changed_at)

    def test_detail_formats_submission_date_in_jakarta_timezone(self):
        """Test behavior: detail formats submission date in jakarta timezone."""
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
        """Test behavior: user can update own pending request and sees toast."""
        upcycling_request = self.make_request(
            self.user,
            fabric_photo=SimpleUploadedFile(
                "existing.png", TINY_PNG, content_type="image/png"
            ),
        )
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
        """Test behavior: update does not accept posted user or status."""
        upcycling_request = self.make_request(
            self.user,
            fabric_photo=SimpleUploadedFile(
                "existing.png", TINY_PNG, content_type="image/png"
            ),
        )
        self.client.force_login(self.user)
        data = self.form_data | {
            "user": self.other_user.pk,
            "status": "IN_PROGRESS",
        }

        response = self.client.post(
            reverse("upcycling:request_update", args=[upcycling_request.pk]),
            data,
        )

        self.assertEqual(response.status_code, 302)
        upcycling_request.refresh_from_db()
        self.assertEqual(upcycling_request.user, self.user)
        self.assertEqual(upcycling_request.status, "PENDING_ASSIGNMENT")

    def test_user_can_open_edit_form_for_own_pending_request(self):
        """Test behavior: user can open edit form for own pending request."""
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_update", args=[upcycling_request.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_update"])
        self.assertEqual(response.context["form"].instance, upcycling_request)

    def test_user_cannot_update_request_after_review_begins(self):
        """Test behavior: user cannot update request after review begins."""
        upcycling_request = self.make_request(self.user, status="IN_PROGRESS")
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
        """Test behavior: user cannot update another users request."""
        other_request = self.make_request(self.other_user)
        self.client.force_login(self.user)

        response = self.post_form(
            reverse("upcycling:request_update", args=[other_request.pk]),
            self.form_data,
        )

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_delete_own_submitted_request(self):
        """Test behavior: deleting a submitted request leaves its record intact."""
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("upcycling:request_delete", args=[upcycling_request.pk]),
            follow=True,
        )

        self.assertTrue(
            UpcyclingRequest.objects.filter(pk=upcycling_request.pk).exists()
        )
        self.assertContains(response, "Permintaan yang sudah diajukan tidak dapat dihapus")

    def test_submitted_request_uses_cancellation_instead_of_deletion(self):
        """Test behavior: submitted requests remain auditable and can be cancelled."""
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)

        detail_response = self.client.get(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )
        delete_response = self.client.post(
            reverse("upcycling:request_delete", args=[upcycling_request.pk]),
            follow=True,
        )

        self.assertContains(detail_response, "Batalkan permintaan")
        self.assertNotContains(detail_response, "Hapus permintaan")
        self.assertTrue(
            UpcyclingRequest.objects.filter(pk=upcycling_request.pk).exists()
        )
        self.assertContains(delete_response, "Permintaan yang sudah diajukan tidak dapat dihapus")
        self.assertContains(delete_response, "Batalkan permintaan")

    def test_user_can_reject_quote_and_start_fabric_return(self):
        """Test behavior: quote rejection is explicit and schedules fabric return."""
        upcycling_request = self.make_request(
            self.user,
            status=UpcyclingRequest.Status.AWAITING_APPROVAL,
            quoted_price=25000,
            fabric_received_at=datetime.now(datetime_timezone.utc),
        )
        self.client.force_login(self.user)

        detail_response = self.client.get(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )
        self.assertContains(detail_response, "Tolak penawaran")
        self.assertNotContains(detail_response, "Batalkan permintaan")

        response = self.client.post(
            reverse("upcycling:cancel_request", args=[upcycling_request.pk]),
            {"action": "reject_quote"},
            follow=True,
        )

        upcycling_request.refresh_from_db()
        self.assertEqual(upcycling_request.status, UpcyclingRequest.Status.CANCELLED)
        self.assertEqual(
            upcycling_request.cancellation_reason,
            "Penawaran harga ditolak oleh user.",
        )
        self.assertEqual(
            upcycling_request.return_status,
            UpcyclingRequest.ReturnStatus.PENDING_RETURN,
        )
        self.assertContains(response, "Penawaran ditolak. Kain akan dikembalikan.")

    def test_legacy_delete_confirmation_redirects_to_request_detail(self):
        """Test behavior: old delete links explain cancellation instead."""
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_delete", args=[upcycling_request.pk])
        )

        self.assertRedirects(
            response,
            reverse("upcycling:request_detail", args=[upcycling_request.pk]),
        )

    def test_user_cannot_delete_request_after_review_begins(self):
        """Test behavior: user cannot delete request after review begins."""
        upcycling_request = self.make_request(self.user, status="IN_PROGRESS")
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
            "Permintaan yang sudah diajukan tidak dapat dihapus",
        )

    def test_user_cannot_delete_another_users_request(self):
        """Test behavior: user cannot delete another users request."""
        other_request = self.make_request(self.other_user)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("upcycling:request_delete", args=[other_request.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_htmx_legacy_delete_redirects_to_detail_without_removing_request(self):
        """Test behavior: legacy HTMX delete keeps the request and returns to detail."""
        upcycling_request = self.make_request(self.user)
        remaining_request = self.make_request(self.user, product="SLING_BAG")
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("upcycling:request_delete", args=[upcycling_request.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertTrue(
            UpcyclingRequest.objects.filter(pk=upcycling_request.pk).exists()
        )
        self.assertIn(
            reverse("upcycling:request_detail", args=[upcycling_request.pk]),
            response["HX-Location"],
        )
        remaining_detail = self.client.get(
            reverse("upcycling:request_detail", args=[remaining_request.pk])
        )
        self.assertEqual(remaining_detail.status_code, 200)

    def test_submitted_request_detail_offers_cancel_but_not_delete(self):
        """Test behavior: submitted request detail exposes cancellation only."""
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)

        delete_url = reverse("upcycling:request_delete", args=[upcycling_request.pk])

        detail_response = self.client.get(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )
        self.assertNotContains(detail_response, delete_url)
        self.assertNotContains(detail_response, "Hapus permintaan")
        self.assertContains(detail_response, 'id="request-actions"')
        self.assertContains(detail_response, "sm:flex-row")
        self.assertContains(detail_response, "w-full sm:w-auto", count=3)
        self.assertContains(detail_response, "Edit permintaan")
        self.assertContains(detail_response, "Batalkan permintaan")
        rendered = detail_response.content.decode()
        actions_start = rendered.index('id="request-actions"')
        actions_end = rendered.index("</div>", actions_start)
        actions_markup = rendered[actions_start:actions_end]
        self.assertIn("Edit permintaan", actions_markup)
        self.assertIn("Batalkan permintaan", actions_markup)
        self.assertNotIn("Hubungi Tim via WhatsApp", actions_markup)
        contact_actions_start = rendered.index('id="contact-team-actions"')
        self.assertLess(contact_actions_start, actions_start)
        contact_actions_end = rendered.index("</div>", contact_actions_start)
        contact_actions_markup = rendered[contact_actions_start:contact_actions_end]
        self.assertIn("sm:justify-between", contact_actions_markup)
        self.assertIn("Permintaan bisa diedit selama masih menunggu tinjauan.", contact_actions_markup)
        self.assertIn("Hubungi Tim via WhatsApp", contact_actions_markup)
        self.assertContains(
            detail_response,
            "Permintaan bisa diedit selama masih menunggu tinjauan.",
        )
        self.assertNotContains(detail_response, "bisa diedit atau dihapus")
        self.assertContains(detail_response, "hover:bg-[var(--danger)]")

        confirmation_response = self.client.get(delete_url)
        self.assertRedirects(
            confirmation_response,
            reverse("upcycling:request_detail", args=[upcycling_request.pk]),
        )

    def test_detail_explains_cancel_preserves_request_history(self):
        """Test behavior: cancellation wording clarifies the request remains recorded."""
        upcycling_request = self.make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )

        self.assertContains(
            response,
            "Jika dibatalkan, permintaan tetap tersimpan di riwayat.",
        )
        rendered = response.content.decode()
        self.assertLess(
            rendered.index("Permintaan bisa diedit selama masih menunggu tinjauan."),
            rendered.index("Batalkan permintaan"),
        )

    def test_request_form_embeds_product_options_for_each_category(self):
        """Test behavior: request form embeds product options for each category."""
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
                {"value": "BACKPACK", "label": "Backpack"},
                {"value": "SHOULDER_BAG", "label": "Shoulder Bag"},
                {"value": "LAINNYA", "label": "Lainnya"},
            ],
        )
        self.assertContains(response, 'id="product-options-data"')
