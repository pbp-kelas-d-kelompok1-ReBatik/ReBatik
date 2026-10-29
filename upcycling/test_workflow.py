from io import BytesIO
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from rewards.models import PointTransaction
from .admin import UpcyclingRequestAdminForm
from .models import ArtisanProfile, ProductType, UpcyclingRequest
from .forms import UpcyclingRequestForm, get_product_options_by_category


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
        artisan_group, _ = Group.objects.get_or_create(name="Artisan")
        self.artisan_user.groups.add(artisan_group)
        self.product_type, _ = ProductType.objects.get_or_create(
            code="TOTE_BAG", defaults={"name": "Tote Bag"}
        )
        self.artisan = ArtisanProfile.objects.create(user=self.artisan_user, max_active_requests=3)
        self.artisan.specializations.add(self.product_type)

    def test_request_form_requires_private_fabric_photo_and_no_donation_option(self):
        data = {
            "fabric": "DENIM",
            "fabric_condition": "GOOD",
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

        self.assertContains(response, "Jenis Kain atau Barang yang Akan Diolah")
        self.assertContains(response, "Pilih kategori yang paling mendekati.")
        self.assertContains(response, "Pilih Produk")
        self.assertContains(response, 'class="grid gap-4 grid-cols-2 lg:grid-cols-3"')
        self.assertContains(response, 'id="id_wants_batik_accent"')
        self.assertContains(response, "Tambahkan kain bermotif batik dari ReBatik")

    def test_product_catalog_includes_practical_upcycling_products(self):
        options = get_product_options_by_category()
        product_codes = {
            product["value"]
            for category_products in options.values()
            for product in category_products
        }
        expected_products = {
            "SCRUNCHIE",
            "BUCKET_HAT",
            "LAPTOP_SLEEVE",
            "SARUNG_BANTAL",
            "BACKPACK",
            "SHOULDER_BAG",
            "PENCIL_CASE",
            "MAKEUP_POUCH",
            "OUTER",
            "ROK",
            "HEADBAND",
            "KEYCHAIN",
        }

        self.assertTrue(expected_products.issubset(product_codes))
        self.assertIn("RUMAH_TANGGA", options)
        expected_by_category = {
            "TAS": {"BACKPACK", "SHOULDER_BAG"},
            "POUCH": {"PENCIL_CASE", "MAKEUP_POUCH"},
            "PAKAIAN": {"OUTER", "ROK"},
            "AKSESORIS": {"HEADBAND", "KEYCHAIN"},
        }
        for category, expected in expected_by_category.items():
            self.assertTrue(
                expected.issubset(
                    {product["value"] for product in options[category]}
                )
            )
        self.assertTrue(
            expected_products.issubset(
                set(ProductType.objects.values_list("code", flat=True))
            )
        )

    def test_submission_starts_unassigned_and_records_history(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("upcycling:request_create"),
            data={
                "fabric": "DENIM",
                "fabric_condition": "GOOD",
                "fabric_dimensions": "1 celana jeans",
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

    def test_admin_candidate_filter_excludes_requesting_artisan(self):
        request_obj = make_request(self.artisan_user)

        candidate_ids = set(
            UpcyclingRequestAdminForm(instance=request_obj)
            .fields["artisan"]
            .queryset.values_list("pk", flat=True)
        )

        self.assertNotIn(self.artisan.pk, candidate_ids)

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

    def test_assigned_artisan_detail_shows_user_fabric_handoff_plan(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.AWAITING_FABRIC,
            fabric_composition="Katun 95%, elastane 5%",
            wants_batik_accent=True,
            batik_motif="Mega Mendung",
            motif_placement="Bagian depan tote bag",
            fabric_delivery_method=UpcyclingRequest.FabricDeliveryMethod.SELF_SHIP,
            fabric_delivery_location="Jl. Melati 10, Depok",
        )
        self.client.force_login(self.artisan_user)

        response = self.client.get(reverse("upcycling:request_detail", args=[request_obj.pk]))

        self.assertContains(response, "bg-[var(--upcycling-panel)]")
        self.assertContains(response, "bg-[var(--upcycling-surface)]")
        self.assertContains(response, "cloud-left.webp")
        self.assertContains(response, "Penyerahan kain")
        self.assertContains(response, "Katun 95%, elastane 5%")
        self.assertContains(response, "Mega Mendung")
        self.assertContains(response, "Bagian depan tote bag")
        self.assertContains(response, "Kirim kain sendiri")
        self.assertContains(response, "Jl. Melati 10, Depok")

    def test_artisan_dashboard_keeps_completed_assignments_in_history(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.COMPLETED,
        )
        self.client.force_login(self.artisan_user)

        response = self.client.get(reverse("upcycling:artisan_dashboard"))

        self.assertContains(response, request_obj.reference_code)
        self.assertContains(response, "Selesai")
        self.assertNotContains(response, "Tandai siap diserahkan")

    def test_each_assigned_request_has_a_detail_link(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.PENDING_REVIEW,
        )
        self.client.force_login(self.artisan_user)

        response = self.client.get(reverse("upcycling:artisan_dashboard"))

        self.assertContains(response, "Lihat Detail →")
        self.assertContains(response, reverse("upcycling:request_detail", args=[request_obj.pk]))

    def test_artisan_dashboard_request_card_is_compact(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.INSPECTION,
            notes="Catatan hanya ditampilkan di detail.",
            wants_batik_accent=True,
            batik_motif="Mega Mendung",
        )
        self.client.force_login(self.artisan_user)

        response = self.client.get(reverse("upcycling:artisan_dashboard"))

        self.assertContains(response, request_obj.get_product_name())
        self.assertContains(response, request_obj.get_fabric_display())
        self.assertContains(response, request_obj.reference_code)
        self.assertContains(response, "Lihat Detail →")
        self.assertNotContains(response, "Catatan hanya ditampilkan di detail.")
        self.assertNotContains(response, "quoted_price")

    def test_artisan_detail_contains_status_specific_review_actions(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.PENDING_REVIEW,
        )
        self.client.force_login(self.artisan_user)

        response = self.client.get(reverse("upcycling:request_detail", args=[request_obj.pk]))

        self.assertContains(response, "Tindakan Artisan")
        self.assertContains(response, "Terima review")
        self.assertContains(response, "Tolak Permintaan")

    def test_assigned_artisan_can_view_detail_without_member_actions(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.AWAITING_APPROVAL,
            quoted_price="75555",
        )
        self.client.force_login(self.artisan_user)

        response = self.client.get(reverse("upcycling:request_detail", args=[request_obj.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard Artisan")
        self.assertContains(response, "Rp75555")
        self.assertNotContains(response, "Setujui harga")
        self.assertNotContains(response, "Tolak penawaran")
        self.assertNotContains(response, "Batalkan permintaan")

    def test_artisan_cannot_view_request_assigned_to_another_artisan(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.PENDING_REVIEW,
        )
        other_artisan_user = User.objects.create_user(username="other-artisan", password="pw")
        artisan_group, _ = Group.objects.get_or_create(name="Artisan")
        other_artisan_user.groups.add(artisan_group)
        ArtisanProfile.objects.create(user=other_artisan_user)
        self.client.force_login(other_artisan_user)

        response = self.client.get(reverse("upcycling:request_detail", args=[request_obj.pk]))

        self.assertEqual(response.status_code, 404)

    def test_empty_artisan_dashboard_uses_member_request_empty_state_style(self):
        self.client.force_login(self.artisan_user)

        response = self.client.get(reverse("upcycling:artisan_dashboard"))

        self.assertContains(response, "crying.webp")
        self.assertContains(response, "Belum ada permintaan")
        self.assertContains(response, "Request yang ditugaskan oleh admin akan muncul di sini.")

    def test_artisan_dashboard_has_return_link_to_member_request_list(self):
        self.client.force_login(self.artisan_user)

        response = self.client.get(reverse("upcycling:artisan_dashboard"))

        self.assertContains(response, "Kembali ke Permintaan Saya")
        self.assertContains(response, 'href="/upcycling/"')

    def test_non_artisan_cannot_open_artisan_dashboard(self):
        ArtisanProfile.objects.create(user=self.user)
        self.client.force_login(self.user)

        response = self.client.get(reverse("upcycling:artisan_dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_artisan_group_without_upcycling_profile_cannot_open_dashboard(self):
        artisan_group, _ = Group.objects.get_or_create(name="Artisan")
        self.user.groups.add(artisan_group)
        self.client.force_login(self.user)

        response = self.client.get(reverse("upcycling:artisan_dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_hamburger_nav_shows_upcycling_and_dashboard_links_for_artisans(self):
        self.client.force_login(self.artisan_user)

        response = self.client.get(reverse("upcycling:request_list"))

        self.assertContains(response, 'href="/upcycling/">Upcycling Request</a>')
        self.assertContains(response, 'href="/upcycling/artisan/">Dashboard Artisan</a>')
        self.assertContains(response, "Buka dashboard artisan")
        self.assertContains(response, "primary-action-button mt-5 min-h-11 px-5 py-2 text-sm")

    def test_hamburger_nav_hides_artisan_dashboard_from_members(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("upcycling:request_list"))

        self.assertContains(response, 'href="/upcycling/">Upcycling Request</a>')
        self.assertNotContains(response, "Dashboard Artisan")

    def test_artisan_rejection_action_has_clear_label_and_danger_gradient(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.PENDING_REVIEW,
        )
        self.client.force_login(self.artisan_user)

        response = self.client.get(reverse("upcycling:request_detail", args=[request_obj.pk]))

        self.assertContains(response, "Tolak Permintaan")
        self.assertContains(response, "upcycling-danger-action-button")

    def test_artisan_can_quote_any_positive_whole_rupiah_amount(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.INSPECTION,
            fabric_received_at=timezone.now(),
            fabric_received_by=self.artisan_user,
        )
        self.client.force_login(self.artisan_user)

        response = self.client.get(reverse("upcycling:request_detail", args=[request_obj.pk]))

        self.assertContains(response, 'name="quoted_price" type="number" min="1" max="99999999" step="1"')
        response = self.client.post(
            reverse("upcycling:artisan_update_request", args=[request_obj.pk]),
            {"action": "inspection_pass", "quoted_price": "75555", "notes": "Layak."},
        )

        request_obj.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.AWAITING_APPROVAL)
        self.assertEqual(str(request_obj.quoted_price), "75555.00")

    def test_artisan_cannot_quote_fractional_or_overflowing_rupiah_amount(self):
        self.client.force_login(self.artisan_user)
        for price in ("75555.50", "100000000"):
            with self.subTest(price=price):
                request_obj = make_request(
                    self.user,
                    artisan=self.artisan,
                    status=UpcyclingRequest.Status.INSPECTION,
                    fabric_received_at=timezone.now(),
                    fabric_received_by=self.artisan_user,
                )

                self.client.post(
                    reverse("upcycling:artisan_update_request", args=[request_obj.pk]),
                    {"action": "inspection_pass", "quoted_price": price, "notes": "Layak."},
                )

                request_obj.refresh_from_db()
                self.assertEqual(request_obj.status, UpcyclingRequest.Status.INSPECTION)
                self.assertIsNone(request_obj.quoted_price)

    def test_non_artisan_cannot_submit_artisan_actions(self):
        ArtisanProfile.objects.create(user=self.user)
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.PENDING_REVIEW,
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("upcycling:artisan_update_request", args=[request_obj.pk]),
            {"action": "review_accept", "notes": "Bisa dibuat."},
        )

        self.assertEqual(response.status_code, 403)
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.PENDING_REVIEW)

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
