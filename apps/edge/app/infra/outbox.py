import json


def insert_outbox_event(cur, event_type, aggregate_type, aggregate_id, payload_dict):
    """
    Insert an outbox event using an existing cursor.
    This MUST be called inside the same transaction as the business change.

    payload_dict will be JSON-serialized to text to keep it simple.
    """
    payload_json = json.dumps(payload_dict, ensure_ascii=False)

    cur.execute(
        """
        INSERT INTO outbox_events (event_type, aggregate_type, aggregate_id, payload_json)
        VALUES (%s, %s, %s, %s)
        RETURNING id, event_type, aggregate_type, aggregate_id, payload_json, created_at, sent_at;
        """,
        (event_type, aggregate_type, aggregate_id, payload_json),
    )
    row = cur.fetchone()
    return row
