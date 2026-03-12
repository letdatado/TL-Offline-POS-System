import json

from infra.db import get_conn
from infra.settings import settings
from infra.sync_client import post_json


def fetch_unsent_outbox(cur, limit):
    cur.execute(
        """
        SELECT id, event_type, aggregate_type, aggregate_id, payload_json, created_at
        FROM outbox_events
        WHERE sent_at IS NULL
        ORDER BY created_at ASC, id ASC
        LIMIT %s;
        """,
        (limit,),
    )
    rows = cur.fetchall()
    if rows is None:
        return []
    return rows


def mark_events_sent(cur, event_ids):
    """
    Mark sent_at for given IDs.
    """
    i = 0
    while i < len(event_ids):
        eid = event_ids[i]
        cur.execute(
            """
            UPDATE outbox_events
            SET sent_at = now()
            WHERE id = %s;
            """,
            (eid,),
        )
        i = i + 1


def update_sync_state(cur, last_error_text):
    cur.execute(
        """
        UPDATE sync_state
        SET last_push_at = now(),
            last_error = %s
        WHERE id = 1;
        """,
        (last_error_text,),
    )


def push_outbox_batch(limit):
    """
    - Read unsent outbox events from DB
    - POST them to cloud ingest endpoint
    - On ack, mark sent_at
    """
    if limit <= 0:
        return False, "limit must be > 0", 0, []

    if limit > 500:
        limit = 500

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        events = fetch_unsent_outbox(cur, limit)

        if len(events) == 0:
            update_sync_state(cur, "")
            conn.commit()
            return True, "", 0, []

        # Build payload
        payload_events = []
        i = 0
        while i < len(events):
            ev = events[i]
            payload_events.append(
                {
                    "id": str(ev["id"]),
                    "event_type": ev["event_type"],
                    "aggregate_type": ev["aggregate_type"],
                    "aggregate_id": str(ev["aggregate_id"]),
                    "payload_json": ev["payload_json"],
                    "created_at": str(ev["created_at"]),
                }
            )
            i = i + 1

        payload = {
            "device_id": settings.POS_DEVICE_ID,
            "events": payload_events,
        }

        ingest_url = settings.POS_CLOUD_URL.rstrip("/") + "/ingest"

        headers = {}

        # Required now
        headers["X-Device-Id"] = settings.POS_DEVICE_ID.strip()

        api_key = settings.POS_CLOUD_API_KEY
        if api_key is None:
            api_key = ""
        api_key = api_key.strip()
        if api_key != "":
            headers["X-API-Key"] = api_key

        ok, status_code, resp_text = post_json(ingest_url, payload, headers_dict=headers)

        if not ok:
            # store error for visibility
            update_sync_state(cur, "HTTP " + str(status_code) + ": " + resp_text)
            conn.commit()
            return False, resp_text, 0, []

        # Expect response JSON: {"acked_ids":[...]}
        resp_obj = json.loads(resp_text)
        acked_ids = resp_obj.get("acked_ids", [])
        if acked_ids is None:
            acked_ids = []

        # Mark sent
        mark_events_sent(cur, acked_ids)

        update_sync_state(cur, "")
        conn.commit()

        return True, "", len(acked_ids), acked_ids

    except Exception as exc:
        if conn is not None:
            conn.rollback()
        # best effort store error
        try:
            if conn is None:
                conn = get_conn()
            cur2 = conn.cursor()
            update_sync_state(cur2, str(exc))
            conn.commit()
        except Exception:
            pass

        return False, str(exc), 0, []
    finally:
        if conn is not None:
            conn.close()
