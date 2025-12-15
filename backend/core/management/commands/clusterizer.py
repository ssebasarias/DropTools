"""
Módulo de Clustering AVANZADO (Django Command).
"""

import os
import time
import logging
import psycopg2
import re
import pathlib
import sys
from difflib import SequenceMatcher
from django.core.management.base import BaseCommand
from dotenv import load_dotenv

load_dotenv()

# ─────── Configuración de Logs ───────
LOG_DIR = pathlib.Path("/app/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("clusterizer")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

fh = logging.FileHandler(LOG_DIR / "clusterizer.log", encoding='utf-8')
fh.setFormatter(formatter)
logger.addHandler(fh)

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)

UMBRAL_VISUAL_STRICT = 0.05
UMBRAL_VISUAL_CANDIDATE = 0.20
UMBRAL_TEXTO_MINIMO = 0.40
UMBRAL_SCORE_FINAL = 0.80

def get_db_connection():
    try:
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        
        if host == 'db': 
            try:
                import socket
                socket.gethostbyname('db')
            except:
                host = 'localhost'
                if port == '5433': pass 
                else: port = '5432'
        
        dbname = str(os.getenv("POSTGRES_DB", "dahell_db"))
        user = str(os.getenv("POSTGRES_USER", "dahell_admin"))
        password = str(os.getenv("POSTGRES_PASSWORD", "secure_password_123"))
        
        return psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
            client_encoding='UTF8'
        )
    except Exception as e:
        logger.error(f"Error conectando a DB: {e}")
        return None

def normalize_sku(sku):
    if not sku: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(sku)).upper()

def text_similarity(a, b):
    if not a or not b: return 0.0
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

def create_cluster(cur, representative_pid, method, confidence):
    cur.execute("""
        INSERT INTO unique_product_clusters (representative_product_id, created_at, updated_at)
        VALUES (%s, NOW(), NOW())
        RETURNING cluster_id
    """, (representative_pid,))
    cluster_id = cur.fetchone()[0]
    add_to_cluster(cur, cluster_id, representative_pid, method, confidence)
    return cluster_id

def add_to_cluster(cur, cluster_id, product_id, method, confidence):
    cur.execute("""
        INSERT INTO product_cluster_membership (product_id, cluster_id, match_confidence, match_method)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (product_id) DO UPDATE 
        SET cluster_id = EXCLUDED.cluster_id,
            match_confidence = EXCLUDED.match_confidence,
            match_method = EXCLUDED.match_method
    """, (product_id, cluster_id, confidence, method))

def update_cluster_metrics(cur):
    logger.info("   Actualizando métricas de clusters...")
    cur.execute("""
        UPDATE unique_product_clusters c
        SET 
            total_competitors = sub.competitors,
            average_price = sub.avg_price,
            saturation_score = CASE 
                WHEN sub.competitors <= 2 THEN 'BAJA'
                WHEN sub.competitors BETWEEN 3 AND 10 THEN 'MEDIA'
                ELSE 'ALTA'
            END,
            updated_at = NOW()
        FROM (
            SELECT 
                cluster_id, 
                COUNT(DISTINCT p.supplier_id) as competitors,
                AVG(p.sale_price) as avg_price
            FROM product_cluster_membership m
            JOIN products p ON m.product_id = p.product_id
            GROUP BY cluster_id
        ) sub
        WHERE c.cluster_id = sub.cluster_id;
    """)

def run_hard_clustering(conn):
    cur = conn.cursor()
    logger.info("🔒 Fase 1: Hard Clustering (Solo por SKU)...")
    
    # NOTA: Se eliminó el clustering por BODEGA porque una bodega
    # puede tener múltiples productos distintos, causando falsos positivos graves.
    
    # 1. SKU CLUSTERING
    # Buscamos SKUs idénticos que tengan más de 3 caracteres
    cur.execute("""
        SELECT sku, array_agg(product_id)
        FROM products
        WHERE length(sku) > 3 
        GROUP BY sku
        HAVING count(*) > 1
    """)
    sku_groups = cur.fetchall()
    
    count_sku_clusters = 0
    
    for sku, pids in sku_groups:
        norm_sku = normalize_sku(sku)
        
        # Filtros de seguridad para SKUs basura
        if not norm_sku or len(norm_sku) < 4: continue
        if norm_sku in ["TEST", "PRUEBA", "GENERICO", "VARIOS", "0000", "1234"]: continue
        
        target_cluster = None
        
        # Verificar si alguno de estos productos ya tiene cluster
        cur.execute(f"SELECT cluster_id FROM product_cluster_membership WHERE product_id IN %s LIMIT 1", (tuple(pids),))
        res = cur.fetchone()
        
        if res:
            target_cluster = res[0]
        else:
            # Crear nuevo cluster
            target_cluster = create_cluster(cur, pids[0], 'HARD_SKU', 0.98)
            count_sku_clusters += 1
            
        # Unir todos al cluster
        for pid in pids:
            add_to_cluster(cur, target_cluster, pid, 'HARD_SKU', 0.98)
            
    conn.commit()
    logger.info(f"   Fase 1 completada. {count_sku_clusters} nuevos clusters creados por SKU.")
    cur.close()

