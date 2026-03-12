-- Sync state: minimal progress markers for debugging/ops
CREATE TABLE IF NOT EXISTS sync_state (
  id INTEGER PRIMARY KEY,
  last_push_at TIMESTAMPTZ NULL,
  last_error TEXT NOT NULL DEFAULT ''
);

INSERT INTO sync_state (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- Mock cloud storage (temporary, for Batch 7 verification)
CREATE TABLE IF NOT EXISTS mock_cloud_received (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id TEXT NOT NULL,
  outbox_event_id UUID NOT NULL,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT mock_cloud_received_unique UNIQUE (device_id, outbox_event_id)
);

CREATE INDEX IF NOT EXISTS idx_mock_cloud_received_received_at
ON mock_cloud_received(received_at);
