from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal
from importlib import import_module
from pathlib import Path
import tempfile
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from .models import PointTransaction, Reward
from .admin import RewardAdmin, RewardAdminForm
from .services import (
    InsufficientPoints,
    award_upcycling_completion,
    award_verified_donation,
    calculate_donation_points,
    get_available_points,
    get_lifetime_points,
    redeem_points,
)
from .views import _level_progress
from .templatetags.rewards_format import decimal_comma_id


class VoucherAdminPresentationTests(SimpleTestCase):
    def test_new_reward_form_is_prepared_for_adding_a_voucher(self):
        form = RewardAdminForm()

        self.assertEqual(form["reward_type"].value(), Reward.Type.VOUCHER)
        self.assertEqual(form.fields["name"].label, "Nama voucher")
        self.assertIn("nama singkat", form.fields["name"].help_text)
        self.assertEqual(form.fields["image"].label, "Gambar voucher")

    def test_reward_admin_groups_fields_and_shows_catalog_images(self):
        model_admin = RewardAdmin(Reward, admin.site)

        self.assertEqual(Reward._meta.verbose_name_plural, "katalog voucher")
        self.assertEqual(
            model_admin.fieldsets,
            (
                ("Informasi voucher", {"fields": ("name", "description", "reward_type")}),
                ("Penukaran", {"fields": ("points_required", "discount_value", "stock", "is_active")}),
                ("Gambar katalog", {"fields": ("image",)}),
            ),
        )
        self.assertIn("image_preview", model_admin.list_display)


class LegacyDonationWeightMigrationTests(SimpleTestCase):
    def test_backfills_only_weights_in_the_known_legacy_description_format(self):
        saved = []
        records = [
            SimpleNamespace(
                kind="donation",
                weight_kg=None,
                description="Donasi terverifikasi (1.25 kg)",
                save=lambda **kwargs: saved.append(("known", kwargs)),
            ),
            SimpleNamespace(
                kind="donation",
                weight_kg=None,
                description="Donasi kain tercatat, berat tidak dicantumkan",
                save=lambda **kwargs: saved.append(("unknown", kwargs)),
            ),
            SimpleNamespace(
                kind="donation",
                weight_kg=None,
                description="Donasi terverifikasi (4E-7 kg)",
                save=lambda **kwargs: saved.append(("unrepresentable", kwargs)),
            ),
        ]

        class FakeQuerySet:
            def __init__(self, rows):
                self.rows = rows

            def iterator(self):
                return iter(self.rows)

        class FakeManager:
            def filter(self, **filters):
                self.filters = filters
                return FakeQuerySet(
                    row
                    for row in records
                    if row.kind == filters["kind"] and row.weight_kg is None
                )

        fake_manager = FakeManager()
        historical_model = SimpleNamespace(objects=fake_manager)
        fake_apps = SimpleNamespace(
            get_model=lambda app_label, model_name: historical_model
        )
        migration = import_module(
            "rewards.migrations.0002_pointtransaction_weight_kg_and_more"
        )

        migration.backfill_donation_weights(fake_apps, schema_editor=None)

        self.assertEqual(records[0].weight_kg, Decimal("1.25"))
        self.assertIsNone(records[1].weight_kg)
        self.assertIsNone(records[2].weight_kg)
        self.assertEqual(len(saved), 1)
        self.assertEqual(fake_manager.filters["kind"], "donation")


