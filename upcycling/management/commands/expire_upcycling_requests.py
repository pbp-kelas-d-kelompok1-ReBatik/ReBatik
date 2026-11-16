from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from upcycling.models import UpcyclingRequest, UpcyclingStatusHistory


class Command(BaseCommand):
    help = "Mark fabric handoff requests as expired after their deadline."

    def handle(self, *args, **options):
        """Expire overdue fabric handoffs with no recorded receipt and record history."""
        now = timezone.now()
        expired_count = 0
        candidates = UpcyclingRequest.objects.filter(
            status=UpcyclingRequest.Status.AWAITING_FABRIC,
            fabric_deadline__lte=now,
            fabric_received_at__isnull=True,
        )
        for candidate_id in candidates.values_list("pk", flat=True).iterator():
            with transaction.atomic():
                request_obj = UpcyclingRequest.objects.select_for_update().get(pk=candidate_id)
                if (
                    request_obj.status != UpcyclingRequest.Status.AWAITING_FABRIC
                    or request_obj.fabric_received_at
                    or not request_obj.fabric_deadline
                    or request_obj.fabric_deadline > now
                ):
                    continue
                old_status = request_obj.status
                request_obj.status = UpcyclingRequest.Status.EXPIRED
                request_obj.save(update_fields=("status", "updated_at"))
                UpcyclingStatusHistory.objects.create(
                    request=request_obj,
                    from_status=old_status,
                    to_status=request_obj.status,
                )
                expired_count += 1
        self.stdout.write(self.style.SUCCESS(f"Marked {expired_count} request(s) expired."))
