"""
Módulo de Clustering AVANZADO HÍBRIDO (Django Command).
V3: Implementa lógica híbrida (Imagen + Texto) más robusta y "Human-in-the-Loop ready".
"""

import os
import time
import logging
import psycopg2
import re
import pathlib
import sys
import json
from difflib import SequenceMatcher
from django.core.management.base import BaseCommand
from dotenv import load_dotenv

load_dotenv()

# ─────── Configuración de Logs ───────
LOG_DIR = pathlib.Path("/app/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Logger principal (texto plano para debug)
logger = logging.getLogger("clusterizer")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

fh = logging.FileHandler(LOG_DIR / "clusterizer.log", encoding='utf-8')
fh.setFormatter(formatter)
logger.addHandler(fh)

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)

# Logger de Decisiones (JSON para Auditoría Frontend)
# Este escribirá en un archivo separado o con un formato parseable
audit_logger = logging.getLogger("cluster_audit")
audit_logger.setLevel(logging.INFO)
audit_handler = logging.FileHandler(LOG_DIR / "cluster_audit.jsonl", encoding='utf-8')
audit_handler.setFormatter(logging.Formatter('%(message)s'))
audit_logger.addHandler(audit_handler)

# ─────── CONFIGURACIÓN DINÁMICA ───────
def load_config(cur):
    """Carga los pesos actuales desde la base de datos (Cerebro Dinámico)"""
    config = {
        "weight_visual": 0.6,
        "weight_text": 0.4,
        "threshold_visual_rescue": 0.15,
        "threshold_text_rescue": 0.95,
        "threshold_hybrid": 0.68
    }
    try:
        cur.execute("""
            SELECT weight_visual, weight_text, threshold_visual_rescue, 
                   threshold_text_rescue, threshold_hybrid
            FROM cluster_config ORDER BY id DESC LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            config["weight_visual"] = float(row[0])
            config["weight_text"] = float(row[1])
            config["threshold_visual_rescue"] = float(row[2])
            config["threshold_text_rescue"] = float(row[3])
            config["threshold_hybrid"] = float(row[4])
    except Exception as e:
        logger.error(f"⚠️ Error cargando config dinámica: {e}. Usando defaults.")
    return config

# ─────── HELPERS ───────

def get_db_connection():
    try:
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        
        # Corrección automática para ambiente Docker vs Local
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
    # SequenceMatcher es bueno para detectar typos y palabras comunes
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

def log_decision(pid_a, pid_b, visual_score, text_score, final_score, decision, method, title_a, title_b, active_weights, image_a=None, image_b=None):
    """Guarda la decisión en un log estructurado JSONL para el Dashboard"""
    event = {
        "timestamp": time.time(),
        "product_id": pid_a,
        "candidate_id": pid_b,
        "title_a": title_a[:50],
        "title_b": title_b[:50],
        "image_a": image_a,
        "image_b": image_b,
        "visual_score": round(visual_score, 3),
        "text_score": round(text_score, 3),
        "final_score": round(final_score, 3),
        "decision": decision, # MATCH / REJECT
        "method": method,
        "active_weights": active_weights # Snapshot para Training
    }
    audit_logger.info(json.dumps(event))

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

# ---------------------------------------------------------------------
# FASE 2: CLUSTERING HÍBRIDO INTELIGENTE
# ---------------------------------------------------------------------
def run_hybrid_clustering(conn):
    cur = conn.cursor()
    logger.info("🧠 Fase 2: Clustering Híbrido (Imagen + Texto Paralelo)...")

    # CARGAR CONFIGURACIÓN DINÁMICA
    CONFIG = load_config(cur)
    logger.info(f"   ⚙️ Pesos Activos: V={CONFIG['weight_visual']}, T={CONFIG['weight_text']} | Umbral={CONFIG['threshold_hybrid']}")

    # 1. Habilitar extensión Trigram (si es posible) para búsquedas de texto aceleradas
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        conn.commit()
    except:
        conn.rollback()
        logger.warning("⚠️ No se pudo habilitar pg_trgm. La búsqueda por texto será más lenta o limitada.")

    # 2. Buscar huérfanos
    cur.execute("""
        SELECT pe.product_id, p.title, p.product_type, p.url_image_s3
        FROM product_embeddings pe
        JOIN products p ON pe.product_id = p.product_id
        LEFT JOIN product_cluster_membership m ON pe.product_id = m.product_id
        WHERE m.cluster_id IS NULL 
        AND pe.embedding_visual IS NOT NULL
        LIMIT 200
    """)
    orphans = cur.fetchall()
    
    count_new = 0
    count_joined = 0
    
    # Constante fija alta para strong visual match
    STRONG_VISUAL_THRESHOLD = 0.85 
    
    for row in orphans:
        pid, title, p_type, img_a = row
        
        # --- ESTRATEGIA DE RETRIEVAL (CANDIDATOS) ---
        # Buscamos candidatos por DOS vías:
        # A. Visual (Vector) - Trae cosas que se VEN igual
        # B. Texto (Trigram/Like) - Trae cosas que se LLAMAN igual
        
        candidates_map = {} # pid -> {data}

        # A. Búsqueda Visual (Top 50 - Deep Probe)
        cur.execute("""
            SELECT 
                pe.product_id, 
                (pe.embedding_visual <=> (SELECT embedding_visual FROM product_embeddings WHERE product_id = %s)) as dist,
                m.cluster_id, p.title, p.product_type, 'VISUAL_SEARCH', p.url_image_s3
            FROM product_embeddings pe
            JOIN products p ON pe.product_id = p.product_id
            LEFT JOIN product_cluster_membership m ON pe.product_id = m.product_id
            WHERE pe.product_id != %s AND pe.embedding_visual IS NOT NULL
            ORDER BY dist ASC
            LIMIT 50
        """, (pid, pid))
        
        for c in cur.fetchall():
            c_pid = c[0]
            candidates_map[c_pid] = {
                'dist': c[1], 'cluster_id': c[2], 'title': c[3], 'type': c[4], 'source': 'VISUAL', 'image': c[6]
            }

        # B. Búsqueda de Texto (Opcional - Si pg_trgm funciona mejoraría)
        # Por ahora, usamos una heurística simple: Misma longitud aproximada y palabras clave
        # "Si el título comparte las primeras 2 palabras..."
        # Nota: Hacer esto en SQL sin FTS puede ser lento, lo haremos ligero en Python sobre los candidatos visuales
        # para no matar la DB, PERO idealmente haríamos una query textual aquí.
        
        # --- SCORING HÍBRIDO ---
        best_match = None
        best_score = 0.0
        match_reason = ""

        # Evaluamos todos los candidatos recuperados
        for c_pid, data in candidates_map.items():
            dist = data['dist']
            c_title = data['title']
            
            # 1. Similitud Visual (Re-calibrada V4)
            # Clip dist va de 0 a 2.
            # El "piso de ruido" para productos fondo blanco es aprox 0.26.
            # Usamos un factor x3.2 para enviar ese ruido hacia el 10-15% y no 75%.
            visual_sim = max(0.0, 1.0 - (dist * 3.2)) 
            
            # 2. Similitud Texto
            text_sim = text_similarity(title, c_title)
            
            # 3. Lógica de Decisión (Árbol de Reglas DINÁMICO)
            final_score = 0.0
            method = "REJECT"
            
            # CASO 1: FOTO IDENTICA (Variación de luz mínima)
            if visual_sim >= STRONG_VISUAL_THRESHOLD:
                final_score = visual_sim
                method = "VISUAL_MATCH"
            
            # CASO 2: RESCATE POR TEXTO (Foto regular, Texto idéntico)
            elif text_sim >= CONFIG['threshold_text_rescue'] and visual_sim >= CONFIG['threshold_visual_rescue']:
                final_score = (0.3 * visual_sim) + (0.7 * text_sim) # Prioridad Texto
                method = "TEXT_RESCUE"
                
            # CASO 3: HÍBRIDO ESTÁNDAR
            else:
                final_score = (CONFIG['weight_visual'] * visual_sim) + (CONFIG['weight_text'] * text_sim)
                method = "HYBRID_SCORE"
            
            # Penalización por tipo (si detecta que uno es 'Zapato' y otro 'Reloj')
            if p_type and data['type'] and p_type != data['type']:
                final_score *= 0.8
            
            # LOG PARA AUDITORIA (Solo candidatos prometedores)
            if final_score > 0.5:
                # Logueamos "REJECT" si no alcanza, o "CANDIDATE" si alcanza pero no es el mejor aun
                decision_temp = "CANDIDATE" if final_score >= CONFIG['threshold_hybrid'] else "REJECTED_LOW_SCORE"
                log_decision(pid, c_pid, visual_sim, text_sim, final_score, decision_temp, method, title, c_title, CONFIG, img_a, data['image'])

            # Check si es el mejor hasta ahora
            if final_score >= CONFIG['threshold_hybrid']:
                if final_score > best_score:
                    best_score = final_score
                    best_match = data
                    match_reason = method

        # --- ACCIÓN FINAL ---
        if best_match:
            target_cluster = best_match['cluster_id']
            
            if target_cluster:
                # Unirse a cluster existente
                add_to_cluster(cur, target_cluster, pid, match_reason, best_score)
                count_joined += 1
                log_decision(pid, best_match['cluster_id'], best_score, 0, best_score, "JOINED_CLUSTER", match_reason, title, best_match['title'], img_a, best_match['image'])
            else:
                # El candidato tampoco tiene cluster (raro si viene de embeddings, pero posible)
                # Creamos uno nuevo con ambos
                new_c = create_cluster(cur, row[0], match_reason, best_score) # row[0] es el candidato original (c_pid esta en loop)
                # Ah, row es el orphan. best_match es el otro.
                # Unimos al orphan al nuevo cluster
                # Y "robamos" al candidato si no tenía cluster? (Ya lo filtramos, candidates usually have clusters or self)
                pass 
                
        else:
            # Nadie cumplió los requisitos -> SINGLETON
            create_cluster(cur, pid, 'SINGLETON', 1.0)
            count_new += 1
            
    conn.commit()
    logger.info(f"   Ciclo Híbrido: {count_joined} unidos, {count_new} nuevos clusters.")
    cur.close()

# ---------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Product Clusterizer Daemon V3'

    def handle(self, *args, **options):
        self.stdout.write("INICIANDO CLUSTERIZER HÍBRIDO V3...")
        while True:
            conn = get_db_connection()
            if conn:
                try:
                    # Mantenemos Hard Clustering para SKUs obvios
                    # run_hard_clustering(conn) # (Opcional, comentado para probar solo Híbrido)
                    
                    run_hybrid_clustering(conn)
                    
                    cur = conn.cursor()
                    update_cluster_metrics(cur)
                    conn.commit()
                    cur.close()
                    conn.close()
                    
                    self.stdout.write("💤 Ciclo terminado. Esperando 30s...")
                    time.sleep(30)
                except Exception as e:
                    self.stderr.write(f"❌ Error CRITICO: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(10)
            else:
                time.sleep(10)
