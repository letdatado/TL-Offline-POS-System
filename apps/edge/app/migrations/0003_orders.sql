-- Orders + Order lines
-- An order is immutable. We snapshot prices into order_lines.

CREATE TABLE IF NOT EXISTS orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cart_id UUID NOT NULL UNIQUE REFERENCES carts(id),
  status TEXT NOT NULL DEFAULT 'paid',
  currency CHAR(3) NOT NULL DEFAULT 'PKR',
  subtotal_cents INTEGER NOT NULL,
  tax_cents INTEGER NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS order_lines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES products(id),
  barcode TEXT NOT NULL,
  name TEXT NOT NULL,
  qty INTEGER NOT NULL,
  unit_price_cents INTEGER NOT NULL,
  line_total_cents INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT order_lines_qty_positive CHECK (qty > 0),
  CONSTRAINT order_lines_price_non_negative CHECK (unit_price_cents >= 0),
  CONSTRAINT order_lines_line_total_non_negative CHECK (line_total_cents >= 0)
);

CREATE INDEX IF NOT EXISTS idx_order_lines_order_id ON order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_orders_cart_id ON orders(cart_id);
