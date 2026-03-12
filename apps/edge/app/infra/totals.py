def compute_cart_totals(lines):
    """
    Compute totals using simple loops.
    lines: list of dict rows containing at least qty and unit_price_cents.

    Tax is 0 in Batch 3 (placeholder for later tax engine integration).
    """
    subtotal_cents = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        qty = int(line["qty"])
        unit_price_cents = int(line["unit_price_cents"])
        subtotal_cents = subtotal_cents + (qty * unit_price_cents)
        i = i + 1

    tax_cents = 0
    total_cents = subtotal_cents + tax_cents

    return {
        "subtotal_cents": subtotal_cents,
        "tax_cents": tax_cents,
        "total_cents": total_cents,
    }
