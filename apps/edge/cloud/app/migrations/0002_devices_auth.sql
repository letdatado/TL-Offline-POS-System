-- Devices table for per-device auth + rotation
CREATE TABLE IF NOT EXISTS devices (
  device_id TEXT PRIMARY KEY,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,

  api_key_current TEXT NOT NULL,
  api_key_next TEXT NOT NULL DEFAULT '',

  -- Rotation window:
  -- If api_key_next is set and now() >= next_valid_from, next key is accepted.
  next_valid_from TIMESTAMPTZ NULL,

  -- Optionally force current key expiry (rarely needed, but useful)
  current_valid_until TIMESTAMPTZ NULL,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Updated_at trigger (reuse if exists, else create)
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

DROP TRIGGER IF EXISTS trg_devices_updated_at ON devices;
CREATE TRIGGER trg_devices_updated_at
BEFORE UPDATE ON devices
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_devices_active ON devices(is_active);