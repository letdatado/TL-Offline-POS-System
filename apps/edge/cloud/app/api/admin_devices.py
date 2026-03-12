from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from infra.db import get_conn
from infra.auth_devices import require_admin_key

router = APIRouter()


class DeviceUpsertBody(BaseModel):
    device_id: str
    api_key_current: str
    is_active: bool = True


class RotateKeyBody(BaseModel):
    api_key_next: str
    # minutes until next key becomes valid (grace scheduling)
    next_valid_in_minutes: int = 0
    # optional: expire current key in N minutes (if you want to force cutover)
    expire_current_in_minutes: int = 0


@router.post("/admin/devices/upsert")
def upsert_device(body: DeviceUpsertBody, _auth=Depends(require_admin_key)):
    did = body.device_id.strip()
    if did == "":
        raise HTTPException(status_code=400, detail="device_id is required")

    key = body.api_key_current.strip()
    if key == "":
        raise HTTPException(status_code=400, detail="api_key_current is required")

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO devices (device_id, is_active, api_key_current)
            VALUES (%s, %s, %s)
            ON CONFLICT (device_id)
            DO UPDATE SET
              is_active = EXCLUDED.is_active,
              api_key_current = EXCLUDED.api_key_current;
            """,
            (did, body.is_active, key),
        )
        conn.commit()
        return {"ok": True, "device_id": did}
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()


@router.post("/admin/devices/{device_id}/rotate")
def rotate_device_key(device_id: str, body: RotateKeyBody, _auth=Depends(require_admin_key)):
    did = device_id.strip()
    if did == "":
        raise HTTPException(status_code=400, detail="device_id is required")

    next_key = body.api_key_next.strip()
    if next_key == "":
        raise HTTPException(status_code=400, detail="api_key_next is required")

    nmin = int(body.next_valid_in_minutes)
    if nmin < 0:
        nmin = 0

    expire_min = int(body.expire_current_in_minutes)
    if expire_min < 0:
        expire_min = 0

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # Ensure device exists
        cur.execute("SELECT device_id FROM devices WHERE device_id = %s;", (did,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="device not found")

        # next_valid_from = now() + interval
        # current_valid_until = now() + interval (optional)
        if nmin == 0:
            cur.execute(
                """
                UPDATE devices
                SET api_key_next = %s,
                    next_valid_from = now()
                WHERE device_id = %s;
                """,
                (next_key, did),
            )
        else:
            cur.execute(
                """
                UPDATE devices
                SET api_key_next = %s,
                    next_valid_from = now() + (%s || ' minutes')::interval
                WHERE device_id = %s;
                """,
                (next_key, nmin, did),
            )

        if expire_min > 0:
            cur.execute(
                """
                UPDATE devices
                SET current_valid_until = now() + (%s || ' minutes')::interval
                WHERE device_id = %s;
                """,
                (expire_min, did),
            )

        conn.commit()
        return {"ok": True, "device_id": did, "next_valid_in_minutes": nmin, "expire_current_in_minutes": expire_min}
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


@router.post("/admin/devices/{device_id}/promote")
def promote_next_to_current(device_id: str, _auth=Depends(require_admin_key)):
    """
    Promotes next key to current, clears next key, clears current_valid_until.
    Use after you've updated the Edge device with the new key and verified it.
    """
    did = device_id.strip()
    if did == "":
        raise HTTPException(status_code=400, detail="device_id is required")

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT api_key_next
            FROM devices
            WHERE device_id = %s;
            """,
            (did,),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="device not found")

        next_key = row["api_key_next"]
        if next_key is None:
            next_key = ""
        next_key = next_key.strip()

        if next_key == "":
            raise HTTPException(status_code=400, detail="no next key set")

        cur.execute(
            """
            UPDATE devices
            SET api_key_current = api_key_next,
                api_key_next = '',
                next_valid_from = NULL,
                current_valid_until = NULL
            WHERE device_id = %s;
            """,
            (did,),
        )

        conn.commit()
        return {"ok": True, "device_id": did}
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