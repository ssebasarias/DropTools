
import os
import psycopg2
import json
import pathlib
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuración DB
user = os.getenv("POSTGRES_USER", "dahell_admin")
pwd = os.getenv("POSTGRES_PASSWORD", "secure_password_123")
host = os.getenv("POSTGRES_HOST", "127.0.0.1")
port = os.getenv("POSTGRES_PORT", "5433")
dbname = os.getenv("POSTGRES_DB", "dahell_db")

def get_stats():
    print("--- DIAGNÓSTICO DEL SISTEMA ---")
    
    # 1. Analisis de Archivos RAW
    raw_dir = pathlib.Path("raw_data")
    total_lines = 0
    files_info = []
    if raw_dir.exists():
        for f in raw_dir.glob("*.jsonl"):
            size_mb = f.stat().st_size / (1024 * 1024)
            # Count lines quickly
            with open(f, 'rb') as fp:
                lines = sum(1 for _ in fp)
            total_lines += lines
            files_info.append(f"{f.name} ({size_mb:.2f} MB, {lines} líneas)")
            
    print(f"\n[FILESYSTEM] Archivos RAW encontrados: {len(files_info)}")
    for info in files_info:
        print(f"  - {info}")
    print(f"  > Total registros extraídos (raw): {total_lines}")

    # 2. Analisis de Base de Datos
    try:
        conn = psycopg2.connect(dbname=dbname, user=user, password=pwd, host=host, port=port)
        cur = conn.cursor()
        
        # Conteo Productos
        cur.execute("SELECT COUNT(*) FROM products;")
        total_products = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM products WHERE url_image_s3 IS NOT NULL AND url_image_s3 != '';")
        products_with_images = cur.fetchone()[0]
        
        # Conteo Vectores
        cur.execute("SELECT COUNT(*) FROM product_embeddings;")
        total_embeddings_rows = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM product_embeddings WHERE embedding_visual IS NOT NULL;")
        valid_vectors = cur.fetchone()[0]
        
        failed_vectors = total_embeddings_rows - valid_vectors
        
        # Conteo Clusters
        cur.execute("SELECT COUNT(*) FROM unique_product_clusters;")
        total_clusters = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM product_cluster_membership;")
        clustered_products = cur.fetchone()[0]
        
        # Conteo Bodegas/Proveedores
        cur.execute("SELECT COUNT(*) FROM warehouses;")
        total_warehouses = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM suppliers;")
        total_suppliers = cur.fetchone()[0]

        print(f"\n[DATABASE] Estado Actual:")
        print(f"  - Productos Totales (Tabla 'products'): {total_products}")
        print(f"  - Productos con URL de Imagen: {products_with_images}")
        print(f"  - Proveedores detectados: {total_suppliers}")
        print(f"  - Bodegas detectadas: {total_warehouses}")
        
        print(f"\n[VECTORIZER] Estado de IA:")
        print(f"  - Imágenes procesadas (filas en embeddings): {total_embeddings_rows}")
        print(f"  - Vectores exitosos: {valid_vectors}")
        print(f"  - Fallos (imágenes no descargadas/corruptas): {failed_vectors}")
        if products_with_images > 0:
            coverage = (valid_vectors / products_with_images) * 100
            print(f"  - Cobertura de Vectorización: {coverage:.1f}% de las imágenes disponibles")
        
        print(f"\n[CLUSTERIZER] Estado de Agrupación:")
        print(f"  - Total Clusters Únicos: {total_clusters}")
        print(f"  - Productos asignados a clusters: {clustered_products}")
        if total_products > 0:
            cluster_coverage = (clustered_products / total_products) * 100
            print(f"  - Cobertura de Clustering: {cluster_coverage:.1f}% del catálogo")

        # Top proveedores
        print(f"\n[INSIGHTS] Top 5 Proveedores por Volumen:")
        cur.execute("""
            SELECT s.name, COUNT(p.product_id) as c 
            FROM products p 
            JOIN suppliers s ON p.supplier_id = s.supplier_id 
            GROUP BY s.name 
            ORDER BY c DESC 
            LIMIT 5
        """)
        for name, count in cur.fetchall():
            print(f"  - {name}: {count} productos")

        conn.close()
        
    except Exception as e:
        print(f"\n❌ ERROR conectando a la DB: {e}")

if __name__ == "__main__":
    get_stats()
