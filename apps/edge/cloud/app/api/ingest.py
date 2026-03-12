from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from infra.db import get_conn
from infra.auth import require_ingest_api_key
from infra.auth_devices import require_device_auth_and_rate_limit

router = APIRouter()


class IngestEvent(BaseModel):
    id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload_json: str
    created_at: str


class IngestBody(BaseModel):
    device_id: str
    events: list[IngestEvent]


@router.post("/ingest")
def ingest(
    body: IngestBody,
    _guard=Depends(require_device_auth_and_rate_limit),
):
    """
    Real cloud ingest:
    - idempotent insert per (device_id, outbox_event_id)
    - returns acked_ids so edge can mark sent_at
    """
    # Ensure body.device_id matches authenticated header device_id
    if body.device_id is None:
        raise HTTPException(status_code=400, detail="device_id is required")

    body_did = body.device_id.strip()
    if body_did == "":
        raise HTTPException(status_code=400, detail="device_id is required")

    if body_did != _guard["device_id"]:
        raise HTTPException(status_code=400, detail="device_id mismatch")

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        acked_ids = []
        i = 0
        while i < len(body.events):
            ev = body.events[i]

            # Insert idempotently
            cur.execute(
                """
                INSERT INTO cloud_inbox_events
                  (device_id, outbox_event_id, event_type, aggregate_type, aggregate_id, payload_json, created_at)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (device_id, outbox_event_id)
                DO NOTHING;
                """,
                (
                    body.device_id,
                    ev.id,
                    ev.event_type,
                    ev.aggregate_type,
                    ev.aggregate_id,
                    ev.payload_json,
                    ev.created_at,
                ),
            )

            # We ACK regardless (because idempotency means duplicates are safe)
            acked_ids.append(ev.id)
            i = i + 1

        conn.commit()
        return {"acked_ids": acked_ids}

    except Exception as exc:
        if conn is not None:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()


@router.get("/received/recent")
def received_recent(limit: int = 50):
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be > 0")
    if limit > 500:
        limit = 500

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT device_id, outbox_event_id, event_type, aggregate_type, aggregate_id, received_at
            FROM cloud_inbox_events
            ORDER BY received_at DESC
            LIMIT %s;
            """,
            (limit,),
        )
        rows = cur.fetchall()
        if rows is None:
            rows = []
        return {"recent": rows}
    finally:
        if conn is not None:
            conn.close()


@router.get("/received/by-device/{device_id}")
def received_by_device(device_id: str, limit: int = 50):
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be > 0")
    if limit > 500:
        limit = 500

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT outbox_event_id, event_type, aggregate_type, aggregate_id, received_at
            FROM cloud_inbox_events
            WHERE device_id = %s
            ORDER BY received_at DESC
            LIMIT %s;
            """,
            (device_id, limit),
        )
        rows = cur.fetchall()
        if rows is None:
            rows = []
        return {"device_id": device_id, "events": rows}
    finally:
        if conn is not None:
            conn.close()
