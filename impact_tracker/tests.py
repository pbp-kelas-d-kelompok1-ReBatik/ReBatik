from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from upcycling.models import UpcyclingRequest

from .services import get_personal_stats, get_upcycling_stats


class ImpactTrackerUpcyclingStatsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="impact-member",
            password="test-password",
        )

    def create_request(self, status, quantity=1):
        return UpcyclingRequest.objects.create(
            user=self.user,
            fabric=UpcyclingRequest.FabricType.DENIM,
            category="TAS",
            product="TOTE_BAG",
            delivery_method=UpcyclingRequest.DeliveryMethod.DROP_OFF,
            address="Depok",
            whatsapp="081234567890",
            status=status,
            quantity=quantity,
        )

    def test_upcycling_stats_use_current_workflow_statuses(self):
        self.create_request(UpcyclingRequest.Status.PENDING_ASSIGNMENT)
        self.create_request(UpcyclingRequest.Status.PENDING_REVIEW)
        self.create_request(UpcyclingRequest.Status.AWAITING_FABRIC)
        self.create_request(UpcyclingRequest.Status.IN_PROGRESS)
        self.create_request(UpcyclingRequest.Status.READY)
        self.create_request(UpcyclingRequest.Status.COMPLETED, quantity=2)

        stats = get_upcycling_stats()

        self.assertEqual(stats["pending"], 2)
        self.assertEqual(stats["processing"], 3)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["items_completed"], 2)

    def test_dashboard_loads_with_empty_donation_and_upcycling_tables(self):
        response = self.client.get(reverse("impact_tracker:dashboard"))

        self.assertEqual(response.status_code, 200)

    def test_personal_processing_count_includes_pending_and_active_stages(self):
        self.create_request(UpcyclingRequest.Status.PENDING_ASSIGNMENT)
        self.create_request(UpcyclingRequest.Status.AWAITING_APPROVAL)
        self.create_request(UpcyclingRequest.Status.IN_PROGRESS)
        self.create_request(UpcyclingRequest.Status.COMPLETED)
        self.create_request(UpcyclingRequest.Status.CANCELLED)

        stats = get_personal_stats(self.user)

        self.assertEqual(stats["processing"], 3)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["requests"], 4)
