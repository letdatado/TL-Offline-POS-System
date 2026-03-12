import time

from infra.settings import settings


# In-memory limiter: device_id -> state
# NOTE: This is per-process. If you run multiple workers, you'll want Redis later.
_state = {}


def _now_minute():
    return int(time.time() // 60)


def allow_request(device_id):
    """
    Simple fixed-window limiter per minute with burst.
    Returns (allowed: bool, remaining: int)
    """
    per_min = int(settings.CLOUD_RATE_LIMIT_PER_MIN)
    burst = int(settings.CLOUD_RATE_LIMIT_BURST)

    if per_min <= 0:
        per_min = 120
    if burst < 0:
        burst = 0

    limit = per_min + burst
    minute = _now_minute()

    s = _state.get(device_id)
    if s is None:
        s = {"minute": minute, "count": 0}
        _state[device_id] = s

    if s["minute"] != minute:
        s["minute"] = minute
        s["count"] = 0

    if s["count"] >= limit:
        return False, 0

    s["count"] = s["count"] + 1
    remaining = limit - s["count"]
    return True, remaining