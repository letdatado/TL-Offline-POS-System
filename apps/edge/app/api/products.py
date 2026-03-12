from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from infra.db import get_conn

router = APIRouter()


class ProductCreate(BaseModel):
    barcode: str
    name: str
    price_cents: int
    currency: str = "PKR"
    is_active: bool = True


@router.get("/products/{barcode}")
def get_product_by_barcode(barcode: str):
    """
    Lookup product by barcode (fast path).
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, barcode, name, price_cents, currency, is_active, created_at, updated_at
            FROM products
            WHERE barcode = %s;
            """,
            (barcode,),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="product not found")
        return row
    finally:
        if conn is not None:
            conn.close()


@router.post("/products", status_code=201)
def create_or_update_product(body: ProductCreate):
    """
    Upsert by barcode:
    - If barcode exists, update details.
    - Else insert.
    This is helpful for local catalog loading.
    """
    if body.price_cents < 0:
        raise HTTPException(status_code=400, detail="price_cents must be >= 0")

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO products (barcode, name, price_cents, currency, is_active)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (barcode)
            DO UPDATE SET
              name = EXCLUDED.name,
              price_cents = EXCLUDED.price_cents,
              currency = EXCLUDED.currency,
              is_active = EXCLUDED.is_active
            RETURNING id, barcode, name, price_cents, currency, is_active, created_at, updated_at;
            """,
            (body.barcode, body.name, body.price_cents, body.currency, body.is_active),
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