class RewardDiscountSnapshotMigrationTests(SimpleTestCase):
    def test_backfills_existing_redemptions_from_the_reward_value(self):
        redemptions = [
            SimpleNamespace(
                pk=1,
                discount_value_snapshot=None,
                reward=SimpleNamespace(discount_value=Decimal("20000.00")),
            ),
            SimpleNamespace(
                pk=2,
                discount_value_snapshot=None,
                reward=SimpleNamespace(discount_value=None),
            ),
        ]

        class FakeQuerySet:
            def __init__(self, rows):
                self.rows = rows

            def select_related(self, *fields):
                return self

            def iterator(self):
                return iter(self.rows)

            def update(self, **values):
                for row in self.rows:
                    for name, value in values.items():
                        setattr(row, name, value)
                return len(self.rows)

        class FakeManager:
            def using(self, alias):
                return self

            def filter(self, **filters):
                rows = redemptions
                if filters.get("discount_value_snapshot__isnull"):
                    rows = [row for row in rows if row.discount_value_snapshot is None]
                if "pk" in filters:
                    rows = [row for row in rows if row.pk == filters["pk"]]
                return FakeQuerySet(rows)

        historical_model = SimpleNamespace(objects=FakeManager())
        fake_apps = SimpleNamespace(
            get_model=lambda app_label, model_name: historical_model
        )
        schema_editor = SimpleNamespace(
            connection=SimpleNamespace(alias="default")
        )
        migration = import_module(
            "rewards.migrations.0004_rewardredemption_discount_value_snapshot"
        )

        migration.backfill_discount_value_snapshot(fake_apps, schema_editor)

        self.assertEqual(redemptions[0].discount_value_snapshot, Decimal("20000.00"))
        self.assertIsNone(redemptions[1].discount_value_snapshot)


class LevelProgressTests(SimpleTestCase):
    def test_level_names_are_consistent_at_each_tier_boundary(self):
        cases = (
            (0, "Penenun Pemula", "Penenun Mahir"),
            (1999, "Penenun Pemula", "Penenun Mahir"),
            (2000, "Penenun Mahir", "Penenun Ahli"),
            (4999, "Penenun Mahir", "Penenun Ahli"),
            (5000, "Penenun Ahli", None),
        )

        for lifetime_points, expected_current, expected_next in cases:
            with self.subTest(lifetime_points=lifetime_points):
                progress = _level_progress(lifetime_points)
                self.assertEqual(progress["current_level"], expected_current)
                self.assertEqual(progress["next_level"], expected_next)


class DonationPointCalculationTests(SimpleTestCase):
    def test_donation_weight_maps_to_the_figma_point_tiers(self):
        cases = (
            ("0.01", 50),
            ("0.49", 50),
            ("0.5", 100),
            ("2", 100),
            ("2.01", 200),
            ("5", 200),
            ("5.01", 300),
        )

        for weight, expected_points in cases:
            with self.subTest(weight=weight):
                self.assertEqual(
                    calculate_donation_points(Decimal(weight)),
                    expected_points,
                )

    def test_donation_weight_must_be_positive_and_numeric(self):
        for weight in (0, -1, "not a weight"):
            with self.subTest(weight=weight), self.assertRaises(ValueError):
                calculate_donation_points(weight)


class WeightFormattingTests(SimpleTestCase):
    def test_small_positive_weights_keep_significant_decimal_places(self):
        self.assertEqual(decimal_comma_id(Decimal("0.04")), "0,04")
        self.assertEqual(decimal_comma_id(Decimal("1.230000")), "1,23")
        self.assertEqual(decimal_comma_id(Decimal("0")), "0")


class PointLedgerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="points-user",
            password="safe-test-password",
        )

    def test_verified_donation_awards_weight_points_and_monthly_bonus_once(self):
        verified_at = datetime(2026, 10, 5, 8, 0, tzinfo=datetime_timezone.utc)

        donation, bonus = award_verified_donation(
            self.user,
            donation_reference="donation-1",
            weight_kg=Decimal("1.2"),
            verified_at=verified_at,
        )
        second_donation, second_bonus = award_verified_donation(
            self.user,
            donation_reference="donation-2",
            weight_kg=Decimal("3.1"),
            verified_at=verified_at,
        )

        self.assertEqual(donation.points, 100)
        self.assertEqual(
            bonus.kind,
            PointTransaction.Kind.MONTHLY_DONATION_BONUS,
        )
        self.assertEqual(bonus.points, 25)
        self.assertEqual(second_donation.points, 200)
        self.assertEqual(donation.weight_kg, Decimal("1.200"))
        self.assertEqual(second_donation.weight_kg, Decimal("3.100"))
        self.assertIsNone(second_bonus)
        self.assertEqual(
            PointTransaction.objects.filter(
                user=self.user,
                kind=PointTransaction.Kind.MONTHLY_DONATION_BONUS,
            ).count(),
            1,
        )
        self.assertEqual(get_available_points(self.user), 325)

    def test_reprocessing_same_verified_donation_does_not_duplicate_points(self):
        verified_at = datetime(2026, 10, 5, 8, 0, tzinfo=datetime_timezone.utc)
        first_transaction, first_bonus = award_verified_donation(
            self.user,
            donation_reference="donation-duplicate",
            weight_kg=Decimal("1"),
            verified_at=verified_at,
        )
        retry_transaction, retry_bonus = award_verified_donation(
            self.user,
            donation_reference="donation-duplicate",
            weight_kg=Decimal("1"),
            verified_at=verified_at,
        )

        self.assertEqual(first_transaction.pk, retry_transaction.pk)
        self.assertIsNotNone(first_bonus)
        self.assertIsNone(retry_bonus)
        self.assertEqual(get_available_points(self.user), 125)
        self.assertEqual(PointTransaction.objects.filter(user=self.user).count(), 2)

    def test_reprocessing_donation_rounds_weight_to_storage_precision(self):
        weight = Decimal("1.2345678")
        verified_at = datetime(2026, 10, 5, 8, 0, tzinfo=datetime_timezone.utc)
        award_verified_donation(
            self.user,
            donation_reference="donation-rounded-retry",
            weight_kg=weight,
            verified_at=verified_at,
        )
        stored_donation = PointTransaction.objects.get(
            user=self.user,
            kind=PointTransaction.Kind.DONATION,
            source_reference="donation-rounded-retry",
        )

        retry, retry_bonus = award_verified_donation(
            self.user,
            donation_reference="donation-rounded-retry",
            weight_kg=weight,
            verified_at=verified_at,
        )

        self.assertEqual(retry.pk, stored_donation.pk)
        self.assertEqual(retry.weight_kg, Decimal("1.234568"))
        self.assertIsNone(retry_bonus)

    def test_donation_below_storage_precision_is_rejected_before_database_write(self):
        with self.assertRaisesMessage(ValueError, "at least 0.000001 kg"):
            award_verified_donation(
                self.user,
                donation_reference="donation-below-storage-precision",
                weight_kg=Decimal("0.0000004"),
            )

        self.assertFalse(
            PointTransaction.objects.filter(
                user=self.user,
                source_reference="donation-below-storage-precision",
            ).exists()
        )

    def test_first_verified_donation_bonus_restarts_in_new_jakarta_month(self):
        before_month_boundary = datetime(
            2026, 10, 31, 16, 59, tzinfo=datetime_timezone.utc
        )
        after_month_boundary = datetime(
            2026, 10, 31, 17, 1, tzinfo=datetime_timezone.utc
        )

        _, october_bonus = award_verified_donation(
            self.user,
            donation_reference="donation-october",
            weight_kg=Decimal("1"),
            verified_at=before_month_boundary,
        )
        _, november_bonus = award_verified_donation(
            self.user,
            donation_reference="donation-november",
            weight_kg=Decimal("1"),
            verified_at=after_month_boundary,
        )

        self.assertIsNotNone(october_bonus)
        self.assertIsNotNone(november_bonus)
        self.assertEqual(
            PointTransaction.objects.filter(
                user=self.user,
                kind=PointTransaction.Kind.MONTHLY_DONATION_BONUS,
            ).count(),
            2,
        )

    def test_completed_upcycling_points_are_awarded_only_once(self):
        first = award_upcycling_completion(
            self.user,
            request_reference="request-1",
        )
        retry = award_upcycling_completion(
            self.user,
            request_reference="request-1",
        )

        self.assertEqual(first.pk, retry.pk)
        self.assertEqual(first.points, 150)
        self.assertEqual(get_available_points(self.user), 150)
        self.assertEqual(PointTransaction.objects.filter(user=self.user).count(), 1)

    def test_redemption_reduces_balance_but_not_lifetime_points(self):
        verified_at = datetime(2026, 10, 5, 8, 0, tzinfo=datetime_timezone.utc)
        award_verified_donation(
            self.user,
            donation_reference="donation-for-redemption",
            weight_kg=Decimal("1"),
            verified_at=verified_at,
        )
        award_upcycling_completion(
            self.user,
            request_reference="request-for-redemption",
        )

        redemption = redeem_points(
            self.user,
            redemption_reference="redemption-1",
            reward_name="Voucher Marketplace Rp25.000",
            points_cost=200,
        )

        self.assertEqual(redemption.points, -200)
        self.assertEqual(get_available_points(self.user), 75)
        self.assertEqual(get_lifetime_points(self.user), 275)

    def test_redemption_cannot_make_the_available_balance_negative(self):
        award_upcycling_completion(
            self.user,
            request_reference="request-limited",
        )

        with self.assertRaises(InsufficientPoints):
            redeem_points(
                self.user,
                redemption_reference="redemption-too-expensive",
                reward_name="Voucher Marketplace Rp25.000",
                points_cost=500,
            )

        self.assertEqual(get_available_points(self.user), 150)
        self.assertFalse(
            PointTransaction.objects.filter(
                user=self.user,
                kind=PointTransaction.Kind.REDEMPTION,
            ).exists()
        )

    def test_retrying_same_redemption_does_not_deduct_points_twice(self):
        award_upcycling_completion(
            self.user,
            request_reference="request-redemption-retry",
        )

        first = redeem_points(
            self.user,
            redemption_reference="redemption-retry",
            reward_name="Hadiah 100 poin",
            points_cost=100,
        )
        retry = redeem_points(
            self.user,
            redemption_reference="redemption-retry",
            reward_name="Hadiah 100 poin",
            points_cost=100,
        )

        self.assertEqual(first.pk, retry.pk)
        self.assertEqual(get_available_points(self.user), 50)
        self.assertEqual(get_lifetime_points(self.user), 150)


