from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import PointTransaction, Reward, RewardRedemption
from .services import (
    InsufficientPoints,
    cancel_physical_redemption,
    get_available_points,
    get_lifetime_points,
    redeem_reward,
)


User = get_user_model()


class RewardWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="pw")
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "pw")
        PointTransaction.objects.create(
            user=self.user,
            kind=PointTransaction.Kind.UPCYCLING_COMPLETED,
            points=300,
            source_reference="seed-credit",
            description="Saldo awal tes",
        )

    def test_reward_page_hero_uses_readable_text_on_light_background(self):
        stylesheet = (
            Path(__file__).resolve().parent.parent
            / "static"
            / "css"
            / "rewards.css"
        ).read_text(encoding="utf-8")
        hero_rule = stylesheet.split(".rewards-hero {", 1)[1].split("}", 1)[0]

        self.assertIn("color: var(--rewards-brown);", hero_rule)

    def test_voucher_redemption_debits_points_and_uses_reward_stock_once(self):
        reward = Reward.objects.create(
            name="Voucher 20 ribu",
            reward_type=Reward.Type.VOUCHER,
            points_required=100,
            stock=2,
            discount_value="20000",
        )

        redemption = redeem_reward(self.user, reward.pk)

        reward.refresh_from_db()
        self.assertEqual(redemption.status, RewardRedemption.Status.FULFILLED)
        self.assertEqual(redemption.voucher_status, RewardRedemption.VoucherStatus.AVAILABLE)
        self.assertTrue(redemption.voucher_code)
        self.assertEqual(reward.stock, 1)
        self.assertEqual(get_available_points(self.user), 200)
        spend = PointTransaction.objects.get(
            reward_redemption=redemption,
            kind=PointTransaction.Kind.REDEMPTION,
        )
        self.assertEqual(spend.points, -100)

    def test_admin_cancellation_refunds_points_and_restores_physical_stock(self):
        reward = Reward.objects.create(
            name="Scrunchie batik",
            reward_type=Reward.Type.PHYSICAL,
            points_required=100,
            stock=1,
        )
        redemption = redeem_reward(self.user, reward.pk, shipping_address="Depok")
        self.assertEqual(get_available_points(self.user), 200)

        cancel_physical_redemption(
            redemption,
            admin_user=self.admin,
            reason="Stok rusak saat pengecekan.",
        )

        reward.refresh_from_db()
        redemption.refresh_from_db()
        self.assertEqual(redemption.status, RewardRedemption.Status.CANCELLED)
        self.assertEqual(redemption.cancelled_by, self.admin)
        self.assertEqual(reward.stock, 1)
        self.assertEqual(get_available_points(self.user), 300)
        self.assertEqual(
            PointTransaction.objects.filter(
                reward_redemption=redemption,
                kind=PointTransaction.Kind.REWARD_REFUNDED,
            ).count(),
            1,
        )
        self.assertEqual(get_lifetime_points(self.user), 300)

    def test_insufficient_balance_does_not_change_stock_or_create_redemption(self):
        reward = Reward.objects.create(
            name="Hadiah mahal",
            reward_type=Reward.Type.PHYSICAL,
            points_required=500,
            stock=4,
        )

        with self.assertRaises(InsufficientPoints):
            redeem_reward(self.user, reward.pk, shipping_address="Depok")

        reward.refresh_from_db()
        self.assertEqual(reward.stock, 4)
        self.assertFalse(RewardRedemption.objects.exists())
