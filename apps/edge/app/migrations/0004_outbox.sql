-- Transactional outbox for offline-first sync.
-- Written in the same transaction as the business change (checkout).

CREATE TABLE IF NOT EXISTS outbox_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,
  aggregate_type TEXT NOT NULL,
  aggregate_id UUID NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_outbox_unsent ON outbox_events (sent_at) WHERE sent_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_outbox_created ON outbox_events (created_at);
