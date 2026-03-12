CREATE TABLE IF NOT EXISTS cloud_inbox_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id TEXT NOT NULL,
  outbox_event_id UUID NOT NULL,
  event_type TEXT NOT NULL,
  aggregate_type TEXT NOT NULL,
  aggregate_id UUID NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT cloud_inbox_unique UNIQUE (device_id, outbox_event_id)
);

CREATE INDEX IF NOT EXISTS idx_cloud_inbox_received_at
ON cloud_inbox_events(received_at);

CREATE INDEX IF NOT EXISTS idx_cloud_inbox_device
ON cloud_inbox_events(device_id);

CREATE INDEX IF NOT EXISTS idx_cloud_inbox_event_type
ON cloud_inbox_events(event_type);
