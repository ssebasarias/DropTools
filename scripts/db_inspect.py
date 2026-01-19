import psycopg2
import json
import sys

# DB settings (mirar backend/dahell_backend/settings.py defaults)
<<<<<<< HEAD
DB_NAME = 'dahell_db'
DB_USER = 'dahell_admin'
DB_PASS = 'secure_password_123'
DB_HOST = '127.0.0.1'
DB_PORT = 5433
=======
import os

DB_NAME = os.environ.get('POSTGRES_DB', 'dahell_db')
DB_USER = os.environ.get('POSTGRES_USER', 'dahell_admin')
DB_PASS = os.environ.get('POSTGRES_PASSWORD')
DB_HOST = os.environ.get('POSTGRES_HOST', '127.0.0.1')
DB_PORT = int(os.environ.get('POSTGRES_PORT', 5433))

if not DB_PASS:
    print("ERROR: POSTGRES_PASSWORD is not set in environment. Aborting.")
    sys.exit(2)
>>>>>>> feature/rename-workers

try:
    # Try connecting using a DSN string including client_encoding
    dsn = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASS} client_encoding=LATIN1"
    conn = psycopg2.connect(dsn)
    # For databases using SQL_ASCII/latin1 content, force client encoding to LATIN1
    try:
        conn.set_client_encoding('LATIN1')
    except Exception:
        pass
    cur = conn.cursor()

    # Server encoding
    cur.execute("SHOW server_encoding;")
    enc = cur.fetchone()[0]

    # Installed extensions
    cur.execute("SELECT extname FROM pg_extension ORDER BY extname;")
    exts = [r[0] for r in cur.fetchall()]

    # Tables in public schema
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
    print("ERROR:", str(e))
    traceback.print_exc()
    sys.exit(2)
