-- Carts + Cart lines
-- Snapshot pricing at time of add: unit_price_cents + currency on cart_lines.

CREATE TABLE IF NOT EXISTS carts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  status TEXT NOT NULL DEFAULT 'open',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cart_lines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cart_id UUID NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES products(id),
  qty INTEGER NOT NULL,
  unit_price_cents INTEGER NOT NULL,
  currency CHAR(3) NOT NULL DEFAULT 'PKR',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT cart_lines_qty_positive CHECK (qty > 0),
  CONSTRAINT cart_lines_price_non_negative CHECK (unit_price_cents >= 0),
  CONSTRAINT cart_lines_cart_product_unique UNIQUE (cart_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_cart_lines_cart_id ON cart_lines(cart_id);

-- Reuse the set_updated_at trigger function created in 0001.
-- If it doesn't exist for any reason, create it defensively.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'set_updated_at') THEN
    CREATE OR REPLACE FUNCTION set_updated_at()
    RETURNS TRIGGER AS $func$
    BEGIN
      NEW.updated_at = now();
      RETURN NEW;
    END;
    $func$ LANGUAGE plpgsql;
  END IF;
END $$;

DROP TRIGGER IF EXISTS trg_carts_updated_at ON carts;
CREATE TRIGGER trg_carts_updated_at
BEFORE UPDATE ON carts
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_cart_lines_updated_at ON cart_lines;
CREATE TRIGGER trg_cart_lines_updated_at
BEFORE UPDATE ON cart_lines
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
