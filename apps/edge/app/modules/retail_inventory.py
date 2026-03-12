from infra.inventory import insert_movement


def handle_order_paid(cur, outbox_event_row, payload):
    """
    Retail module:
    When an order is paid, subtract inventory based on order_lines.

    We read order_lines from the local edge DB (they exist from Batch 4).
    """
    order_id = payload.get("order_id", "")
    if order_id == "":
        raise Exception("payload missing order_id")

    # Fetch order lines
    cur.execute(
        """
        SELECT product_id, qty
        FROM order_lines
        WHERE order_id = %s;
        """,
        (order_id,),
    )
    lines = cur.fetchall()
    if lines is None:
        lines = []

    if len(lines) == 0:
        # This should not happen, but keep it safe
        raise Exception("no order_lines found for order_id " + str(order_id))

    # For each line, record a SALE movement (negative delta)
    i = 0
    while i < len(lines):
        line = lines[i]
        product_id = line["product_id"]
        qty = int(line["qty"])

        # qty_delta is negative for sale
        insert_movement(
            cur=cur,
            product_id=product_id,
            reason="sale",
            qty_delta=(0 - qty),
            ref_type="order",
            ref_id=order_id,
        )

        i = i + 1


handle_order_paid._module_name = "retail-inventory"
