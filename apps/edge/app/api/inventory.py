from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from infra.db import get_conn
from infra.inventory import get_stock_cents_and_qty, insert_movement

router = APIRouter()


class ReceiveStockBody(BaseModel):
    barcode: str
    qty: int


@router.post("/inventory/receive", status_code=201)
def receive_stock(body: ReceiveStockBody):
    if body.qty <= 0:
        raise HTTPException(status_code=400, detail="qty must be > 0")

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # Find product
        cur.execute(
            """
            SELECT id, barcode, name
            FROM products
            WHERE barcode = %s;
            """,
            (body.barcode,),
        )
        product = cur.fetchone()
        if product is None:
            raise HTTPException(status_code=404, detail="product not found")

        movement = insert_movement(
            cur=cur,
            product_id=product["id"],
            reason="receive",
            qty_delta=body.qty,
            ref_type="receive",
            ref_id=None,
        )

        conn.commit()
        return {"movement": movement}
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


@router.get("/inventory/stock/{barcode}")
def get_stock(barcode: str):
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, barcode, name
            FROM products
            WHERE barcode = %s;
            """,
            (barcode,),
        )
        product = cur.fetchone()
        if product is None:
            raise HTTPException(status_code=404, detail="product not found")

        qty = get_stock_cents_and_qty(cur, product["id"])

        return {
            "barcode": product["barcode"],
            "name": product["name"],
            "stock_qty": qty,
        }
    finally:
        if conn is not None:
            conn.close()
