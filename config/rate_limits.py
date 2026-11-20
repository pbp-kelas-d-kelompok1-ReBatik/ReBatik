from datetime import timedelta
from math import ceil

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.timezone import now


@transaction.atomic
def consume_user_rate_limit(user, bucket_model, *, limit, window_seconds, **bucket_fields):
    """Count an attempt in a fixed window shared by workers using the same database."""
    # The user row exists even when this is the account's first attempt.
    get_user_model().objects.select_for_update().only("pk").get(pk=user.pk)
    current_time = now()
    bucket, _ = bucket_model.objects.get_or_create(
        user=user, **bucket_fields, defaults={"window_started_at": current_time}
    )
    expires_at = bucket.window_started_at + timedelta(seconds=window_seconds)
    if current_time >= expires_at:
        bucket.window_started_at = current_time
        bucket.request_count = 0
    elif bucket.request_count >= limit:
        return False, ceil((expires_at - current_time).total_seconds())

    bucket.request_count += 1
    bucket.save(update_fields=["window_started_at", "request_count"])
    return True, 0
