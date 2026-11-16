from datetime import timedelta
from math import ceil

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import UpcyclingRateLimitBucket


def consume_upcycling_rate_limit(user, action, *, limit, window_seconds):
    """Atomically consume one per-user action from a persistent fixed window."""
    now = timezone.now()
    window = timedelta(seconds=window_seconds)

    with transaction.atomic():
        # Serialize requests for the same account across database-backed workers.
        get_user_model().objects.select_for_update().only("pk").get(pk=user.pk)
        bucket, _ = UpcyclingRateLimitBucket.objects.get_or_create(
            user=user,
            action=action,
            defaults={"window_started_at": now},
        )

        if now >= bucket.window_started_at + window:
            bucket.window_started_at = now
            bucket.request_count = 0

        if bucket.request_count >= limit:
            retry_after = ceil(
                (bucket.window_started_at + window - now).total_seconds()
            )
            return False, max(retry_after, 1)

        bucket.request_count += 1
        bucket.save(update_fields=["window_started_at", "request_count"])

    return True, 0
