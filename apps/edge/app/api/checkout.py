from fastapi import APIRouter, HTTPException

from infra.db import get_conn
from infra.totals import compute_cart_totals
from infra.outbox import insert_outbox_event


router = APIRouter()


@router.post("/carts/{cart_id}/checkout", status_code=201)
def checkout_cart(cart_id: str):
    """
    Checkout in one DB transaction:
    - lock the cart row
    - read cart lines
    - create order
    - create order_lines
    - write outbox event (same txn)
    - mark cart as checked_out

    For now, order status is 'paid' and tax=0 (same as Batch 3).
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        outbox_row = None

        # Lock the cart to avoid double-checkout.
        cur.execute(
            """
            SELECT id, status
            FROM carts
            WHERE id = %s
            FOR UPDATE;
            """,
            (cart_id,),
        )
        cart = cur.fetchone()
        if cart is None:
            raise HTTPException(status_code=404, detail="cart not found")

        if cart["status"] != "open":
            raise HTTPException(status_code=400, detail="cart is not open")

        # Read cart lines with product snapshot data
        cur.execute(
            """
            SELECT
              cl.product_id,
              p.barcode,
              p.name,
              cl.qty,
              cl.unit_price_cents,
              cl.currency
            FROM cart_lines cl
            JOIN products p ON p.id = cl.product_id
            WHERE cl.cart_id = %s
            ORDER BY p.name ASC;
            """,
            (cart_id,),
        )
        lines = cur.fetchall()
        if lines is None:
            lines = []

        if len(lines) == 0:
            raise HTTPException(status_code=400, detail="cart is empty")

        # Compute totals (tax=0 placeholder)
        totals = compute_cart_totals(lines)

        # Currency: take from first line (we enforce single currency later if needed)
        currency = lines[0]["currency"]

        # Create order
        cur.execute(
            """
            INSERT INTO orders (cart_id, status, currency, subtotal_cents, tax_cents, total_cents)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, cart_id, status, currency, subtotal_cents, tax_cents, total_cents, created_at;
            """,
            (
                cart_id,
                "paid",
                currency,
                totals["subtotal_cents"],
                totals["tax_cents"],
                totals["total_cents"],
            ),
        )
        order = cur.fetchone()

        # Insert order_lines
        i = 0
        while i < len(lines):
            line = lines[i]
            qty = int(line["qty"])
            unit_price_cents = int(line["unit_price_cents"])
            line_total_cents = qty * unit_price_cents

            cur.execute(
                """
                INSERT INTO order_lines
                  (order_id, product_id, barcode, name, qty, unit_price_cents, line_total_cents)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    order["id"],
                    line["product_id"],
                    line["barcode"],
                    line["name"],
                    qty,
                    unit_price_cents,
                    line_total_cents,
                ),
            )

            i = i + 1

        # ---- Batch 10 addition: include line items in outbox payload ----
        payload_lines = []
        j = 0
        while j < len(lines):
            ln = lines[j]
            qty = int(ln["qty"])
            unit_price_cents = int(ln["unit_price_cents"])

            payload_lines.append(
                {
                    "product_id": str(ln["product_id"]),
                    "barcode": ln["barcode"],
                    "name": ln["name"],
                    "qty": qty,
                    "unit_price_cents": unit_price_cents,
                    "line_total_cents": qty * unit_price_cents,
                }
            )

            j = j + 1
        # ---------------------------------------------------------------

        # Write outbox event in the SAME transaction
        payload = {
            "order_id": str(order["id"]),
            "cart_id": str(cart_id),
            "currency": str(currency),
            "subtotal_cents": int(totals["subtotal_cents"]),
            "tax_cents": int(totals["tax_cents"]),
            "total_cents": int(totals["total_cents"]),
            "lines": payload_lines,  # Batch 10: for cloud product reports
        }

        outbox_row = insert_outbox_event(
            cur=cur,
            event_type="order.paid",
            aggregate_type="order",
            aggregate_id=order["id"],
            payload_dict=payload,
        )

        # Mark cart as checked_out (lock it)
        cur.execute(
            """
            UPDATE carts
            SET status = 'checked_out'
            WHERE id = %s;
            """,
            (cart_id,),
        )

        conn.commit()

        # Return order + lines + outbox for confirmation
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, cart_id, status, currency, subtotal_cents, tax_cents, total_cents, created_at
            FROM orders
            WHERE id = %s;
            """,
            (order["id"],),
        )
        order_row = cur.fetchone()

        cur.execute(
            """
            SELECT barcode, name, qty, unit_price_cents, line_total_cents
            FROM order_lines
            WHERE order_id = %s
            ORDER BY name ASC;
            """,
            (order["id"],),
        )
        order_lines = cur.fetchall()
        if order_lines is None:
            order_lines = []

        return {
            "order": order_row,
            "lines": order_lines,
            "outbox": outbox_row,
        }

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
