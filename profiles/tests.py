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
        voucher_url = reverse("rewards:admin_vouchers")
        self.assertContains(response, voucher_url)
        self.assertContains(response, f"{voucher_url}#voucher-form")
        add_voucher_links = f'href="{voucher_url}#voucher-form"'.encode()
        self.assertEqual(response.content.count(add_voucher_links), 3)

    def test_regular_user_does_not_see_add_voucher_navigation_link(self):
        member = get_user_model().objects.create_user(
            username="regular-member",
            email="regular-member@example.com",
            password="test-password",
        )
        self.client.force_login(member)

        response = self.client.get(reverse("profiles:overview"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Tambah voucher")
