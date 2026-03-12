-- Local dispatch tracking for outbox events
-- sent_at is for cloud sync later; local_processed_at is for in-device module processing.

ALTER TABLE outbox_events
ADD COLUMN IF NOT EXISTS local_processed_at TIMESTAMPTZ NULL;

ALTER TABLE outbox_events
ADD COLUMN IF NOT EXISTS local_error TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_outbox_local_unprocessed
ON outbox_events (created_at)
WHERE local_processed_at IS NULL;

-- Module handler idempotency log:
-- If the same event is dispatched again, handlers should not re-apply side effects.

CREATE TABLE IF NOT EXISTS module_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  module_name TEXT NOT NULL,
  outbox_event_id UUID NOT NULL REFERENCES outbox_events(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  status TEXT NOT NULL, -- 'ok' or 'error'
  error TEXT NOT NULL DEFAULT '',
  handled_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT module_events_unique UNIQUE (module_name, outbox_event_id)
);

CREATE INDEX IF NOT EXISTS idx_module_events_handled_at ON module_events (handled_at);
