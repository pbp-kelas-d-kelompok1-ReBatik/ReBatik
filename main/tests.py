from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class LoginRedirectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="rezky",
            password="password123",
        )

    def test_anonymous_navigation_shows_sign_in_and_sign_up(self):
        response = self.client.get(reverse("main:show_home"))

        self.assertContains(response, 'href="/login/">Sign in</a>')
        self.assertContains(response, 'href="/signup/">Sign up</a>')

        desktop_nav = response.content.decode().split(
            '<nav class="nav-links">',
            1,
        )[1].split("</nav>", 1)[0]
        item_positions = [
            desktop_nav.index(item)
            for item in ("Home", "Batik Story", "Sign in", "Sign up", "Reward")
        ]
        self.assertEqual(item_positions, sorted(item_positions))

    def test_authenticated_navigation_shows_username_and_logout(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("main:show_home"))

        self.assertContains(response, "rezky")
        self.assertContains(response, 'action="/logout/"')
        self.assertNotContains(response, ">Sign in</a>")
        self.assertNotContains(response, ">Sign up</a>")

    def test_dropdown_navigation_links_keep_order_for_guests_and_members(self):
        guest_response = self.client.get(reverse("main:show_home"))
        self.client.force_login(self.user)
        member_response = self.client.get(reverse("main:show_home"))

        menu_start = '<div class="nav-menu" id="navMenu">'
        guest_menu = guest_response.content.decode().split(menu_start, 1)[1].split(
            "</div>",
            1,
        )[0]
        member_menu = member_response.content.decode().split(menu_start, 1)[1].split(
            "</div>",
            1,
        )[0]

        labels_in_order = (
            "Profile",
            "MarketPlace",
            "Donasi Kain",
            "Drop-off Point",
            "Upcycling Request",
            "Custom Batik",
            "Impact Tracker",
            "Landing page",
        )
        for menu in (guest_menu, member_menu):
            positions = [menu.index(label) for label in labels_in_order]
            self.assertEqual(positions, sorted(positions))

        self.assertIn('href="#">Profile</a>', guest_menu)
        self.assertIn('href="#">Profile (rezky)</a>', member_menu)

    def test_hamburger_shows_auth_actions_for_guest_and_member(self):
        guest_response = self.client.get(reverse("main:show_home"))
        guest_menu = guest_response.content.decode().split(
            '<div class="nav-menu" id="navMenu">',
            1,
        )[1].split("</div>", 1)[0]

        self.assertIn('href="/login/">Sign in</a>', guest_menu)
        self.assertIn('href="/signup/">Sign up</a>', guest_menu)
        self.assertNotIn("Logout", guest_menu)

        self.client.force_login(self.user)
        member_response = self.client.get(reverse("main:show_home"))
        member_menu = member_response.content.decode().split(
            '<div class="nav-menu" id="navMenu">',
            1,
        )[1].split("</div>", 1)[0]

        self.assertIn('href="#">Profile (rezky)</a>', member_menu)
        self.assertNotIn("Masuk sebagai", member_menu)
        self.assertIn('action="/logout/" class="nav-menu-logout-form"', member_menu)
        self.assertIn('class="nav-menu-logout-button">Logout</button>', member_menu)
        self.assertNotIn('>Sign in</a>', member_menu)
        self.assertNotIn('>Sign up</a>', member_menu)

    def test_login_returns_user_to_safe_next_url(self):
        response = self.client.post(
            reverse("main:login"),
            {
                "username": "rezky",
                "password": "password123",
                "next": "/upcycling/new/",
            },
        )

        self.assertRedirects(
            response,
            "/upcycling/new/",
            fetch_redirect_response=False,
        )

    def test_login_rejects_external_next_url(self):
        response = self.client.post(
            reverse("main:login"),
            {
                "username": "rezky",
                "password": "password123",
                "next": "https://malicious.example/",
            },
        )

        self.assertRedirects(
            response,
            reverse("main:show_home"),
            fetch_redirect_response=False,
        )
