-- Inventory movements (ledger-style)
-- Stock is derived from sum(qty_delta) per product.

CREATE TABLE IF NOT EXISTS inventory_movements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL REFERENCES products(id),
  reason TEXT NOT NULL, -- 'receive', 'sale', 'adjust'
  qty_delta INTEGER NOT NULL, -- negative for sale
  ref_type TEXT NOT NULL DEFAULT '', -- e.g. 'order'
  ref_id UUID NULL,              -- e.g. order_id
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_inventory_movements_product_id
ON inventory_movements(product_id);

CREATE INDEX IF NOT EXISTS idx_inventory_movements_ref
ON inventory_movements(ref_type, ref_id);
