from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from .models import PointTransaction, Reward, RewardRedemption
from .services import award_upcycling_completion, get_available_points, redeem_reward


class RewardsAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.member = get_user_model().objects.create_user("member")
        cls.other = get_user_model().objects.create_user("other")
        cls.voucher = Reward.objects.create(
            name="Voucher Batik", reward_type=Reward.Type.VOUCHER,
            points_required=100, stock=2, discount_value="15000",
        )
        for user in (cls.member, cls.other):
            award_upcycling_completion(user, request_reference="first")

    def setUp(self):
        self.client.force_login(self.member)
        self.redeem_url = reverse("api_rewards:redeem", args=[self.voucher.pk])

    def test_redemption_rate_limit_is_per_user_and_expires(self):
        missing = reverse("api_rewards:redeem", args=[self.voucher.pk + 1000])
        start = timezone.now()
        with patch("config.rate_limits.now", return_value=start) as timer:
            self.assertEqual(self.client.options(self.redeem_url).status_code, 200)
            for attempt in range(5):
                with self.subTest(attempt=attempt + 1):
                    self.assertEqual(self.client.post(missing).status_code, 404)
            second_session = APIClient()
            second_session.force_login(self.member)
            timer.return_value = start + timedelta(seconds=15)
            response = second_session.post(self.redeem_url)
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response["Retry-After"], "45")
            self.assertIn("detail", response.json())
            self.assertEqual(get_available_points(self.member), 150)
            self.voucher.refresh_from_db()
            self.assertEqual(self.voucher.stock, 2)
            self.assertFalse(RewardRedemption.objects.exists())
            self.assertEqual(self.client.get(reverse("api_rewards:catalog")).status_code, 200)

            self.client.force_login(self.other)
            self.assertEqual(self.client.post(self.redeem_url).status_code, 201)
            timer.return_value = start + timedelta(seconds=60)
            self.client.force_login(self.member)
            self.assertEqual(self.client.post(self.redeem_url).status_code, 201)

    def test_login_and_csrf_required(self):
        client = APIClient(enforce_csrf_checks=True)
        for route in ("overview", "catalog", "history", "my-vouchers", "admin-vouchers"):
            with self.subTest(route=route):
                self.assertEqual(client.get(reverse(f"api_rewards:{route}")).status_code, 403)
        client.force_login(self.member)
        self.assertEqual(client.post(self.redeem_url).status_code, 403)
        self.assertFalse(RewardRedemption.objects.exists())
        token = client.get(reverse("api_auth:csrf")).json()["csrfToken"]
        self.assertEqual(client.post(self.redeem_url, HTTP_X_CSRFTOKEN=token).status_code, 201)

    def test_catalog_and_overview_exclude_unavailable_rewards(self):
        for overrides in ({"stock": 0}, {"is_active": False}, {"reward_type": Reward.Type.PHYSICAL}):
            fields = {"reward_type": Reward.Type.VOUCHER, "stock": 1, **overrides}
            Reward.objects.create(name="Hidden", points_required=1, **fields)
        catalog = self.client.get(reverse("api_rewards:catalog")).json()
        self.assertEqual([item["id"] for item in catalog], [self.voucher.pk])
        overview = self.client.get(reverse("api_rewards:overview")).json()
        self.assertEqual(overview["featured_vouchers"], catalog)
        self.assertEqual(overview["available_points"], 150)
        self.assertEqual(overview["current_level"], "Penenun Pemula")
        self.assertEqual(len(overview["recent_transactions"]), 1)

    def test_redeem_and_read_only_own_voucher_and_history(self):
        other_voucher = redeem_reward(self.other, self.voucher.pk)
        response = self.client.post(self.redeem_url, {"user": self.other.pk, "points_spent": 0}, format="json")
        self.assertEqual(response.status_code, 201)
        redemption = response.json()["redemption"]
        self.assertEqual(response.json()["available_points"], 50)
        self.assertEqual(redemption["discount_value_snapshot"], "15000.00")
        self.assertEqual(redemption["points_spent"], 100)
        self.assertNotEqual(redemption["voucher_code"], other_voucher.voucher_code)
        self.assertEqual(self.client.get(reverse("api_rewards:my-vouchers")).json(), [redemption])
        history = reverse("api_rewards:history")
        for direction, points in (("in", 150), ("out", -100)):
            page = self.client.get(history, {"type": direction}).json()
            self.assertEqual(page["count"], 1)
            self.assertEqual(page["results"][0]["points"], points)
        self.assertEqual(self.client.post(self.redeem_url).status_code, 400)
        self.assertEqual(get_available_points(self.member), 50)
        self.voucher.refresh_from_db()
        self.assertEqual(self.voucher.stock, 0)

    def test_insufficient_points_and_missing_voucher_do_not_change_state(self):
        Reward.objects.filter(pk=self.voucher.pk).update(points_required=151)
        self.assertEqual(self.client.post(self.redeem_url).status_code, 400)
        Reward.objects.filter(pk=self.voucher.pk).update(is_active=False)
        self.assertEqual(self.client.post(self.redeem_url).status_code, 404)
        self.voucher.refresh_from_db()
        self.assertEqual(self.voucher.stock, 2)
        self.assertEqual(get_available_points(self.member), 150)
        self.assertFalse(PointTransaction.objects.filter(kind=PointTransaction.Kind.REDEMPTION).exists())

    def test_admin_permissions_and_catalog_updates(self):
        listing = reverse("api_rewards:admin-vouchers")
        self.assertEqual(self.client.get(listing).status_code, 403)
        staff = get_user_model().objects.create_user("staff", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.post(listing, {}).status_code, 403)
        staff.user_permissions.add(Permission.objects.get(content_type__app_label="rewards", codename="add_reward"))
        payload = {"name": "Batik", "stock": 1, "points_required": 50, "code_prefix": "batik"}
        self.assertEqual(self.client.post(listing, payload, format="json").status_code, 400)
        created = self.client.post(listing, {**payload, "discount_value": "5000"}, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["code_prefix"], "BATIK")
        detail = reverse("api_rewards:admin-voucher-detail", args=[created.data["id"]])
        change = {"is_active": False}
        self.assertEqual(self.client.patch(detail, change, format="json").status_code, 403)
        staff.user_permissions.add(Permission.objects.get(content_type__app_label="rewards", codename="change_reward"))
        self.assertEqual(self.client.patch(detail, change, format="json").status_code, 200)
        catalog = self.client.get(reverse("api_rewards:catalog")).json()
        self.assertNotIn(created.data["id"], [item["id"] for item in catalog])

    def test_staff_with_only_change_permission_can_load_and_edit_by_id(self):
        staff = get_user_model().objects.create_user("editor", is_staff=True)
        staff.user_permissions.add(Permission.objects.get(content_type__app_label="rewards", codename="change_reward"))
        self.client.force_login(staff)
        detail = reverse("api_rewards:admin-voucher-detail", args=[self.voucher.pk])
        self.assertEqual(self.client.get(reverse("api_rewards:admin-vouchers")).status_code, 403)
        self.assertEqual(self.client.get(detail).status_code, 200)
        response = self.client.patch(detail, {"name": "Voucher Baru"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Voucher Baru")
        self.assertEqual(self.client.patch(detail, {"code_prefix": "ß" * 20}, format="json").status_code, 400)

    def test_new_vouchers_have_the_same_active_default_for_json_and_multipart(self):
        staff = get_user_model().objects.create_user("creator", is_staff=True)
        staff.user_permissions.add(Permission.objects.get(content_type__app_label="rewards", codename="add_reward"))
        self.client.force_login(staff)
        listing = reverse("api_rewards:admin-vouchers")
        payload = {"name": "Batik", "points_required": 20, "stock": 1}
        for encoding in ("json", "multipart"):
            with self.subTest(encoding=encoding):
                self.assertEqual(self.client.post(listing, payload, format=encoding).status_code, 400)
                response = self.client.post(listing, {**payload, "discount_value": "5000"}, format=encoding)
                self.assertEqual(response.status_code, 201)
                self.assertTrue(response.data["is_active"])

    def test_misconfigured_vouchers_are_hidden_and_cannot_be_redeemed(self):
        for cost, discount in ((0, 1000), (100, None), (100, 0)):
            with self.subTest(cost=cost, discount=discount):
                Reward.objects.filter(pk=self.voucher.pk).update(points_required=cost, discount_value=discount)
                self.assertEqual(self.client.get(reverse("api_rewards:catalog")).json(), [])
                overview = self.client.get(reverse("api_rewards:overview")).json()
                self.assertEqual(overview["featured_vouchers"], [])
                self.assertEqual(self.client.post(self.redeem_url).status_code, 400)
        self.voucher.refresh_from_db()
        self.assertEqual(self.voucher.stock, 2)
        self.assertEqual(get_available_points(self.member), 150)
        self.assertFalse(RewardRedemption.objects.exists())
