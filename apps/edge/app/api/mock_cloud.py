from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from infra.db import get_conn

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


@router.post("/mock-cloud/ingest")
def mock_cloud_ingest(body: IngestBody):
    """
    Simulates cloud ingest:
    - stores each (device_id, outbox_event_id) idempotently
    - returns acked_ids
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        acked_ids = []
        i = 0
        while i < len(body.events):
            ev = body.events[i]

            # idempotent insert
            cur.execute(
                """
                INSERT INTO mock_cloud_received (device_id, outbox_event_id, event_type, payload_json)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (device_id, outbox_event_id)
                DO NOTHING;
                """,
                (body.device_id, ev.id, ev.event_type, ev.payload_json),
            )

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


@router.get("/mock-cloud/received")
def mock_cloud_received(limit: int = 50):
    """
    Debug: view what mock cloud has received.
    """
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
            SELECT device_id, outbox_event_id, event_type, received_at
            FROM mock_cloud_received
            ORDER BY received_at DESC
            LIMIT %s;
            """,
            (limit,),
        )
        rows = cur.fetchall()
        if rows is None:
            rows = []
        return {"received": rows}
    finally:
        if conn is not None:
            conn.close()
