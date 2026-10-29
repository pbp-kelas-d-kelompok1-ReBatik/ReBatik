from io import BytesIO
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from rewards.models import PointTransaction
from .admin import UpcyclingRequestAdminForm
from .models import ArtisanProfile, ProductType, UpcyclingRequest
from .forms import UpcyclingRequestForm


User = get_user_model()


def make_png():
    image = Image.new("RGB", (2, 2), color="blue")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return SimpleUploadedFile("fabric.png", buffer.getvalue(), content_type="image/png")


def make_request(user, *, artisan=None, status=UpcyclingRequest.Status.PENDING_ASSIGNMENT, **kwargs):
    return UpcyclingRequest.objects.create(
        user=user,
        artisan=artisan,
        fabric="DENIM",
        category="TAS",
        product="TOTE_BAG",
        delivery_method="DROP_OFF",
        address="Depok",
        whatsapp="+6281234567890",
        status=status,
        **kwargs,
    )


class UpcyclingWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="pw")
        self.artisan_user = User.objects.create_user(username="artisan", password="pw")
        self.product_type, _ = ProductType.objects.get_or_create(
            code="TOTE_BAG", defaults={"name": "Tote Bag"}
        )
        self.artisan = ArtisanProfile.objects.create(user=self.artisan_user, max_active_requests=3)
        self.artisan.specializations.add(self.product_type)

    def test_request_form_requires_private_fabric_photo_and_no_donation_option(self):
        data = {
            "fabric": "DENIM",
            "fabric_condition": "GOOD",
            "fabric_delivery_method": "DROP_OFF",
            "category": "TAS",
            "product": "TOTE_BAG",
            "quantity": "1",
            "notes": "",
            "delivery_method": "DROP_OFF",
            "address": "Depok",
            "whatsapp": "081234567890",
        }
        self.assertNotIn("NEW_DONATION", dict(UpcyclingRequest.FABRIC_CHOICES))
        self.assertFalse(UpcyclingRequestForm(data=data).is_valid())
        form = UpcyclingRequestForm(data=data, files={"fabric_photo": make_png()})
        self.assertTrue(form.is_valid(), form.errors)

    def test_other_fabric_requires_a_description(self):
        data = {
            "fabric": "OTHER",
            "fabric_condition": "GOOD",
            "fabric_delivery_method": "DROP_OFF",
            "category": "TAS",
            "product": "TOTE_BAG",
            "quantity": "1",
            "notes": "",
            "delivery_method": "DROP_OFF",
            "address": "Depok",
            "whatsapp": "081234567890",
        }
        form = UpcyclingRequestForm(data=data, files={"fabric_photo": make_png()})
        self.assertFalse(form.is_valid())
        self.assertIn("fabric_other_description", form.errors)

        data["fabric_other_description"] = "Kain kanvas"
        form = UpcyclingRequestForm(data=data, files={"fabric_photo": make_png()})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["fabric_other_description"], "Kain kanvas")

        data.update(fabric="DENIM", fabric_other_description="Keterangan lama")
        form = UpcyclingRequestForm(data=data, files={"fabric_photo": make_png()})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["fabric_other_description"], "")

    def test_form_distinguishes_user_fabric_from_output_product(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("upcycling:request_create"))

        self.assertContains(response, "Jenis Kain yang Akan Diolah")
        self.assertContains(response, "Pilih produk yang ingin dibuat pada bagian berikutnya.")
        self.assertContains(response, "Pilih Produk")

    def test_submission_starts_unassigned_and_records_history(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("upcycling:request_create"),
            data={
                "fabric": "DENIM",
                "fabric_condition": "GOOD",
                "fabric_dimensions": "1 celana jeans",
                "fabric_delivery_method": "DROP_OFF",
                "fabric_delivery_location": "Depok",
                "category": "TAS",
                "product": "TOTE_BAG",
                "quantity": "1",
                "notes": "",
                "delivery_method": "DROP_OFF",
                "address": "Depok",
                "whatsapp": "081234567890",
                "fabric_photo": make_png(),
            },
        )
        self.assertEqual(response.status_code, 302)
        request_obj = UpcyclingRequest.objects.get(user=self.user)
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.PENDING_ASSIGNMENT)
        self.assertIsNone(request_obj.artisan_id)
        self.assertEqual(request_obj.status_history.count(), 1)

    def test_admin_candidate_filter_matches_skill_availability_and_capacity(self):
        request_obj = make_request(self.user)
        full_user = User.objects.create_user(username="full-artisan")
        full = ArtisanProfile.objects.create(user=full_user, max_active_requests=1)
        full.specializations.add(self.product_type)
        make_request(self.user, artisan=full, status=UpcyclingRequest.Status.PENDING_REVIEW)

        other_product, _ = ProductType.objects.get_or_create(
            code="POUCH", defaults={"name": "Pouch"}
        )
        wrong_skill_user = User.objects.create_user(username="wrong-skill")
        wrong_skill = ArtisanProfile.objects.create(user=wrong_skill_user)
        wrong_skill.specializations.add(other_product)
        unavailable_user = User.objects.create_user(username="unavailable")
        unavailable = ArtisanProfile.objects.create(user=unavailable_user, is_available=False)
        unavailable.specializations.add(self.product_type)

        candidate_ids = set(
            UpcyclingRequestAdminForm(instance=request_obj)
            .fields["artisan"]
            .queryset.values_list("pk", flat=True)
        )
        self.assertIn(self.artisan.pk, candidate_ids)
        self.assertNotIn(full.pk, candidate_ids)
        self.assertNotIn(wrong_skill.pk, candidate_ids)
        self.assertNotIn(unavailable.pk, candidate_ids)

    def test_artisan_review_receipt_and_inspection_set_expected_statuses(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.PENDING_REVIEW,
        )
        self.client.force_login(self.artisan_user)
        self.client.post(
            reverse("upcycling:artisan_update_request", args=[request_obj.pk]),
            {"action": "review_accept", "notes": "Bisa dibuat."},
        )
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.AWAITING_FABRIC)
        self.assertAlmostEqual(
            (request_obj.fabric_deadline - request_obj.review_approved_at).total_seconds(),
            7 * 24 * 60 * 60,
            delta=2,
        )

        self.client.post(
            reverse("upcycling:artisan_update_request", args=[request_obj.pk]),
            {"action": "receive_fabric", "notes": "Kain diterima."},
        )
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.INSPECTION)
        self.assertEqual(request_obj.fabric_received_by, self.artisan_user)

        self.client.post(
            reverse("upcycling:artisan_update_request", args=[request_obj.pk]),
            {"action": "inspection_pass", "quoted_price": "75000", "notes": "Kain layak."},
        )
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.AWAITING_APPROVAL)
        self.assertEqual(str(request_obj.quoted_price), "75000.00")

    def test_rejection_stages_match_workflow_and_set_return_obligation(self):
        self.client.force_login(self.artisan_user)
        preliminary = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.PENDING_REVIEW,
        )
        self.client.post(
            reverse("upcycling:artisan_update_request", args=[preliminary.pk]),
            {"action": "review_reject", "notes": "Tidak sesuai kemampuan artisan."},
        )
        preliminary.refresh_from_db()
        self.assertEqual(preliminary.rejection_stage, "PRELIMINARY_REVIEW")
        self.assertEqual(
            preliminary.return_status,
            UpcyclingRequest.ReturnStatus.NOT_REQUIRED,
        )

        inspection = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.INSPECTION,
            fabric_received_at=timezone.now(),
            fabric_received_by=self.artisan_user,
        )
        self.client.post(
            reverse("upcycling:artisan_update_request", args=[inspection.pk]),
            {"action": "inspection_reject", "notes": "Kain terlalu rusak."},
        )
        inspection.refresh_from_db()
        self.assertEqual(inspection.rejection_stage, "PHYSICAL_INSPECTION")
        self.assertEqual(
            inspection.return_status,
            UpcyclingRequest.ReturnStatus.PENDING_RETURN,
        )

    def test_approving_quote_starts_production_without_payment_step(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.AWAITING_APPROVAL,
            quoted_price="75000",
        )
        self.client.force_login(self.user)
        self.client.post(reverse("upcycling:approve_quote", args=[request_obj.pk]))
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.IN_PROGRESS)
        self.assertIsNotNone(request_obj.approved_at)
        self.assertNotIn("AWAITING_PAYMENT", dict(UpcyclingRequest.Status.choices))
        self.assertNotIn(
            "payment_status",
            {field.name for field in UpcyclingRequest._meta.get_fields()},
        )

    def test_user_completion_awards_points_only_once(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.READY,
            quoted_price="75000",
            approved_at=timezone.now(),
        )
        self.client.force_login(self.user)
        url = reverse("upcycling:confirm_completion", args=[request_obj.pk])
        self.client.post(url)
        self.client.post(url)
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.COMPLETED)
        self.assertEqual(
            PointTransaction.objects.filter(
                upcycling_request=request_obj,
                kind=PointTransaction.Kind.UPCYCLING_COMPLETED,
            ).count(),
            1,
        )
