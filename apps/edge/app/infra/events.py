import json


# Global registry: event_type -> list of handlers
# Handler signature:
#   handler(cur, outbox_event_row, payload_dict)
_handlers = {}


def register_handler(event_type, handler_fn):
    """
    Register a handler for a given event type.
    """
    if event_type not in _handlers:
        _handlers[event_type] = []
    _handlers[event_type].append(handler_fn)


def get_handlers(event_type):
    if event_type not in _handlers:
        return []
    return _handlers[event_type]


def parse_payload(payload_json):
    """
    payload_json stored as TEXT in DB.
    """
    return json.loads(payload_json)


def ensure_module_event_row(cur, module_name, outbox_event_id, event_type, status, error_text):
    """
    Idempotency: (module_name, outbox_event_id) is unique.
    If already exists, do nothing.
    """
    cur.execute(
        """
        INSERT INTO module_events (module_name, outbox_event_id, event_type, status, error)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (module_name, outbox_event_id)
        DO NOTHING;
        """,
        (module_name, outbox_event_id, event_type, status, error_text),
    )


def module_event_already_ok(cur, module_name, outbox_event_id):
    cur.execute(
        """
        SELECT status
        FROM module_events
        WHERE module_name = %s AND outbox_event_id = %s;
        """,
        (module_name, outbox_event_id),
    )
    row = cur.fetchone()
    if row is None:
        return False
    if row["status"] == "ok":
        return True
    return False


def dispatch_one_outbox_event(cur, outbox_event_row):
    """
    Dispatch one outbox event to all registered handlers.
    Runs using the provided cursor, so this is transactional.
    """
    event_type = outbox_event_row["event_type"]
    payload_json = outbox_event_row["payload_json"]
    payload = parse_payload(payload_json)

    handlers = get_handlers(event_type)

    # If no handlers, we still consider it processed locally.
    i = 0
    while i < len(handlers):
        handler_fn = handlers[i]

        # Each handler must provide a name for idempotency logging
        module_name = getattr(handler_fn, "_module_name", "unknown-module")

        # If already handled OK, skip
        if module_event_already_ok(cur, module_name, outbox_event_row["id"]):
            i = i + 1
            continue

        try:
            handler_fn(cur, outbox_event_row, payload)
            ensure_module_event_row(
                cur=cur,
                module_name=module_name,
                outbox_event_id=outbox_event_row["id"],
                event_type=event_type,
                status="ok",
                error_text="",
            )
        except Exception as exc:
            # Record handler failure
            ensure_module_event_row(
                cur=cur,
                module_name=module_name,
                outbox_event_id=outbox_event_row["id"],
                event_type=event_type,
                status="error",
                error_text=str(exc),
            )
            # Re-raise so the caller can mark local_error and stop processing if desired
            raise

        i = i + 1
