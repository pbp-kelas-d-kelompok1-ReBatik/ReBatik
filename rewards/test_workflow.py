from pathlib import Path
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .admin import RewardAdminForm
from .models import PointTransaction, Reward, RewardRedemption
from .services import (
    InsufficientPoints,
    RewardUnavailable,
    get_available_points,
    redeem_reward,
)


User = get_user_model()


class RewardWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="pw")
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
        self.assertEqual(redemption.discount_value_snapshot, Decimal("20000.00"))
        self.assertEqual(reward.stock, 1)
        self.assertEqual(get_available_points(self.user), 200)
        spend = PointTransaction.objects.get(
            reward_redemption=redemption,
            kind=PointTransaction.Kind.REDEMPTION,
        )
        self.assertEqual(spend.points, -100)

    def test_physical_reward_cannot_be_redeemed(self):
        reward = Reward.objects.create(
            name="Scrunchie batik",
            reward_type=Reward.Type.PHYSICAL,
            points_required=100,
            stock=1,
        )

        with self.assertRaises(RewardUnavailable):
            redeem_reward(self.user, reward.pk)

        reward.refresh_from_db()
        self.assertEqual(reward.stock, 1)
        self.assertEqual(get_available_points(self.user), 300)
        self.assertFalse(RewardRedemption.objects.exists())

    def test_insufficient_balance_does_not_change_stock_or_create_redemption(self):
        reward = Reward.objects.create(
            name="Voucher mahal",
            reward_type=Reward.Type.VOUCHER,
            points_required=500,
            stock=4,
            discount_value="5000",
        )

        with self.assertRaises(InsufficientPoints):
            redeem_reward(self.user, reward.pk)

        reward.refresh_from_db()
        self.assertEqual(reward.stock, 4)
        self.assertFalse(RewardRedemption.objects.exists())

    def test_catalog_only_shows_vouchers_even_if_legacy_physical_reward_is_active(self):
        Reward.objects.create(
            name="Voucher aktif",
            reward_type=Reward.Type.VOUCHER,
            points_required=100,
            stock=2,
            discount_value="5000",
        )
        Reward.objects.create(
            name="Reward fisik lama",
            reward_type=Reward.Type.PHYSICAL,
            points_required=100,
            stock=2,
            is_active=True,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("rewards:catalog"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Voucher aktif")
        self.assertNotContains(response, "Reward fisik lama")

    def test_admin_cannot_create_an_active_physical_reward(self):
        form = RewardAdminForm(
            data={
                "name": "Reward fisik baru",
                "description": "",
                "reward_type": Reward.Type.PHYSICAL,
                "points_required": "100",
                "stock": "1",
                "is_active": "on",
                "discount_value": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("reward_type", form.errors)

    def test_my_vouchers_shows_only_the_signed_in_users_vouchers(self):
        reward = Reward.objects.create(
            name="Voucher 20 ribu",
            reward_type=Reward.Type.VOUCHER,
            points_required=100,
            stock=2,
            discount_value="20000",
        )
        own_redemption = redeem_reward(self.user, reward.pk)
        reward.discount_value = Decimal("25000")
        reward.save(update_fields=("discount_value",))
        other_user = User.objects.create_user(username="other", password="pw")
        PointTransaction.objects.create(
            user=other_user,
            kind=PointTransaction.Kind.UPCYCLING_COMPLETED,
            points=300,
            source_reference="other-seed-credit",
            description="Saldo awal",
        )
        other_redemption = redeem_reward(other_user, reward.pk)
        self.client.force_login(self.user)

        response = self.client.get(reverse("rewards:vouchers"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, own_redemption.voucher_code)
        self.assertContains(response, "Rp20.000")
        self.assertNotContains(response, other_redemption.voucher_code)

    def test_redemption_confirmation_does_not_spend_points_until_confirmed(self):
        reward = Reward.objects.create(
            name="Voucher 5 ribu",
            reward_type=Reward.Type.VOUCHER,
            points_required=100,
            stock=2,
            discount_value="5000",
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse("rewards:redeem", args=[reward.pk]))

        reward.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rewards/catalog.html")
        self.assertContains(response, 'id="voucher-confirm-modal"')
        self.assertContains(response, 'class="voucher-confirm-modal is-open"')
        self.assertContains(response, "Sisa setelah penukaran")
        self.assertEqual(get_available_points(self.user), 300)
        self.assertEqual(reward.stock, 2)
        self.assertFalse(RewardRedemption.objects.exists())

    def test_confirmed_redemption_spends_points_and_redirects_to_my_vouchers(self):
        reward = Reward.objects.create(
            name="Voucher 5 ribu",
            reward_type=Reward.Type.VOUCHER,
            points_required=100,
            stock=2,
            discount_value="5000",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("rewards:redeem", args=[reward.pk]),
            {"confirm": "yes"},
        )

        self.assertRedirects(response, reverse("rewards:vouchers"))
        self.assertEqual(get_available_points(self.user), 200)
        self.assertEqual(RewardRedemption.objects.count(), 1)
