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
from .models import AdditionalFabricPhoto, ArtisanProfile, ProductType, UpcyclingRequest
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
            "current_item_form": "PANTS",
            "has_batik_pattern": "NO",
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
        form = UpcyclingRequestForm(data=data, files={"fabric_photos": [make_png()]})
        self.assertTrue(form.is_valid(), form.errors)

    def test_other_fabric_requires_a_description(self):
        data = {
            "fabric": "OTHER",
            "current_item_form": "PANTS",
            "has_batik_pattern": "UNSURE",
            "fabric_condition": "GOOD",
            "category": "TAS",
            "product": "TOTE_BAG",
            "quantity": "1",
            "notes": "",
            "delivery_method": "DROP_OFF",
            "address": "Depok",
            "whatsapp": "081234567890",
        }
        form = UpcyclingRequestForm(data=data, files={"fabric_photos": [make_png()]})
        self.assertFalse(form.is_valid())
        self.assertIn("fabric_other_description", form.errors)

        data["fabric_other_description"] = "Kain kanvas"
        form = UpcyclingRequestForm(data=data, files={"fabric_photos": [make_png()]})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["fabric_other_description"], "Kain kanvas")

        data.update(fabric="DENIM", fabric_other_description="Keterangan lama")
        form = UpcyclingRequestForm(data=data, files={"fabric_photos": [make_png()]})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["fabric_other_description"], "")

    def test_form_distinguishes_user_fabric_from_output_product(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("upcycling:request_create"))

        self.assertContains(response, "Jenis bahan utama yang akan diolah")
        self.assertContains(response, "Barang &amp; Bahan")
        self.assertContains(response, "Apakah barang atau kain Anda sudah memiliki motif batik?")
        self.assertContains(response, "Barang atau kain apa yang ingin Anda olah?")
        self.assertContains(response, "Apa jenis bahan utama barang atau kain Anda?")
        self.assertNotContains(response, "Apa jenis bahan utamanya?")
        self.assertContains(response, "Pilih bentuk barang yang Anda miliki saat ini.")
        self.assertContains(response, 'class="text-base leading-relaxed text-[var(--brown-muted)] sm:text-lg"')
        self.assertContains(response, "Celana")
        self.assertContains(response, "Kaos / Kemeja")
        self.assertContains(response, "Kain lembaran / Potongan kain")
        self.assertContains(response, "Pilih kategori dan produk akhir yang ingin dibuat.")
        self.assertContains(response, "Produk &amp; Desain")
        self.assertContains(response, "Detail &amp; Konfirmasi")
        self.assertContains(response, "Pilih produk yang ingin dibuat")
        self.assertContains(response, "Kombinasikan bahan saya dengan kain batik dari ReBatik")
        self.assertNotContains(response, "Catatan desain tambahan")
        self.assertContains(response, "Foto barang atau kain")
        self.assertContains(response, "Bagaimana kondisi barang atau kain Anda?")
        self.assertContains(response, "Berapa banyak barang atau bahan yang ingin diolah?")
        self.assertContains(response, "Contoh: 1 celana jeans ukuran L, 2 kaos, atau kain sekitar 1 × 2 m.")
        self.assertContains(response, "Berapa produk baru yang ingin dibuat?")
        self.assertContains(response, "Di bagian mana Anda ingin kain batik ditambahkan?")
        self.assertContains(response, "Foto contoh hasil yang Anda inginkan (opsional)")
        self.assertContains(response, "Tuliskan preferensi warna, ukuran produk, atau permintaan lain untuk artisan.")
        self.assertNotContains(response, "Komposisi bahan (opsional)")
        self.assertNotContains(response, "id=\"id_fabric_composition\"")
        self.assertNotContains(response, "id=\"id_design_notes\"")
        self.assertContains(response, "Jumlah akhir bergantung pada kecukupan bahan setelah inspeksi artisan.")
        self.assertContains(response, "Ubah barang atau kain bekas milik Anda menjadi karya baru")
        self.assertContains(response, "Celana atau jaket jeans")
        self.assertContains(response, "Kemeja atau kain katun")
        self.assertContains(response, "Misalnya polyester")
        self.assertContains(response, "Gabungan beberapa bahan")
        self.assertContains(response, "Artisan akan memeriksa")
        self.assertContains(response, 'class="grid gap-3 grid-cols-2 md:grid-cols-3"')
        self.assertContains(response, 'class="upcycling-fabric-card-title block"')
        self.assertContains(response, 'class="upcycling-fabric-card-description mt-1 block')
        self.assertNotContains(response, 'class="grid aspect-[2] place-items-center overflow-hidden bg-[var(--upcycling-soft)]"')
        page = response.content.decode()
        self.assertLess(
            page.index("Sebutkan bahan lainnya"),
            page.index("Apakah barang atau kain Anda sudah memiliki motif batik?"),
        )
        self.assertContains(response, 'id="id_wants_batik_accent"')
        self.assertContains(response, "Kombinasikan bahan saya dengan kain batik dari ReBatik")
        self.assertContains(response, "Setelah bahan diperiksa, artisan akan mengirim penawaran harga.")
        self.assertContains(response, "Tim ReBatik akan menginformasikan langkah berikutnya sebelum produksi dimulai.")
        self.assertContains(response, "Bahan pribadi tetap milik Anda dan tidak otomatis menjadi donasi.")
        self.assertNotContains(response, "Produksi dimulai setelah detail tersebut disimpan.")

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
                "current_item_form": "PANTS",
                "has_batik_pattern": "NO",
                "fabric_condition": "GOOD",
                "fabric_dimensions": "1 celana jeans",
                "category": "TAS",
                "product": "TOTE_BAG",
                "quantity": "1",
                "notes": "",
                "delivery_method": "DROP_OFF",
                "address": "Depok",
                "whatsapp": "081234567890",
                "fabric_photos": [make_png()],
            },
        )
        self.assertEqual(response.status_code, 302)
        request_obj = UpcyclingRequest.objects.get(user=self.user)
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.PENDING_ASSIGNMENT)
        self.assertIsNone(request_obj.artisan_id)
        self.assertEqual(request_obj.status_history.count(), 1)

    def test_request_detail_uses_one_timeline_with_stage_descriptions(self):
        request_obj = make_request(self.user)
        self.client.force_login(self.user)

        response = self.client.get(reverse("upcycling:request_detail", args=[request_obj.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Langkah berikutnya")
        self.assertNotContains(response, "Riwayat Status")
        self.assertNotContains(response, "upcycling-status-badge")
        self.assertContains(response, "Admin sedang mencocokkan permintaan dengan keahlian dan kapasitas artisan.")
        self.assertContains(response, "Artisan meninjau model produk dan informasi kain yang Anda kirim.")
        self.assertContains(response, 'data-status-description')

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
            {"action": "inspection_pass", "work_price": "75000", "notes": "Kain layak."},
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

    def test_artisan_dashboard_opens_all_fabric_photos_in_zoom_gallery(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.PENDING_REVIEW,
            fabric_photo=make_png(),
        )
        for _ in range(2):
            AdditionalFabricPhoto.objects.create(
                request=request_obj,
                image=make_png(),
            )
        self.client.force_login(self.artisan_user)

        response = self.client.get(reverse("upcycling:artisan_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.count(b'data-fabric-photo-zoom='), 3)
        self.assertEqual(response.content.count(b'data-photo-zoom-icon'), 3)
        self.assertNotContains(response, "Zoom ⤢")
        self.assertContains(response, 'id="artisan-photo-zoom"')
        self.assertContains(response, 'id="artisan-photo-zoom-previous"')
        self.assertContains(response, 'id="artisan-photo-zoom-next"')
        self.assertContains(response, 'src="/static/js/upcycling-photo-zoom.js"')
        self.assertContains(response, "Foto barang atau kain 1 dari 3")
        self.assertContains(response, "Foto barang atau kain 2 dari 3")
        self.assertContains(response, "Foto barang atau kain 3 dari 3")

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
        self.assertContains(response, "Rp75.555")
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
        self.assertNotContains(response, "Dashboard Admin")

    def test_admin_dashboard_requires_staff_access(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("upcycling:admin_dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_admin_dashboard_empty_statuses_match_member_empty_state_style(self):
        staff = User.objects.create_user(username="queue-empty-admin", is_staff=True)
        self.client.force_login(staff)

        dashboard_url = reverse("upcycling:admin_dashboard")
        for status in (
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
            UpcyclingRequest.Status.PENDING_REVIEW,
            UpcyclingRequest.Status.IN_PROGRESS,
        ):
            with self.subTest(status=status):
                response = self.client.get(dashboard_url, {"status": status})

                self.assertContains(response, "Belum ada permintaan")
                self.assertContains(
                    response,
                    'class="h-40 w-40 object-contain sm:h-72 sm:w-72 lg:h-[26rem] lg:w-[26rem]"',
                )
                self.assertContains(response, "px-5 py-10 text-center sm:gap-6 sm:px-10 sm:py-16")
                self.assertContains(response, "Lihat semua request →")

    def test_admin_dashboard_status_tabs_filter_without_full_page_reload(self):
        assignment_request = make_request(self.user)
        review_request = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.PENDING_REVIEW,
        )
        production_request = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.IN_PROGRESS,
        )
        other_request = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.AWAITING_FABRIC,
        )
        staff = User.objects.create_user(username="admin-status-lists", is_staff=True)
        self.client.force_login(staff)

        dashboard_url = reverse("upcycling:admin_dashboard")
        response = self.client.get(dashboard_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["selected_admin_status"],
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
        )
        self.assertContains(response, 'hx-target="#admin-dashboard-live"')
        self.assertContains(response, 'hx-select="#admin-dashboard-live"')
        self.assertContains(response, 'hx-swap="outerHTML"')
        self.assertContains(response, f'hx-get="{dashboard_url}?status=PENDING_REVIEW"')
        self.assertContains(response, assignment_request.reference_code)
        self.assertNotContains(response, review_request.reference_code)
        self.assertNotContains(response, production_request.reference_code)

        response = self.client.get(
            dashboard_url,
            {"status": UpcyclingRequest.Status.PENDING_REVIEW},
        )
        self.assertEqual(
            list(response.context["status_requests"].values_list("pk", flat=True)),
            [review_request.pk],
        )
        self.assertContains(response, review_request.reference_code)
        self.assertContains(response, self.artisan_user.username)
        self.assertContains(response, "Lihat Detail")
        self.assertNotContains(response, assignment_request.reference_code)
        self.assertNotContains(response, production_request.reference_code)

        response = self.client.get(
            dashboard_url,
            {"status": UpcyclingRequest.Status.IN_PROGRESS},
        )
        self.assertEqual(
            list(response.context["status_requests"].values_list("pk", flat=True)),
            [production_request.pk],
        )
        self.assertContains(response, production_request.reference_code)
        self.assertContains(response, self.artisan_user.username)
        self.assertContains(response, "Lihat Detail")
        self.assertNotContains(response, assignment_request.reference_code)
        self.assertNotContains(response, review_request.reference_code)

        response = self.client.get(
            dashboard_url,
            {"status": UpcyclingRequest.Status.AWAITING_FABRIC},
        )
        self.assertEqual(
            response.context["selected_admin_status"],
            UpcyclingRequest.Status.PENDING_ASSIGNMENT,
        )
        self.assertNotContains(response, other_request.reference_code)

    def test_admin_dashboard_keeps_summary_counts_and_segmented_status_filter(self):
        make_request(self.user)
        make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.PENDING_REVIEW,
        )
        make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.IN_PROGRESS,
        )
        staff = User.objects.create_user(username="admin-summary-layout", is_staff=True)
        self.client.force_login(staff)

        response = self.client.get(reverse("upcycling:admin_dashboard"))

        self.assertEqual(response.context["pending_assignment_count"], 1)
        self.assertEqual(response.context["pending_review_count"], 1)
        self.assertEqual(response.context["in_progress_count"], 1)
        self.assertContains(response, 'aria-label="Ringkasan request"')
        self.assertContains(response, 'id="admin-status-filter"')
        self.assertContains(response, 'aria-label="Filter status request admin"')
        self.assertContains(
            response,
            'class="mb-7 inline-flex w-fit max-w-full items-center gap-1 overflow-x-auto rounded-full',
        )
        self.assertContains(response, 'data-status-count="PENDING_ASSIGNMENT">1</p>')

    def test_admin_assignment_form_is_inside_the_request_card(self):
        request_obj = make_request(self.user)
        staff = User.objects.create_user(username="admin-assignment-layout", is_staff=True)
        self.client.force_login(staff)

        response = self.client.get(reverse("upcycling:admin_dashboard"))
        page = response.content.decode()
        request_position = page.index(request_obj.reference_code)
        card_start = page.rfind("<article", 0, request_position)
        card_end = page.index("</article>", card_start)
        detail_link = page.index("Lihat Detail →", card_start)
        assignment_form = page.index('action="/upcycling/admin-dashboard/assign/')

        self.assertLess(card_start, assignment_form)
        self.assertLess(detail_link, assignment_form)
        self.assertLess(assignment_form, card_end)
        self.assertContains(response, "Lihat Detail →")

    def test_admin_request_card_uses_single_preview_and_keeps_all_photos_in_zoom_gallery(self):
        request_obj = make_request(
            self.user,
            fabric_photo=make_png(),
        )
        extra_photos = [
            AdditionalFabricPhoto.objects.create(
                request=request_obj,
                image=make_png(),
            )
            for _ in range(2)
        ]
        primary_photo_url = request_obj.fabric_photo.url
        self.client.force_login(self.user)

        member_list = self.client.get(reverse("upcycling:request_list"))

        self.assertContains(member_list, primary_photo_url)
        for photo in extra_photos:
            self.assertNotContains(member_list, photo.image.url)

        staff = User.objects.create_user(username="thumbnail-admin", is_staff=True)
        self.client.force_login(staff)
        admin_dashboard = self.client.get(reverse("upcycling:admin_dashboard"))

        self.assertContains(admin_dashboard, primary_photo_url)
        for photo in extra_photos:
            self.assertContains(admin_dashboard, photo.image.url)
        self.assertEqual(admin_dashboard.content.count(b'data-fabric-photo-zoom='), 3)
        self.assertEqual(admin_dashboard.content.count(b'data-photo-zoom-icon'), 1)
        self.assertContains(admin_dashboard, 'lg:grid-cols-[16.5rem_minmax(0,1fr)_auto]')
        self.assertContains(admin_dashboard, 'class="hidden"')
        self.assertNotContains(admin_dashboard, f'Pemohon: {self.user.username}')
        self.assertContains(admin_dashboard, 'id="artisan-photo-zoom"')
        self.assertContains(admin_dashboard, 'src="/static/js/upcycling-photo-zoom.js"')

    def test_admin_dashboard_only_shows_eligible_artisans_for_unassigned_requests(self):
        request_obj = make_request(self.user)
        full_user = User.objects.create_user(username="admin-queue-full")
        full_artisan = ArtisanProfile.objects.create(user=full_user, max_active_requests=1)
        full_artisan.specializations.add(self.product_type)
        make_request(self.user, artisan=full_artisan, status=UpcyclingRequest.Status.PENDING_REVIEW)

        pouch_type, _ = ProductType.objects.get_or_create(
            code="POUCH", defaults={"name": "Pouch"}
        )
        wrong_user = User.objects.create_user(username="admin-queue-wrong-skill")
        wrong_artisan = ArtisanProfile.objects.create(user=wrong_user)
        wrong_artisan.specializations.add(pouch_type)
        ungrouped_user = User.objects.create_user(username="admin-queue-ungrouped")
        ungrouped_artisan = ArtisanProfile.objects.create(user=ungrouped_user)
        ungrouped_artisan.specializations.add(self.product_type)

        staff = User.objects.create_user(username="queue-admin", is_staff=True)
        self.client.force_login(staff)

        response = self.client.get(reverse("upcycling:admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, request_obj.reference_code)
        self.assertContains(response, "Dashboard Admin")
        self.assertContains(response, self.artisan_user.username)
        self.assertContains(response, 'hx-target="#admin-dashboard-live"')
        self.assertContains(response, 'hx-select="#admin-dashboard-live"')
        self.assertContains(response, 'hx-swap="outerHTML show:none"')
        self.assertNotContains(response, full_user.username)
        self.assertNotContains(response, wrong_user.username)
        self.assertNotContains(response, ungrouped_user.username)

    def test_admin_dashboard_keeps_request_queued_when_no_artisan_is_eligible(self):
        request_obj = make_request(self.user)
        self.artisan.is_available = False
        self.artisan.save(update_fields=("is_available",))
        staff = User.objects.create_user(username="queue-no-candidate-admin", is_staff=True)
        self.client.force_login(staff)

        response = self.client.get(reverse("upcycling:admin_dashboard"))

        self.assertContains(response, request_obj.reference_code)
        self.assertContains(response, "Belum ada artisan yang cocok dan tersedia.")
        self.assertNotContains(response, "Pilih artisan yang sesuai")

    def test_admin_dashboard_assigns_artisan_and_records_admin_actor(self):
        request_obj = make_request(self.user)
        staff = User.objects.create_user(username="queue-assign-admin", is_staff=True)
        self.client.force_login(staff)

        response = self.client.post(
            reverse("upcycling:admin_assign_artisan", args=[request_obj.pk]),
            {"artisan": str(self.artisan.pk)},
        )

        request_obj.refresh_from_db()
        self.assertRedirects(response, reverse("upcycling:admin_dashboard"))
        self.assertEqual(request_obj.artisan, self.artisan)
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.PENDING_REVIEW)
        history = request_obj.status_history.get(to_status=UpcyclingRequest.Status.PENDING_REVIEW)
        self.assertEqual(history.from_status, UpcyclingRequest.Status.PENDING_ASSIGNMENT)
        self.assertEqual(history.changed_by, staff)

    def test_admin_dashboard_rejects_self_assignment(self):
        request_obj = make_request(self.artisan_user)
        staff = User.objects.create_user(username="queue-self-admin", is_staff=True)
        self.client.force_login(staff)

        response = self.client.post(
            reverse("upcycling:admin_assign_artisan", args=[request_obj.pk]),
            {"artisan": str(self.artisan.pk)},
        )

        request_obj.refresh_from_db()
        self.assertRedirects(response, reverse("upcycling:admin_dashboard"))
        self.assertIsNone(request_obj.artisan_id)
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.PENDING_ASSIGNMENT)

    def test_admin_dashboard_rejects_tampered_ineligible_artisan(self):
        request_obj = make_request(self.user)
        pouch_type, _ = ProductType.objects.get_or_create(
            code="POUCH", defaults={"name": "Pouch"}
        )
        wrong_user = User.objects.create_user(username="queue-tampered-artisan")
        artisan_group, _ = Group.objects.get_or_create(name="Artisan")
        wrong_user.groups.add(artisan_group)
        wrong_artisan = ArtisanProfile.objects.create(user=wrong_user)
        wrong_artisan.specializations.add(pouch_type)
        staff = User.objects.create_user(username="queue-tamper-admin", is_staff=True)
        self.client.force_login(staff)

        response = self.client.post(
            reverse("upcycling:admin_assign_artisan", args=[request_obj.pk]),
            {"artisan": str(wrong_artisan.pk)},
        )

        request_obj.refresh_from_db()
        self.assertRedirects(response, reverse("upcycling:admin_dashboard"))
        self.assertIsNone(request_obj.artisan_id)
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.PENDING_ASSIGNMENT)

    def test_admin_dashboard_rejects_assignment_to_full_artisan(self):
        request_obj = make_request(self.user)
        self.artisan.max_active_requests = 1
        self.artisan.save(update_fields=("max_active_requests",))
        make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.PENDING_REVIEW,
        )
        staff = User.objects.create_user(username="queue-capacity-admin", is_staff=True)
        self.client.force_login(staff)

        response = self.client.post(
            reverse("upcycling:admin_assign_artisan", args=[request_obj.pk]),
            {"artisan": str(self.artisan.pk)},
        )

        request_obj.refresh_from_db()
        self.assertRedirects(response, reverse("upcycling:admin_dashboard"))
        self.assertIsNone(request_obj.artisan_id)
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.PENDING_ASSIGNMENT)

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

        self.assertContains(response, 'name="work_price" type="text" inputmode="numeric"')
        self.assertContains(response, 'data-rupiah-input')
        self.assertContains(response, 'name="additional_fee_type"')
        self.assertContains(response, 'name="additional_fee_amount"')
        self.assertNotContains(response, 'name="batik_material_price"')
        response = self.client.post(
            reverse("upcycling:artisan_update_request", args=[request_obj.pk]),
            {"action": "inspection_pass", "work_price": "75555", "notes": "Layak."},
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
                    {"action": "inspection_pass", "work_price": price, "notes": "Layak."},
                )

                request_obj.refresh_from_db()
                self.assertEqual(request_obj.status, UpcyclingRequest.Status.INSPECTION)
                self.assertIsNone(request_obj.quoted_price)

    def test_artisan_quote_includes_requested_batik_and_described_additional_fee(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.INSPECTION,
            fabric_received_at=timezone.now(),
            wants_batik_accent=True,
        )
        self.client.force_login(self.artisan_user)

        response = self.client.get(reverse("upcycling:request_detail", args=[request_obj.pk]))
        self.assertContains(response, 'name="batik_material_price"')

        response = self.client.post(
            reverse("upcycling:artisan_update_request", args=[request_obj.pk]),
            {
                "action": "inspection_pass",
                "work_price": "75.000",
                "batik_material_price": "15.000",
                "additional_fee_type": "Penyesuaian desain khusus",
                "additional_fee_amount": "5.000",
                "notes": "Kain layak.",
            },
        )

        request_obj.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(str(request_obj.work_price), "75000.00")
        self.assertEqual(str(request_obj.batik_material_price), "15000.00")
        self.assertEqual(request_obj.additional_fee_type, "Penyesuaian desain khusus")
        self.assertEqual(str(request_obj.additional_fee_amount), "5000.00")
        self.assertEqual(str(request_obj.quoted_price), "95000.00")

    def test_additional_fee_requires_both_description_and_amount(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.INSPECTION,
            fabric_received_at=timezone.now(),
        )
        self.client.force_login(self.artisan_user)

        response = self.client.post(
            reverse("upcycling:artisan_update_request", args=[request_obj.pk]),
            {
                "action": "inspection_pass",
                "work_price": "45000",
                "additional_fee_type": "Aksesori tambahan",
                "additional_fee_amount": "",
                "notes": "Layak.",
            },
        )

        self.assertRedirects(
            response,
            reverse("upcycling:request_detail", args=[request_obj.pk]),
        )
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.INSPECTION)
        self.assertIsNone(request_obj.quoted_price)

    def test_member_sees_quote_price_breakdown_and_total(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.AWAITING_APPROVAL,
            wants_batik_accent=True,
            work_price=75000,
            batik_material_price=15000,
            additional_fee_type="Penyesuaian desain khusus",
            additional_fee_amount=5000,
            quoted_price=95000,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("upcycling:request_detail", args=[request_obj.pk]))

        self.assertContains(response, "Harga pengerjaan")
        self.assertContains(response, "Biaya kain batik tambahan")
        self.assertContains(response, "Penyesuaian desain khusus")
        self.assertContains(response, "Total penawaran artisan")
        self.assertContains(response, "Rp95.000")
        self.assertContains(
            response,
            'class="upcycling-danger-action-button min-h-12 w-full px-5 py-3 sm:w-auto"',
        )

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

    def test_approving_quote_requests_delivery_details_before_production(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.AWAITING_APPROVAL,
            quoted_price="75000",
        )
        request_obj.delivery_method = ""
        request_obj.address = ""
        request_obj.save(update_fields=("delivery_method", "address"))
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("upcycling:approve_quote", args=[request_obj.pk]),
            {},
        )
        self.assertRedirects(response, reverse("upcycling:request_detail", args=[request_obj.pk]))
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS)
        self.assertIsNotNone(request_obj.approved_at)
        self.assertEqual(request_obj.delivery_method, "")
        self.assertEqual(request_obj.address, "")
        self.assertNotIn("AWAITING_PAYMENT", dict(UpcyclingRequest.Status.choices))
        self.assertNotIn(
            "payment_status",
            {field.name for field in UpcyclingRequest._meta.get_fields()},
        )

        response = self.client.post(
            reverse("upcycling:submit_product_delivery", args=[request_obj.pk]),
            {"delivery_method": "DROP_OFF", "address": "Depok"},
        )
        self.assertRedirects(response, reverse("upcycling:request_detail", args=[request_obj.pk]))
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.IN_PROGRESS)
        self.assertEqual(request_obj.delivery_method, "DROP_OFF")
        self.assertEqual(request_obj.address, "Depok")

    def test_user_cannot_start_production_without_delivery_details(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.AWAITING_APPROVAL,
            quoted_price="75000",
        )
        request_obj.delivery_method = ""
        request_obj.address = ""
        request_obj.save(update_fields=("delivery_method", "address"))
        self.client.force_login(self.user)
        self.client.post(reverse("upcycling:approve_quote", args=[request_obj.pk]))
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS)
        response = self.client.post(
            reverse("upcycling:submit_product_delivery", args=[request_obj.pk]),
            {},
            follow=True,
        )
        request_obj.refresh_from_db()

        self.assertEqual(request_obj.status, UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS)
        self.assertIsNotNone(request_obj.approved_at)
        self.assertContains(response, "Pilih metode penerimaan produk dan isi alamat")

    def test_user_cannot_cancel_after_approving_quote_before_production(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS,
            quoted_price="75000",
            approved_at=timezone.now(),
            fabric_received_at=timezone.now(),
            fabric_received_by=self.artisan_user,
        )
        self.client.force_login(self.user)

        detail = self.client.get(reverse("upcycling:request_detail", args=[request_obj.pk]))
        self.assertNotContains(detail, "Batalkan permintaan")
        self.assertContains(detail, "Harga sudah disetujui. Permintaan tidak dapat dibatalkan mandiri")

        response = self.client.post(
            reverse("upcycling:cancel_request", args=[request_obj.pk]),
            follow=True,
        )

        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.AWAITING_DELIVERY_DETAILS)
        self.assertEqual(request_obj.return_status, UpcyclingRequest.ReturnStatus.NOT_REQUIRED)
        self.assertContains(response, "Harga sudah disetujui")

    def test_user_can_reject_quote_before_approving_it_after_fabric_received(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.AWAITING_APPROVAL,
            quoted_price="75000",
            fabric_received_at=timezone.now(),
            fabric_received_by=self.artisan_user,
        )
        self.client.force_login(self.user)

        detail = self.client.get(reverse("upcycling:request_detail", args=[request_obj.pk]))
        self.assertContains(detail, "Tolak penawaran")

        response = self.client.post(
            reverse("upcycling:cancel_request", args=[request_obj.pk]),
            {"action": "reject_quote"},
            follow=True,
        )

        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, UpcyclingRequest.Status.CANCELLED)
        self.assertEqual(request_obj.return_status, UpcyclingRequest.ReturnStatus.PENDING_RETURN)
        self.assertContains(response, "Penawaran ditolak. Kain akan dikembalikan.")

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

    def test_completion_actions_share_one_row_with_approval_note_below(self):
        request_obj = make_request(
            self.user,
            artisan=self.artisan,
            status=UpcyclingRequest.Status.READY,
            quoted_price="75000",
            approved_at=timezone.now(),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("upcycling:request_detail", args=[request_obj.pk]))
        page = response.content.decode()
        summary_position = page.index('id="summary-heading"')
        actions_position = page.index('id="completion-contact-actions"')
        confirm_position = page.index("Konfirmasi produk diterima")
        whatsapp_position = page.index("Hubungi Tim via WhatsApp")
        approval_note_position = page.index(
            "Harga sudah disetujui. Permintaan tidak dapat dibatalkan mandiri"
        )

        self.assertLess(summary_position, actions_position)
        self.assertLess(actions_position, confirm_position)
        self.assertLess(confirm_position, whatsapp_position)
        self.assertLess(whatsapp_position, approval_note_position)
