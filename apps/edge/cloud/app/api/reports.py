import json
from fastapi import APIRouter, HTTPException

from infra.db import get_conn

router = APIRouter()


def parse_payload(payload_json):
    return json.loads(payload_json)


@router.get("/reports/sales/daily")
def sales_daily(days: int = 7):
    """
    Daily sales totals for last N days.
    Uses event created_at date and payload total_cents.
    """
    if days <= 0:
        raise HTTPException(status_code=400, detail="days must be > 0")
    if days > 365:
        days = 365

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT created_at, payload_json
            FROM cloud_inbox_events
            WHERE event_type = 'order.paid'
              AND created_at >= (now() - (%s || ' days')::interval)
            ORDER BY created_at ASC;
            """,
            (days,),
        )

        rows = cur.fetchall()
        if rows is None:
            rows = []

        # Aggregate by YYYY-MM-DD
        totals = {}
        i = 0
        while i < len(rows):
            r = rows[i]
            created_at = str(r["created_at"])
            day = created_at[0:10]  # YYYY-MM-DD

            payload = parse_payload(r["payload_json"])
            total_cents = int(payload.get("total_cents", 0))

            if day not in totals:
                totals[day] = 0
            totals[day] = totals[day] + total_cents

            i = i + 1

        # Convert to sorted list
        days_list = list(totals.keys())
        days_list.sort()

        out = []
        j = 0
        while j < len(days_list):
            d = days_list[j]
            out.append({"day": d, "total_cents": totals[d]})
            j = j + 1

        return {"days": out}

    finally:
        if conn is not None:
            conn.close()


@router.get("/reports/sales/products")
def sales_by_product(limit: int = 50):
    """
    Product qty summary based on payload lines.
    Requires that edge sends lines[] in order.paid payload (Batch 10 change).
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
            SELECT payload_json
            FROM cloud_inbox_events
            WHERE event_type = 'order.paid'
            ORDER BY received_at DESC
            LIMIT 5000;
            """
        )
        rows = cur.fetchall()
        if rows is None:
            rows = []

        # Aggregate qty and revenue by barcode
        agg = {}

        i = 0
        while i < len(rows):
            payload = parse_payload(rows[i]["payload_json"])
            lines = payload.get("lines", [])
            if lines is None:
                lines = []

            j = 0
            while j < len(lines):
                ln = lines[j]
                barcode = str(ln.get("barcode", ""))
                name = str(ln.get("name", ""))
                qty = int(ln.get("qty", 0))
                line_total_cents = int(ln.get("line_total_cents", 0))

                if barcode != "":
                    if barcode not in agg:
                        agg[barcode] = {"barcode": barcode, "name": name, "qty": 0, "revenue_cents": 0}
                    agg[barcode]["qty"] = agg[barcode]["qty"] + qty
                    agg[barcode]["revenue_cents"] = agg[barcode]["revenue_cents"] + line_total_cents

                j = j + 1

            i = i + 1

        # Convert to list and sort by qty desc
        items = list(agg.values())
        items.sort(key=lambda x: x["qty"], reverse=True)

        # Limit results
        return {"top": items[:limit]}

    finally:
        if conn is not None:
            conn.close()


@router.get("/reports/orders/recent")
def recent_orders(limit: int = 20):
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be > 0")
    if limit > 200:
        limit = 200

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT device_id, outbox_event_id, aggregate_id, created_at, received_at, payload_json
            FROM cloud_inbox_events
            WHERE event_type = 'order.paid'
            ORDER BY received_at DESC
            LIMIT %s;
            """,
            (limit,),
        )
        rows = cur.fetchall()
        if rows is None:
            rows = []

        # Provide lightweight decoded view
        out = []
        i = 0
        while i < len(rows):
            r = rows[i]
            payload = parse_payload(r["payload_json"])
            out.append(
                {
                    "device_id": r["device_id"],
                    "order_id": str(payload.get("order_id", "")),
                    "total_cents": int(payload.get("total_cents", 0)),
                    "created_at": str(r["created_at"]),
                    "received_at": str(r["received_at"]),
                }
            )
            i = i + 1

        return {"orders": out}
    finally:
        if conn is not None:
            conn.close()