class RewardsPageTests(TestCase):
    """Exercise authenticated points overview and transaction history pages."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="rewards-page-user",
            password="safe-test-password",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other-rewards-user",
            password="safe-test-password",
        )

    def make_transaction(
        self,
        user,
        kind,
        points,
        reference,
        description,
        weight_kg=None,
    ):
        """Create a ledger row for page presentation tests."""
        return PointTransaction.objects.create(
            user=user,
            kind=kind,
            points=points,
            source_reference=reference,
            description=description,
            weight_kg=weight_kg,
        )

    def test_points_overview_requires_login(self):
        """Keep a user's point balance private from anonymous visitors."""
        response = self.client.get("/rewards/")

        self.assertRedirects(response, "/login/?next=/rewards/")

    def test_points_overview_shows_five_vouchers_and_links_to_the_full_catalog(self):
        for index in range(7):
            Reward.objects.create(
                name=f"Voucher utama {index + 1}",
                reward_type=Reward.Type.VOUCHER,
                points_required=100 + index,
                stock=2,
                discount_value=5000 + index * 1000,
            )
        Reward.objects.create(
            name="Voucher nonaktif",
            reward_type=Reward.Type.VOUCHER,
            points_required=100,
            stock=2,
            discount_value=5000,
            is_active=False,
        )
        Reward.objects.create(
            name="Reward fisik lama",
            reward_type=Reward.Type.PHYSICAL,
            points_required=100,
            stock=2,
        )
        self.client.force_login(self.user)

        response = self.client.get("/rewards/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["featured_vouchers"]), 5)
        for index in range(1, 6):
            self.assertContains(response, f"Voucher utama {index}")
        self.assertNotContains(response, "Voucher utama 6")
        self.assertNotContains(response, "Voucher nonaktif")
        self.assertNotContains(response, "Reward fisik lama")
        self.assertContains(response, "Selengkapnya")
        self.assertContains(response, 'href="/rewards/catalog/"')

        catalog_response = self.client.get("/rewards/catalog/")
        self.assertEqual(catalog_response.context["rewards"].count(), 7)

    def test_voucher_image_renders_as_a_small_thumbnail_on_both_catalog_pages(self):
        self.client.force_login(self.user)
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                voucher = Reward.objects.create(
                    name="Voucher bergambar",
                    reward_type=Reward.Type.VOUCHER,
                    points_required=100,
                    stock=2,
                    discount_value=5000,
                    image=SimpleUploadedFile(
                        "voucher.png",
                        b"small test image",
                        content_type="image/png",
                    ),
                )

                for path in ("/rewards/", "/rewards/catalog/"):
                    with self.subTest(path=path):
                        response = self.client.get(path)
                        self.assertEqual(response.status_code, 200)
                        self.assertContains(response, 'class="voucher-thumbnail"')
                        self.assertContains(response, voucher.image.url)

        stylesheet = (
            Path(__file__).resolve().parent.parent
            / "static"
            / "css"
            / "rewards.css"
        ).read_text(encoding="utf-8")
        self.assertIn(".voucher-thumbnail", stylesheet)
        self.assertIn("width: 64px;", stylesheet)
        self.assertIn("height: 64px;", stylesheet)

    def test_earning_guide_precedes_catalog_and_voucher_link_only_appears_there(self):
        self.client.force_login(self.user)

        response = self.client.get("/rewards/")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertLess(
            html.index("Cara Mendapatkan Poin"),
            html.index("Katalog Voucher"),
        )
        catalog_start = html.index('aria-labelledby="voucher-catalog-heading"')
        history_start = html.index('id="recent-history-heading"')
        self.assertIn('href="/rewards/vouchers/">Voucher saya →', html[catalog_start:history_start])
        self.assertNotIn('href="/rewards/vouchers/"', html[history_start:])

    def test_points_overview_shows_balance_and_only_owners_recent_activity(self):
        """Show the signed-in user's balance and recent transactions only."""
        self.make_transaction(
            self.user,
            PointTransaction.Kind.DONATION,
            100,
            "overview-donation",
            "Donasi kain terverifikasi (1 kg)",
        )
        self.make_transaction(
            self.user,
            PointTransaction.Kind.REDEMPTION,
            -25,
            "overview-redemption",
            "Tukar voucher",
        )
        self.make_transaction(
            self.other_user,
            PointTransaction.Kind.DONATION,
            300,
            "private-donation",
            "Transaksi milik pengguna lain",
        )
        self.client.force_login(self.user)

        response = self.client.get("/rewards/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["available_points"], 75)
        self.assertEqual(response.context["lifetime_points"], 100)
        self.assertContains(response, "Donasi kain terverifikasi (1 kg)")
        self.assertContains(response, "Tukar voucher")
        self.assertNotContains(response, "Transaksi milik pengguna lain")

    def test_points_overview_shows_donation_upcycling_and_saved_weight_stats(self):
        """Summarize verified donations, completed upcycling, and saved fabric weight."""
        self.make_transaction(
            self.user,
            PointTransaction.Kind.DONATION,
            100,
            "stats-donation-1",
            "Donasi terverifikasi (1.2 kg)",
            weight_kg=Decimal("1.2"),
        )
        self.make_transaction(
            self.user,
            PointTransaction.Kind.DONATION,
            50,
            "stats-donation-2",
            "Donasi terverifikasi (0.4 kg)",
            weight_kg=Decimal("0.4"),
        )
        self.make_transaction(
            self.user,
            PointTransaction.Kind.UPCYCLING_COMPLETED,
            150,
            "stats-upcycling",
            "Upcycling selesai",
        )
        self.make_transaction(
            self.other_user,
            PointTransaction.Kind.DONATION,
            300,
            "other-stats-donation",
            "Donasi pengguna lain",
            weight_kg=Decimal("20"),
        )
        self.client.force_login(self.user)

        response = self.client.get("/rewards/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["donated_count"], 2)
        self.assertEqual(response.context["upcycling_count"], 1)
        self.assertEqual(response.context["saved_weight_kg"], Decimal("1.600"))
        self.assertContains(response, "Kain didonasikan")
        self.assertContains(response, "Upcycling selesai")
        self.assertContains(response, "Kain terselamatkan")
        self.assertContains(response, "1,6 kg")

    def test_points_overview_marks_legacy_donation_weight_as_unknown(self):
        self.make_transaction(
            self.user,
            PointTransaction.Kind.DONATION,
            50,
            "legacy-donation-weight-unknown",
            "Donasi kain tercatat, berat tidak diketahui",
        )
        self.client.force_login(self.user)

        response = self.client.get("/rewards/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Belum tercatat")
        self.assertNotContains(response, "0 kg")

    def test_points_overview_labels_partial_weight_total_as_a_lower_bound(self):
        self.make_transaction(
            self.user,
            PointTransaction.Kind.DONATION,
            50,
            "known-donation-weight",
            "Donasi terverifikasi (0.4 kg)",
            weight_kg=Decimal("0.4"),
        )
        self.make_transaction(
            self.user,
            PointTransaction.Kind.DONATION,
            50,
            "unknown-donation-weight",
            "Donasi kain lama tanpa berat",
        )
        self.client.force_login(self.user)

        response = self.client.get("/rewards/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "≥ 0,4 kg")

    def test_points_overview_links_to_dropoff_locations_to_donate_more_fabric(self):
        """Give users a direct path to the existing fabric drop-off directory."""
        self.client.force_login(self.user)

        response = self.client.get("/rewards/")

        self.assertContains(response, 'href="/marketplace/drop-off/"')
        self.assertContains(response, "Donasikan Kain Baru →")

    def test_points_overview_explains_all_current_earning_rules(self):
        """Explain the donation flow and all current point awards."""
        self.client.force_login(self.user)

        response = self.client.get("/rewards/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<details class="earning-guide-details">')
        self.assertContains(response, "Cara Mendapatkan Poin")
        self.assertContains(response, "Tiga langkah sederhana")
        self.assertContains(response, "Donasikan kain")
        self.assertContains(response, "Verifikasi tim")
        self.assertContains(response, "Poin masuk")
        self.assertEqual(
            response.content.count(b"/static/img/upcycling/step-number.svg"),
            3,
        )
        self.assertContains(response, "ATURAN PEROLEHAN POIN")
        self.assertNotContains(response, "Donasi kain terverifikasi (sesuai berat)")
        self.assertNotContains(response, "+50 – 300")
        self.assertContains(response, "Bonus donasi pertama bulan ini")
        self.assertContains(response, "+25")
        self.assertContains(response, "Upcycling selesai")
        self.assertContains(response, "+150")
        self.assertContains(response, "POIN DONASI SESUAI BERAT")
        self.assertContains(response, "Kurang dari 0,5 kg")
        self.assertContains(response, "0,5–2 kg")
        self.assertContains(response, "Lebih dari 2 hingga 5 kg")
        self.assertContains(response, "Lebih dari 5 kg")
        self.assertContains(response, "Bonus 25 poin berlaku untuk donasi pertama yang diverifikasi setiap bulan")

    def test_level_progress_bar_contains_three_named_tiers_without_step_circles(self):
        """Show level names beneath one segmented bar instead of numbered nodes."""
        self.client.force_login(self.user)

        response = self.client.get("/rewards/")

        self.assertEqual(
            response.content.count(b'class="level-progress-segment'),
            3,
        )
        self.assertContains(response, 'class="level-progress-segment is-current"')
        self.assertContains(response, "Penenun Pemula")
        self.assertContains(response, "Penenun Mahir")
        self.assertContains(response, "Penenun Ahli")
        self.assertNotContains(response, "level-tier-step")

    def test_expert_level_keeps_progress_full_and_shows_total_past_threshold(self):
        """Keep the highest-tier bar full and show lifetime points above its cap."""
        self.make_transaction(
            self.user,
            PointTransaction.Kind.DONATION,
            5034,
            "expert-level-donation",
            "Donasi terverifikasi",
        )
        self.client.force_login(self.user)

        response = self.client.get("/rewards/")

        self.assertContains(response, "Level tertinggi tercapai")
        self.assertContains(response, "5.034 / 5.000 poin")
        self.assertContains(response, 'aria-valuenow="5000"')
        self.assertNotContains(response, "Jenjang level")

    def test_points_overview_has_an_empty_state_without_transactions(self):
        """Explain the empty state when a user has not earned or spent points."""
        self.client.force_login(self.user)

        response = self.client.get("/rewards/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["available_points"], 0)
        self.assertContains(response, "Belum ada aktivitas poin")

    def test_transaction_history_filters_income_and_expense(self):
        """Filter the ledger without including transactions from other users."""
        self.make_transaction(
            self.user,
            PointTransaction.Kind.MONTHLY_DONATION_BONUS,
            25,
            "history-bonus",
            "Bonus donasi bulanan",
        )
        self.make_transaction(
            self.user,
            PointTransaction.Kind.REDEMPTION,
            -50,
            "history-redemption",
            "Tukar hadiah",
        )
        self.make_transaction(
            self.other_user,
            PointTransaction.Kind.DONATION,
            100,
            "other-history-donation",
            "Riwayat pribadi lain",
        )
        self.client.force_login(self.user)

        income_response = self.client.get("/rewards/history/?type=in")
        expense_response = self.client.get("/rewards/history/?type=out")

        self.assertEqual(income_response.status_code, 200)
        self.assertContains(income_response, "Bonus donasi bulanan")
        self.assertNotContains(income_response, "Tukar hadiah")
        self.assertNotContains(income_response, "Riwayat pribadi lain")
        self.assertContains(expense_response, "Tukar hadiah")
        self.assertNotContains(expense_response, "Bonus donasi bulanan")

    def test_transaction_history_paginates_six_rows_at_a_time(self):
        """Keep the history list compact and expose subsequent transactions."""
        for index in range(7):
            self.make_transaction(
                self.user,
                PointTransaction.Kind.UPCYCLING_COMPLETED,
                150,
                f"history-request-{index}",
                f"Upcycling selesai {index}",
            )
        self.client.force_login(self.user)

        first_page = self.client.get("/rewards/history/")
        second_page = self.client.get("/rewards/history/?page=2")

        self.assertEqual(first_page.context["transaction_page"].paginator.per_page, 6)
        self.assertEqual(first_page.context["transaction_page"].number, 1)
        self.assertEqual(second_page.context["transaction_page"].number, 2)
        self.assertEqual(len(second_page.context["transaction_page"].object_list), 1)
        self.assertContains(second_page, "Upcycling selesai 0")

    def test_transaction_history_htmx_filter_returns_only_refreshable_content(self):
        """Return refreshed filter, rows, and pagination without the page shell."""
        self.make_transaction(
            self.user,
            PointTransaction.Kind.UPCYCLING_COMPLETED,
            150,
            "htmx-history-credit",
            "Upcycling selesai untuk HTMX",
        )
        self.make_transaction(
            self.user,
            PointTransaction.Kind.REDEMPTION,
            -50,
            "htmx-history-debit",
            "Penukaran untuk HTMX",
        )
        self.client.force_login(self.user)

        response = self.client.get(
            "/rewards/history/?type=in",
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rewards/_history_content.html")
        self.assertContains(response, 'id="history-content"')
        self.assertContains(response, "Upcycling selesai untuk HTMX")
        self.assertNotContains(response, "Penukaran untuk HTMX")
        self.assertNotContains(response, "Points and Rewards")

    def test_transaction_history_controls_use_htmx_with_native_link_fallback(self):
        """Keep filter and pagination actions async while preserving normal links."""
        for index in range(7):
            self.make_transaction(
                self.user,
                PointTransaction.Kind.UPCYCLING_COMPLETED,
                150,
                f"htmx-history-control-{index}",
                f"Aktivitas HTMX {index}",
            )
        self.client.force_login(self.user)

        response = self.client.get("/rewards/history/")

        self.assertContains(response, 'hx-target="#history-content"')
        self.assertContains(response, 'hx-select="#history-content"')
        self.assertContains(response, 'hx-sync="#history-content:replace"')
        self.assertContains(response, 'href="?type=in"')
        self.assertContains(response, 'href="?type=all&amp;page=2"')
