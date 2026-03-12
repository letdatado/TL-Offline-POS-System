from fastapi import Header, HTTPException

from infra.db import get_conn
from infra.rate_limit import allow_request


def require_admin_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    from infra.settings import settings

    required = settings.CLOUD_ADMIN_API_KEY
    if required is None:
        required = ""
    required = required.strip()

    if required == "":
        # Dev mode (not recommended for public)
        return

    if x_admin_key is None:
        raise HTTPException(status_code=401, detail="missing admin key")

    if x_admin_key.strip() != required:
        raise HTTPException(status_code=401, detail="invalid admin key")


def _device_key_valid(device_row, api_key):
    """
    Accepts:
    - current key if not expired
    - next key if next_valid_from reached and next key is set
    """
    if api_key is None:
        return False

    key = api_key.strip()
    if key == "":
        return False

    # Must be active
    if device_row["is_active"] is False:
        return False

    # current key expiry (optional)
    current_until = device_row["current_valid_until"]
    if current_until is not None:
        # If expired, current key not valid anymore
        # We don't compare time here in python; let Postgres do it in query where possible.
        pass

    if key == device_row["api_key_current"]:
        return True

    next_key = device_row["api_key_next"]
    if next_key is None:
        next_key = ""
    next_key = next_key.strip()

    if next_key != "" and key == next_key:
        # Next key only valid after next_valid_from (if set)
        return True

    return False


def require_device_auth_and_rate_limit(
    device_id: str | None = Header(default=None, alias="X-Device-Id"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """
    Cloud ingest guard:
    - Device must exist + active
    - API key must match device current or next key (if rotation enabled)
    - Rate limit per device
    """
    if device_id is None or device_id.strip() == "":
        raise HTTPException(status_code=400, detail="missing X-Device-Id")

    did = device_id.strip()

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # Load device row
        cur.execute(
            """
            SELECT device_id, is_active, api_key_current, api_key_next, next_valid_from, current_valid_until
            FROM devices
            WHERE device_id = %s;
            """,
            (did,),
        )
        dev = cur.fetchone()
        if dev is None:
            raise HTTPException(status_code=401, detail="unknown device")

        # Validate key with time constraints in SQL for correctness:
        # - current key: allowed if (current_valid_until is null OR now() < current_valid_until)
        # - next key: allowed if (api_key_next != '' AND (next_valid_from is null OR now() >= next_valid_from))
        api_key = ""
        if x_api_key is not None:
            api_key = x_api_key.strip()

        cur.execute(
            """
            SELECT 1 AS ok
            FROM devices
            WHERE device_id = %s
              AND is_active = TRUE
              AND (
                (
                  api_key_current = %s
                  AND (current_valid_until IS NULL OR now() < current_valid_until)
                )
                OR
                (
                  api_key_next = %s
                  AND api_key_next <> ''
                  AND (next_valid_from IS NULL OR now() >= next_valid_from)
                )
              );
            """,
            (did, api_key, api_key),
        )
        okrow = cur.fetchone()
        if okrow is None:
            raise HTTPException(status_code=401, detail="invalid device key")

        # Rate limit
        allowed, remaining = allow_request(did)
        if not allowed:
            raise HTTPException(status_code=429, detail="rate limit exceeded")

        # Return info for logging if needed
        return {"device_id": did, "remaining": remaining}

    finally:
        if conn is not None:
            conn.close()