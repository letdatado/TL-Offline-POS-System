from fastapi import APIRouter, HTTPException

from infra.db import get_conn
from infra.events import dispatch_one_outbox_event

router = APIRouter()


@router.post("/outbox/dispatch")
def dispatch_pending(limit: int = 25):
    """
    Dispatch locally unprocessed outbox events.
    This is a debug/manual endpoint for now.

    It will:
    - pick events where local_processed_at IS NULL
    - run handlers
    - set local_processed_at on success
    - set local_error on failure (and stop)
    """
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be > 0")
    if limit > 500:
        limit = 500

    conn = None
    processed = 0

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, event_type, aggregate_type, aggregate_id, payload_json, created_at, sent_at, local_processed_at, local_error
            FROM outbox_events
            WHERE local_processed_at IS NULL
            ORDER BY created_at ASC
            LIMIT %s
            FOR UPDATE SKIP LOCKED;
            """,
            (limit,),
        )

        rows = cur.fetchall()
        if rows is None:
            rows = []

        i = 0
        while i < len(rows):
            ev = rows[i]

            try:
                dispatch_one_outbox_event(cur, ev)

                cur.execute(
                    """
                    UPDATE outbox_events
                    SET local_processed_at = now(),
                        local_error = NULL
                    WHERE id = %s;
                    """,
                    (ev["id"],),
                )

                processed = processed + 1

            except Exception as exc:
                # Mark error and stop processing further events in this run
                cur.execute(
                    """
                    UPDATE outbox_events
                    SET local_error = %s
                    WHERE id = %s;
                    """,
                    (str(exc), ev["id"]),
                )
                conn.commit()
                raise HTTPException(status_code=500, detail="dispatch failed: " + str(exc))

            i = i + 1

        conn.commit()
        return {"processed": processed}

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


@router.get("/module-events/recent")
def recent_module_events(limit: int = 50):
    """
    Inspect module handler logs.
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
            SELECT module_name, outbox_event_id, event_type, status, error, handled_at
            FROM module_events
            ORDER BY handled_at DESC
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
