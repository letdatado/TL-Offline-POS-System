def get_stock_cents_and_qty(cur, product_id):
    """
    Returns current stock qty for a product.
    """
    cur.execute(
        """
        SELECT COALESCE(SUM(qty_delta), 0) AS qty
        FROM inventory_movements
        WHERE product_id = %s;
        """,
        (product_id,),
    )
    row = cur.fetchone()
    if row is None:
        return 0
    return int(row["qty"])


def insert_movement(cur, product_id, reason, qty_delta, ref_type, ref_id):
    cur.execute(
        """
        INSERT INTO inventory_movements (product_id, reason, qty_delta, ref_type, ref_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, product_id, reason, qty_delta, ref_type, ref_id, created_at;
        """,
        (product_id, reason, qty_delta, ref_type, ref_id),
    )
    return cur.fetchone()
