from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AdminDashboardVoucherLinksTests(TestCase):
    def test_admin_dashboard_links_to_voucher_catalog_and_add_form(self):
        admin_user = get_user_model().objects.create_superuser(
            username="admin-vouchers",
            email="admin-vouchers@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("profiles:overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kelola Katalog Voucher")
        self.assertContains(response, reverse("admin:rewards_reward_changelist"))
        self.assertContains(response, reverse("admin:rewards_reward_add"))
