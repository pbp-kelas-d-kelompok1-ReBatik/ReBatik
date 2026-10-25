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
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:  # Selenium is an optional development dependency.
    webdriver = None

from .models import UpcyclingRequest


@skipIf(webdriver is None, "Install requirements-dev.txt to run Selenium tests.")
class UpcyclingBrowserTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
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
        browser = getattr(cls, "browser", None)
        if browser:
            browser.quit()
        super().tearDownClass()

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="selenium-user",
            password="selenium-password",
        )
        self.client.force_login(self.user)

    def open_authenticated_page(self, path):
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
        self.browser.execute_script(
            "arguments[0].click();",
            element,
        )

    def get_result_headings(self):
        return self.browser.execute_script(
            "return Array.from(document.querySelectorAll(" 
            "'#request-results article h3')).map((heading) => heading.textContent.trim());"
        )

    def test_status_tabs_switch_from_completed_to_all(self):
        self.create_request(
            status=UpcyclingRequest.Status.PENDING,
            product="TOTE_BAG",
        )
        self.create_request(
            status=UpcyclingRequest.Status.COMPLETED,
            product="POUCH",
        )
        self.open_authenticated_page(reverse("upcycling:request_list"))

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
            lambda _browser: set(self.get_result_headings()) == {"Tote Bag", "Pouch"}
        )

    def test_delete_dialog_can_cancel_then_confirm_and_return_to_list(self):
        upcycling_request = self.create_request(
            status=UpcyclingRequest.Status.PENDING,
            product="TOTE_BAG",
        )
        self.open_authenticated_page(
            reverse("upcycling:request_detail", args=[upcycling_request.pk])
        )

        self.activate_by_dom_click(
            self.browser.find_element(By.CSS_SELECTOR, "[data-open-delete-dialog]")
        )
        dialog = self.browser.find_element(By.ID, "delete-request-dialog")
        self.assertTrue(dialog.is_displayed())
        dialog.find_element(By.CSS_SELECTOR, "[data-close-delete-dialog]").click()
        self.wait.until(lambda browser: not dialog.is_displayed())
        self.assertTrue(
            UpcyclingRequest.objects.filter(pk=upcycling_request.pk).exists()
        )

        self.activate_by_dom_click(
            self.browser.find_element(By.CSS_SELECTOR, "[data-open-delete-dialog]")
        )
        self.browser.find_element(
            By.CSS_SELECTOR,
            "#delete-request-dialog button[type='submit']",
        ).click()
        self.wait.until(
            lambda browser: browser.current_url
            == f"{self.live_server_url}{reverse('upcycling:request_list')}"
        )
        self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-upcycling-toast]"))
        )
        self.assertFalse(
            UpcyclingRequest.objects.filter(pk=upcycling_request.pk).exists()
        )
