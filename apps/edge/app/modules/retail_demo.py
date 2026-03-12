def handle_order_paid(cur, outbox_event_row, payload):
    """
    Demo module handler:
    For now, it just proves the module subscription mechanism works.
    In later batches (Retail module) this will create inventory movements, etc.
    """
    # Example: sanity-check required fields exist
    if "order_id" not in payload:
        raise Exception("payload missing order_id")

    # We do not change business state yet in demo.
    # The idempotency record is written by infra/events.py after this returns successfully.
    return


# Attach a module name for idempotency logging
handle_order_paid._module_name = "retail-demo"
