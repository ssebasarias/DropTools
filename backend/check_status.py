
import os
import psycopg2
import time

dbname = os.getenv("POSTGRES_DB", "dahell_db")
user = os.getenv("POSTGRES_USER", "dahell_admin")
password = os.getenv("POSTGRES_PASSWORD")
host = os.getenv("POSTGRES_HOST", "db")
port = os.getenv("POSTGRES_PORT", "5432")

try:
    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
    cur = conn.cursor()
    
    print("--- DIAGNOSTICO DE DATOS ---")
    
    # 1. Conteo de Productos
    cur.execute("SELECT COUNT(*) FROM products;")
    prod_count = cur.fetchone()[0]
    print(f"Productos en DB: {prod_count}")

    # 2. Conteo de Embeddings
    cur.execute("SELECT COUNT(*) FROM product_embeddings;")
    emb_count = cur.fetchone()[0]
    print(f"Vectores Generados: {emb_count}")
    
    # 3. Verificar Integraciones recientes
    cur.execute("SELECT MAX(created_at) FROM products;")
    last_prod = cur.fetchone()[0]
    print(f"Último producto creado: {last_prod}")

    cur.execute("SELECT MAX(processed_at) FROM product_embeddings;")
    last_emb = cur.fetchone()[0]
    print(f"Último vector procesado: {last_emb}")

    conn.close()

except Exception as e:
    print(f"Error checking DB: {e}")
