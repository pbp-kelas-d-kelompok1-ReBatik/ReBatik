from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse


class AdminDashboardVoucherLinksTests(TestCase):
    def test_admin_dashboard_and_hamburger_link_to_voucher_management(self):
        admin_user = get_user_model().objects.create_superuser(
            username="admin-vouchers",
            email="admin-vouchers@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("profiles:overview"))

        self.assertEqual(response.status_code, 200)
        voucher_url = reverse("rewards:admin_vouchers")
        add_voucher_url = reverse("rewards:admin_voucher_add")
        nav_links = response.content.decode().split('<nav class="rb-drawer__nav">', 1)[1].split("</nav>", 1)[0]
        self.assertIn(voucher_url, nav_links)
        self.assertNotIn(add_voucher_url, nav_links)
        self.assertIn("Kelola Voucher", nav_links)
        self.assertContains(response, "Dashboard Admin")

    def test_staff_with_view_permission_sees_voucher_catalog_link(self):
        staff_user = get_user_model().objects.create_user(
            username="voucher-viewer",
            email="voucher-viewer@example.com",
            password="test-password",
            is_staff=True,
        )
        view_permission = Permission.objects.get(
            content_type__app_label="rewards",
            codename="view_reward",
        )
        staff_user.user_permissions.add(view_permission)
        self.client.force_login(staff_user)

        response = self.client.get(reverse("profiles:overview"))
        nav_links = response.content.decode().split('<nav class="rb-drawer__nav">', 1)[1].split("</nav>", 1)[0]

        self.assertIn(reverse("rewards:admin_vouchers"), nav_links)
        self.assertNotIn(reverse("rewards:admin_voucher_add"), nav_links)

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
