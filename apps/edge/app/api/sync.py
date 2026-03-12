from fastapi import APIRouter, HTTPException

from infra.db import get_conn
from infra.sync_push import push_outbox_batch

router = APIRouter()


@router.get("/sync/status")
def sync_status():
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) AS cnt FROM outbox_events WHERE sent_at IS NULL;")
        unsent = cur.fetchone()
        if unsent is None:
            unsent_count = 0
        else:
            unsent_count = int(unsent["cnt"])

        cur.execute("SELECT last_push_at, last_error FROM sync_state WHERE id = 1;")
        st = cur.fetchone()
        if st is None:
            st = {"last_push_at": None, "last_error": ""}

        return {
            "unsent_count": unsent_count,
            "last_push_at": st["last_push_at"],
            "last_error": st["last_error"],
        }
    finally:
        if conn is not None:
            conn.close()


@router.post("/sync/push")
def sync_push(limit: int = 50):
    ok, err, acked_count, acked_ids = push_outbox_batch(limit)
    if not ok:
        raise HTTPException(status_code=502, detail=err)

    return {
        "acked_count": acked_count,
        "acked_ids": acked_ids,
    }
