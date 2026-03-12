from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from infra.db import get_conn

from uuid import UUID

router = APIRouter()


class AckBody(BaseModel):
    # Optional, but can be useful for later (cloud ack id, etc.)
    note: str = ""


@router.get("/outbox/pending")
def list_pending(limit: int = 50):
    """
    List unsent outbox events (debug endpoint).
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
            SELECT id, event_type, aggregate_type, aggregate_id, payload_json, created_at, sent_at
            FROM outbox_events
            WHERE sent_at IS NULL
            ORDER BY created_at ASC
            LIMIT %s;
            """,
            (limit,),
        )
        rows = cur.fetchall()
        if rows is None:
            rows = []
        return {"pending": rows}
    finally:
        if conn is not None:
            conn.close()


@router.post("/outbox/{event_id}/ack")
def ack_event(event_id: UUID, body: AckBody):
    """
    Mark a specific outbox event as sent.
    In later batches, this will be done by the sync worker after cloud ACK.
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE outbox_events
            SET sent_at = now()
            WHERE id = %s AND sent_at IS NULL
            RETURNING id, event_type, aggregate_type, aggregate_id, payload_json, created_at, sent_at;
            """,
            (event_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="event not found or already acked")

        conn.commit()
        return {"acked": row, "note": body.note}
    except HTTPException:
        if conn is not None:
            conn.rollback()
        raise
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()
