import psycopg
from psycopg.rows import dict_row

from infra.settings import settings


def get_conn():
    """
    Small helper to keep connection creation consistent.
    Autocommit is False by default; that's good for transactions.
    """
    conn = psycopg.connect(settings.POS_DB_DSN, row_factory=dict_row)
    return conn


def db_ping():
    """
    Fast, simple DB connectivity check.
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1 AS ok;")
        row = cur.fetchone()
        if row is None:
            return False, "no row from SELECT 1"
        return True, ""
    except Exception as exc:
        return False, str(exc)
    finally:
        if conn is not None:
            conn.close()
