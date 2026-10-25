from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from .models import PointTransaction
from .services import (
    InsufficientPoints,
    award_upcycling_completion,
    award_verified_donation,
    calculate_donation_points,
    get_available_points,
    get_lifetime_points,
    redeem_points,
)


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

    def make_transaction(self, user, kind, points, reference, description):
        """Create a ledger row for page presentation tests."""
        return PointTransaction.objects.create(
            user=user,
            kind=kind,
            points=points,
            source_reference=reference,
            description=description,
        )

    def test_points_overview_requires_login(self):
        """Keep a user's point balance private from anonymous visitors."""
        response = self.client.get("/rewards/")

        self.assertRedirects(response, "/login/?next=/rewards/")

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
