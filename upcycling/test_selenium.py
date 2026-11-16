from unittest import SkipTest, skipIf

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse

try:
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:  # Selenium is an optional development dependency.
    webdriver = None

from .models import UpcyclingRequest


@skipIf(webdriver is None, "Install requirements-dev.txt to run Selenium tests.")
class UpcyclingBrowserTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        """Start the shared browser fixture for this test class."""
        super().setUpClass()
        if webdriver is None:
            raise SkipTest("Install requirements-dev.txt to run Selenium tests.")

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1280,1000")
        try:
            cls.browser = webdriver.Chrome(options=options)
        except WebDriverException as error:
            raise SkipTest(f"Chrome WebDriver is unavailable: {error}") from error

        cls.wait = WebDriverWait(cls.browser, 10)

    @classmethod
    def tearDownClass(cls):
        """Close the shared browser fixture after this test class."""
        browser = getattr(cls, "browser", None)
        if browser:
            browser.quit()
        super().tearDownClass()

    def setUp(self):
        """Create the user fixture required by this test."""
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="selenium-user",
            password="selenium-password",
        )
        self.client.force_login(self.user)

    def open_authenticated_page(self, path):
        """Open a page in the browser with the test user session."""
        self.browser.get(self.live_server_url)
        session_cookie = self.client.cookies[settings.SESSION_COOKIE_NAME]
        self.browser.add_cookie(
            {
                "name": settings.SESSION_COOKIE_NAME,
                "value": session_cookie.value,
                "path": "/",
            }
        )
        self.browser.get(f"{self.live_server_url}{path}")

    def create_request(self, *, status, product):
        """Create a request fixture with the requested status and product."""
        return UpcyclingRequest.objects.create(
            user=self.user,
            fabric="PARANG",
            category="TAS" if product == "TOTE_BAG" else "POUCH",
            product=product,
            quantity=1,
            delivery_method="DROP_OFF",
            address="Depok",
            whatsapp="081234567890",
            status=status,
        )

    def activate_by_dom_click(self, element):
        """Activate an element through the browser DOM."""
        self.browser.execute_script(
            "arguments[0].click();",
            element,
        )

    def get_result_headings(self):
        """Return the product headings currently shown in the results."""
        return self.browser.execute_script(
            "return Array.from(document.querySelectorAll(" 
            "'#request-results article h3')).map((heading) => heading.textContent.trim());"
        )

    def test_status_tabs_switch_from_completed_to_all(self):
        """Test behavior: status tabs switch from completed to all."""
        self.create_request(
            status=UpcyclingRequest.Status.PENDING,
            product="POUCH",
        )
        self.create_request(
            status=UpcyclingRequest.Status.COMPLETED,
            product="POUCH",
        )
        self.create_request(
            status=UpcyclingRequest.Status.COMPLETED,
            product="TOTE_BAG",
        )
        self.open_authenticated_page(reverse("upcycling:request_list"))

        self.browser.find_element(
            By.CSS_SELECTOR,
            "#upcycling-extra-filters > summary",
        ).click()
        search = self.browser.find_element(By.ID, "filter-query")
        search.send_keys("Pouch")
        self.wait.until(lambda _browser: len(self.get_result_headings()) == 2)
        Select(self.browser.find_element(By.ID, "filter-category")).select_by_value("POUCH")
        self.wait.until(
            lambda browser: "category=POUCH" in browser.current_url
            and "q=Pouch" in browser.current_url
        )

        self.browser.find_element(
            By.CSS_SELECTOR,
            '[data-status-filter="COMPLETED"]',
        ).click()
        self.wait.until(
            lambda _browser: self.get_result_headings() == ["Pouch"]
        )

        self.browser.find_element(
            By.CSS_SELECTOR,
            '[data-status-filter=""]',
        ).click()
        self.wait.until(
            lambda _browser: self.get_result_headings().count("Pouch") == 2
        )

    def test_pagination_url_tracks_live_filter_values(self):
        """Test behavior: pagination links track filters before results swap."""
        for _ in range(11):
            self.create_request(
                status=UpcyclingRequest.Status.PENDING,
                product="POUCH",
            )
        self.open_authenticated_page(reverse("upcycling:request_list"))
        self.browser.find_element(
            By.CSS_SELECTOR,
            "#upcycling-extra-filters > summary",
        ).click()

        pagination_link = self.browser.find_element(
            By.CSS_SELECTOR,
            '#request-results nav[aria-label="Navigasi halaman permintaan"] a',
        )
        parsed_url, href, hx_get = self.browser.execute_script(
            """
            const input = document.getElementById('filter-query');
            input.value = 'Pouch';
            input.dispatchEvent(new Event('input', { bubbles: true }));

            const link = arguments[0];
            return [
                new URL(link.href, window.location.href).searchParams.toString(),
                link.getAttribute("href"),
                link.getAttribute("hx-get"),
            ];
            """,
            pagination_link,
        )
        self.assertIn("q=Pouch", parsed_url)
        self.assertIn("page=2", parsed_url)
        self.assertEqual(href, hx_get)

    def test_submitted_request_has_cancel_action_without_delete_dialog(self):
        """Test behavior: submitted request offers cancellation, not deletion."""
        upcycling_request = self.create_request(
            status=UpcyclingRequest.Status.PENDING_ASSIGNMENT,
            product="TOTE_BAG",
        )
        self.open_authenticated_page(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )

        self.assertIn("Batalkan permintaan", self.browser.find_element(By.TAG_NAME, "body").text)
        self.assertNotIn("Hapus permintaan", self.browser.find_element(By.TAG_NAME, "body").text)
        self.assertEqual(
            self.browser.find_elements(By.ID, "delete-request-dialog"),
            [],
        )
        self.assertTrue(
            UpcyclingRequest.objects.filter(pk=upcycling_request.pk).exists()
        )
