import os

from infra.db import get_conn


def ensure_schema_migrations_table(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          filename TEXT PRIMARY KEY,
          applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )


def migration_applied(cur, filename):
    cur.execute(
        "SELECT 1 FROM schema_migrations WHERE filename = %s;",
        (filename,),
    )
    row = cur.fetchone()
    if row is None:
        return False
    return True


def mark_migration_applied(cur, filename):
    cur.execute(
        "INSERT INTO schema_migrations (filename) VALUES (%s);",
        (filename,),
    )


def read_sql_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def apply_migrations(migrations_dir):
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        ensure_schema_migrations_table(cur)
        conn.commit()

        files = os.listdir(migrations_dir)

        sql_files = []
        i = 0
        while i < len(files):
            name = files[i]
            if name.endswith(".sql"):
                sql_files.append(name)
            i = i + 1

        sql_files.sort()

        j = 0
        while j < len(sql_files):
            filename = sql_files[j]

            if migration_applied(cur, filename):
                j = j + 1
                continue

            full_path = os.path.join(migrations_dir, filename)
            sql = read_sql_file(full_path)

            cur.execute(sql)
            mark_migration_applied(cur, filename)
            conn.commit()

            j = j + 1

        return True, ""
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        return False, str(exc)
    finally:
        if conn is not None:
            conn.close()
