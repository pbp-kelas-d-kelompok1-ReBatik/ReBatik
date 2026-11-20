from config.rate_limits import consume_user_rate_limit

from .models import UpcyclingRateLimitBucket


def consume_upcycling_rate_limit(user, action, *, limit, window_seconds):
    return consume_user_rate_limit(
        user, UpcyclingRateLimitBucket, action=action, limit=limit, window_seconds=window_seconds
    )
