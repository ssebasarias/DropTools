import os
import json
import sys

DB_NAME = os.environ.get('POSTGRES_DB','dahell_db')
DB_USER = os.environ.get('POSTGRES_USER','dahell_admin')
<<<<<<< HEAD
DB_PASS = os.environ.get('POSTGRES_PASSWORD','secure_password_123')
DB_HOST = os.environ.get('POSTGRES_HOST','127.0.0.1')
DB_PORT = int(os.environ.get('POSTGRES_PORT','5433'))

=======
DB_PASS = os.environ.get('POSTGRES_PASSWORD')
DB_HOST = os.environ.get('POSTGRES_HOST','127.0.0.1')
DB_PORT = int(os.environ.get('POSTGRES_PORT','5433'))

if not DB_PASS:
    print("ERROR: POSTGRES_PASSWORD is not set in environment. Aborting.")
    sys.exit(2)

>>>>>>> feature/rename-workers
try:
    import pg8000
    conn = pg8000.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, database=DB_NAME, password=DB_PASS)
    cur = conn.cursor()
    cur.execute("SHOW server_encoding;")
    enc = cur.fetchone()[0]

    cur.execute("SELECT extname FROM pg_extension ORDER BY extname;")
    exts = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;")
    tables = cur.fetchall()

    out = {"server_encoding": enc, "extensions": exts, "tables": {}}

    for schema, tbl in tables:
        cur.execute(
            """
            SELECT column_name, data_type, udt_name, character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_schema=%s AND table_name=%s
            ORDER BY ordinal_position
            """,
            (schema, tbl)
        )
        cols = [
            {
                "column_name": r[0],
                "data_type": r[1],
                "udt_name": r[2],
                "char_max_length": r[3],
                "is_nullable": r[4]
            }
            for r in cur.fetchall()
        ]
        out["tables"][f"{schema}.{tbl}"] = cols

    print(json.dumps(out, ensure_ascii=False, indent=2))
    cur.close()
    conn.close()
except Exception as e:
    import traceback
    print('ERROR:', e)
    traceback.print_exc()
    sys.exit(2)