def run_soft_clustering(conn):
    cur = conn.cursor()
    logger.info("👁️ Fase 2: Clustering Inteligente (Visual + Semántico)...")
    
    cur.execute("""
        SELECT pe.product_id, p.title, p.product_type 
        FROM product_embeddings pe
        JOIN products p ON pe.product_id = p.product_id
        LEFT JOIN product_cluster_membership m ON pe.product_id = m.product_id
        WHERE m.cluster_id IS NULL -- Solo huerfanos
        AND pe.embedding_visual IS NOT NULL
        LIMIT 200
    """)
    orphans = cur.fetchall()
    
    count_new = 0
    count_joined = 0
    
    for row in orphans:
        pid, title, p_type = row
        
        cur.execute("""
            SELECT 
                pe.product_id, 
                (pe.embedding_visual <=> (SELECT embedding_visual FROM product_embeddings WHERE product_id = %s)) as dist,
                m.cluster_id,
                p.title,
                p.product_type
            FROM product_embeddings pe
            JOIN products p ON pe.product_id = p.product_id
            LEFT JOIN product_cluster_membership m ON pe.product_id = m.product_id
            WHERE pe.product_id != %s
            AND pe.embedding_visual IS NOT NULL
            ORDER BY dist ASC
            LIMIT 5
        """, (pid, pid))
        
        candidates = cur.fetchall()
        best_cluster = None
        best_score = 0.0
        
        for cand in candidates:
            c_pid, c_dist, c_cluster_id, c_title, c_type = cand
            
            visual_score = max(0, (1.0 - (c_dist / UMBRAL_VISUAL_CANDIDATE)))
            if c_dist > UMBRAL_VISUAL_CANDIDATE: visual_score = 0
            
            txt_score = text_similarity(title, c_title)
            type_penalty = 1.0
            if p_type != c_type and p_type and c_type:
                type_penalty = 0.9 
            
            final_score = 0.0
            method = "AI_HYBRID"
            
            if c_dist < UMBRAL_VISUAL_STRICT:
                final_score = (0.8 * visual_score) + (0.2 * txt_score)
                method = "AI_VISUAL_STRONG"
            else:
                if txt_score < UMBRAL_TEXTO_MINIMO:
                    final_score = 0.0
                else:
                    final_score = (0.5 * visual_score) + (0.5 * txt_score)
            
            final_score *= type_penalty
            
            if final_score >= UMBRAL_SCORE_FINAL:
                if c_cluster_id:
                    best_cluster = c_cluster_id
                    best_score = final_score
                    break
                else:
                    new_c = create_cluster(cur, c_pid, method, final_score)
                    add_to_cluster(cur, new_c, c_pid, method, final_score)
                    best_cluster = new_c
                    best_score = final_score
                    break
        
        if best_cluster:
            add_to_cluster(cur, best_cluster, pid, 'AI_HYBRID', best_score)
            count_joined += 1
        else:
            create_cluster(cur, pid, 'SINGLETON', 1.0)
            count_new += 1
            
    conn.commit()
    logger.info(f"   Fase 2 Terminada: {count_joined} unidos, {count_new} nuevos clusters.")
    cur.close()

class Command(BaseCommand):
    help = 'Product Clusterizer Daemon'

    def handle(self, *args, **options):
        self.stdout.write("INICIANDO CLUSTERIZER V2 (Robust)...")
        while True:
            conn = get_db_connection()
            if conn:
                try:
                    run_hard_clustering(conn)
                    run_soft_clustering(conn)
                    
                    cur = conn.cursor()
                    update_cluster_metrics(cur)
                    conn.commit()
                    cur.close()
                    conn.close()
                    
                    self.stdout.write("💤 Ciclo finalizado. Esperando 60s...")
                    time.sleep(60)
                except Exception as e:
                    self.stderr.write(f"❌ Error CRITICO en loop: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(10)
            else:
                self.stderr.write("No hay conexión DB. Reintentando en 10s...")
                time.sleep(10)
