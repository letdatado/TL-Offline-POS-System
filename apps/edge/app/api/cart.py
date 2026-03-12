from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from infra.db import get_conn
from infra.totals import compute_cart_totals

router = APIRouter()


class AddItemBody(BaseModel):
    barcode: str
    qty: int


class RemoveItemBody(BaseModel):
    barcode: str
    qty: int


@router.post("/carts", status_code=201)
def create_cart():
    """
    Create a new cart (open).
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO carts DEFAULT VALUES
            RETURNING id, status, created_at, updated_at;
            """
        )
        row = cur.fetchone()
        conn.commit()
        return row
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn is not None:
            conn.close()


@router.get("/carts/{cart_id}")
def get_cart(cart_id: str):
    """
    Get cart + lines + totals.
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, status, created_at, updated_at
            FROM carts
            WHERE id = %s;
            """,
            (cart_id,),
        )
        cart = cur.fetchone()
        if cart is None:
            raise HTTPException(status_code=404, detail="cart not found")

        cur.execute(
            """
            SELECT
              cl.id,
              cl.cart_id,
              cl.product_id,
              p.barcode,
              p.name,
              cl.qty,
              cl.unit_price_cents,
              cl.currency,
              cl.created_at,
              cl.updated_at
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

        # Add per-line total for convenience
        i = 0
        enriched_lines = []
        while i < len(lines):
            line = lines[i]
            qty = int(line["qty"])
            unit_price_cents = int(line["unit_price_cents"])
            line_total_cents = qty * unit_price_cents

            # Make a copy we can extend
            obj = dict(line)
            obj["line_total_cents"] = line_total_cents
            enriched_lines.append(obj)

            i = i + 1

        totals = compute_cart_totals(enriched_lines)

        return {
            "cart": cart,
            "items": enriched_lines,
            "totals": totals,
        }
    finally:
        if conn is not None:
            conn.close()


@router.post("/carts/{cart_id}/items", status_code=200)
def add_item(cart_id: str, body: AddItemBody):
    """
    Add/increase an item in the cart by barcode.

    Behavior:
    - Finds active product by barcode.
    - Upserts cart line by (cart_id, product_id).
    - Increases qty by body.qty.
    - Updates unit_price snapshot to current product price.
    """
    if body.qty <= 0:
        raise HTTPException(status_code=400, detail="qty must be > 0")

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # Ensure cart exists and open
        cur.execute("SELECT status FROM carts WHERE id = %s;", (cart_id,))
        cart = cur.fetchone()
        if cart is None:
            raise HTTPException(status_code=404, detail="cart not found")
        if cart["status"] != "open":
            raise HTTPException(status_code=400, detail="cart is not open")

        # Find product
        cur.execute(
            """
            SELECT id, barcode, name, price_cents, currency
            FROM products
            WHERE barcode = %s AND is_active = TRUE;
            """,
            (body.barcode,),
        )
        product = cur.fetchone()
        if product is None:
            raise HTTPException(status_code=404, detail="product not found or inactive")

        # Upsert line: increase qty
        cur.execute(
            """
            INSERT INTO cart_lines (cart_id, product_id, qty, unit_price_cents, currency)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (cart_id, product_id)
            DO UPDATE SET
              qty = cart_lines.qty + EXCLUDED.qty,
              unit_price_cents = EXCLUDED.unit_price_cents,
              currency = EXCLUDED.currency
            RETURNING id, cart_id, product_id, qty, unit_price_cents, currency, created_at, updated_at;
            """,
            (cart_id, product["id"], body.qty, product["price_cents"], product["currency"]),
        )
        line = cur.fetchone()
        conn.commit()

        return {
            "line": line,
            "product": {
                "barcode": product["barcode"],
                "name": product["name"],
            },
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


@router.post("/carts/{cart_id}/items/remove", status_code=200)
def remove_item(cart_id: str, body: RemoveItemBody):
    """
    Decrease qty; if qty becomes 0 or below, delete the line.
    """
    if body.qty <= 0:
        raise HTTPException(status_code=400, detail="qty must be > 0")

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # Ensure cart exists and open
        cur.execute("SELECT status FROM carts WHERE id = %s;", (cart_id,))
        cart = cur.fetchone()
        if cart is None:
            raise HTTPException(status_code=404, detail="cart not found")
        if cart["status"] != "open":
            raise HTTPException(status_code=400, detail="cart is not open")

        # Find product by barcode
        cur.execute(
            """
            SELECT id
            FROM products
            WHERE barcode = %s;
            """,
            (body.barcode,),
        )
        product = cur.fetchone()
        if product is None:
            raise HTTPException(status_code=404, detail="product not found")

        # Read existing line
        cur.execute(
            """
            SELECT id, qty
            FROM cart_lines
            WHERE cart_id = %s AND product_id = %s;
            """,
            (cart_id, product["id"]),
        )
        line = cur.fetchone()
        if line is None:
            raise HTTPException(status_code=404, detail="item not in cart")

        new_qty = int(line["qty"]) - int(body.qty)

        if new_qty > 0:
            cur.execute(
                """
                UPDATE cart_lines
                SET qty = %s
                WHERE id = %s
                RETURNING id, cart_id, product_id, qty, unit_price_cents, currency, created_at, updated_at;
                """,
                (new_qty, line["id"]),
            )
            updated = cur.fetchone()
            conn.commit()
            return {"line": updated, "action": "updated"}
        else:
            cur.execute("DELETE FROM cart_lines WHERE id = %s;", (line["id"],))
            conn.commit()
            return {"action": "deleted"}
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
