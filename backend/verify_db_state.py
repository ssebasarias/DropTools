
import os
import psycopg2
import sys

dbname = os.getenv("POSTGRES_DB", "dahell_db")
user = os.getenv("POSTGRES_USER", "dahell_admin")
password = os.getenv("POSTGRES_PASSWORD")
host = os.getenv("POSTGRES_HOST", "db")
port = os.getenv("POSTGRES_PORT", "5432")

print(f"Connecting to {dbname} at {host}:{port} as {user}...")

try:
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    cur = conn.cursor()
    
    # 1. Check Extensions
    print("\n--- Extensions in CURRENT Database ---")
    cur.execute("SELECT extname, extversion FROM pg_extension;")
    extensions = cur.fetchall()
    found_vector = False
    for ext in extensions:
        print(f"- {ext[0]} (v{ext[1]})")
        if ext[0] == 'vector':
            found_vector = True
            
    if found_vector:
        print("✅ 'vector' extension IS installed.")
    else:
        print("❌ 'vector' extension is NOT installed in this database.")

    # 2. Check Table Schema
    print("\n--- 'product_embeddings' Schema ---")
    try:
        cur.execute("""
            SELECT column_name, data_type, udt_name 
            FROM information_schema.columns 
            WHERE table_name = 'product_embeddings';
        """)
        columns = cur.fetchall()
        if not columns:
            print("❌ Table 'product_embeddings' does not exist.")
        else:
            for col in columns:
                print(f"Column: {col[0]}, Type: {col[1]}, UDT: {col[2]}")
                if col[0] == 'embedding_visual':
                    if 'vector' in col[2]:
                        print("✅ 'embedding_visual' column is correctly set to type VECTOR.")
                    else:
                        print(f"❌ 'embedding_visual' column is type {col[2]}, expected id-vector or similar.")
    except Exception as e:
        print(f"Error checking schema: {e}")

    conn.close()

except Exception as e:
    print(f"Connection failed: {e}")
