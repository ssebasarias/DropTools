"""
Módulo de Clustering AVANZADO HÍBRIDO (Django Command).
V3: Implementa lógica híbrida (Imagen + Texto) más robusta y "Human-in-the-Loop ready".
REPARADO: Estructura corregida tras auditoría.
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

from django.db.models import F
from django.db.models.functions import Now
load_dotenv()

# ─────── Configuración de Logs ───────
LOG_DIR = pathlib.Path("/app/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Logger principal
logger = logging.getLogger("clusterizer")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

fh = logging.FileHandler(LOG_DIR / "clusterizer.log", encoding='utf-8')
fh.setFormatter(formatter)
logger.addHandler(fh)

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)

# ─────── CONFIGURACIÓN DINÁMICA ───────
# ─────── CONFIGURACIÓN DINÁMICA (CEREBRO POR CONCEPTO) ───────
def load_config(cur, concept_name="DEFAULT"):
    """
    Carga los pesos específicos para un concepto (Personalidad Dinámica).
    Si no existe personalidad para 'Perfume', usa la 'DEFAULT'.
    """
    config = {
        "weight_visual": 0.6,
        "weight_text": 0.4,
        "threshold_visual_rescue": 0.92, # Hardcoded defaults baselines
        "threshold_text_rescue": 0.95,
        "threshold_hybrid": 0.68
    }
    try:
        # Intentar cargar config específica para el concepto
        cur.execute("""
            SELECT weight_visual, weight_text, threshold_hybrid
            FROM concept_weights 
            WHERE concept = %s
        """, (concept_name,))
        row = cur.fetchone()
        
        # Si no hay, cargar DEFAULT
        if not row:
            cur.execute("""
                SELECT weight_visual, weight_text, threshold_hybrid
                FROM concept_weights 
                WHERE concept = 'DEFAULT'
            """)
            row = cur.fetchone()
            
        if row:
            config["weight_visual"] = float(row[0])
            config["weight_text"] = float(row[1])
            config["threshold_hybrid"] = float(row[2])
            
            # Ajuste dinámico de umbrales de rescate basado en pesos
            # Si el texto es muy importante (w_text > 0.7), relajamos el visual rescue?
            # Por seguridad, mantenemos los rescues visuales muy altos (0.92) siempre.
            
    except Exception as e:
        logger.error(f"⚠️ Error cargando config dinámica para {concept_name}: {e}. Usando defaults.")
    
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
        
        dbname = str(os.getenv("POSTGRES_DB", "droptools_db"))
        user = str(os.getenv("POSTGRES_USER", "droptools_admin"))
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

from core.models import ClusterDecisionLog

def log_decision(pid_a, pid_b, visual_score, text_score, final_score, decision, method, title_a, title_b, active_weights, image_a=None, image_b=None):
    """Guarda la decisión en la Base de Datos (Persistente)"""
    try:
        ClusterDecisionLog.objects.create(
            product_id=pid_a,
            candidate_id=pid_b,
            title_a=title_a,
            title_b=title_b,
            image_a=image_a,
            image_b=image_b,
            visual_score=visual_score,
            text_score=text_score,
            final_score=final_score,
            decision=decision,
            match_method=method,
            active_weights=active_weights
        )
    except Exception as e:
        logger.error(f"Error saving audit log to DB: {e}")

# ─────── FUNCIONES CORE DE CLUSTERING ───────

from core.models import UniqueProductCluster, ProductClusterMembership, Product

def create_cluster(cur, pid, saturation_score, avg_price):
    # Use ORM to avoid missing default columns in raw SQL
    # Note: 'cur' is ignored here, we use Django DB connection implicitly
    new_cluster = UniqueProductCluster.objects.create(
        representative_product_id=pid,
        total_competitors=1,
        saturation_score=saturation_score,
        average_price=avg_price
        # All other fields (analysis_level, etc.) use their defaults from models.py
    )
    
    ProductClusterMembership.objects.update_or_create(
        product_id=pid,
        defaults={
            'cluster': new_cluster,
            'match_confidence': 1.0,
            'match_method': 'REPRESENTATIVE'
        }
    )
    return new_cluster.cluster_id

def add_to_cluster(cur, cluster_id, pid, method, confidence):
    # Use ORM
    ProductClusterMembership.objects.update_or_create(
        product_id=pid,
        defaults={
            'cluster_id': cluster_id,
            'match_confidence': confidence,
            'match_method': method
        }
    )
    
    # Update counter
    UniqueProductCluster.objects.filter(cluster_id=cluster_id).update(
        total_competitors=F('total_competitors') + 1,
        updated_at=Now()
    )

def update_cluster_metrics(cur):
    """Recalcula precio promedio y saturación para clusters modificados recientemente"""
    # Simplificado: Recalcular todo o los ultimos 100
    # En producción esto debería ser más selectivo
    pass 

def run_hybrid_clustering(conn):
    cur = conn.cursor()
    
    # 1. Configuración cargada bajo demanda por producto
    # CONFIG = load_config(cur) # <-- REMOVED GLOBAL LOAD
    
    # 2. Obtener productos SIN cluster pero CON vector y CON concepto (Agent 1 Ready)
    # limitamos a 50 por ciclo para no bloquear
    sql_targets = """
        SELECT p.product_id, p.title, p.sale_price, pe.embedding_visual, p.url_image_s3, p.taxonomy_concept
        FROM products p
        JOIN product_embeddings pe ON p.product_id = pe.product_id
        LEFT JOIN product_cluster_membership pcm ON p.product_id = pcm.product_id
        WHERE pcm.cluster_id IS NULL 
        AND pe.embedding_visual IS NOT NULL
        AND p.taxonomy_concept IS NOT NULL
        LIMIT 50
    """
    cur.execute(sql_targets)
    targets = cur.fetchall()
    
    if not targets:
        logger.info("✨ No hay productos clasificados pendientes. Esperando al Taxonomist...")
        cur.close()
        return

    logger.info(f"⚡ Procesando {len(targets)} productos con Lógica Híbrida (Bucket Strategy)...")
    
    count_joined = 0
    count_new = 0

    for row in targets:
        pid, title, price, vector, img_a, concept = row
        
        # 1.5 Cargar Personalidad Dinámica para este concepto
        CONFIG = load_config(cur, concept_name=concept)
        
        # 3. Buscar Candidatos (Vector Search RESTRINGIDO al Bucket)
        # Solo buscamos items que sean del mismo concepto taxonómico
        sql_candidates = """
            SELECT 
                p.product_id, p.title, p.url_image_s3,
                pcm.cluster_id,
                (pe.embedding_visual <=> %s) as distance
            FROM product_embeddings pe
            JOIN products p ON pe.product_id = p.product_id
            JOIN product_cluster_membership pcm ON p.product_id = pcm.product_id
            WHERE pe.product_id != %s
            AND p.taxonomy_concept = %s  -- <-- OPTIMIZACIÓN CRÍTICA (Nivel 2)
            ORDER BY distance ASC
            LIMIT 5
        """
        cur.execute(sql_candidates, (vector, pid, concept))
        raw_candidates = cur.fetchall()
        
        best_score = 0.0
        best_match = None
        match_reason = "NONE"
        
        for cand in raw_candidates:
            c_pid, c_title, c_image, c_cluster_id, dist = cand
            
            # 4. Calcular Scores
            visual_score = max(0, 1.0 - float(dist))
            text_score = SequenceMatcher(None, str(title).lower(), str(c_title).lower()).ratio()
            
            final_score = (CONFIG['weight_visual'] * visual_score) + (CONFIG['weight_text'] * text_score)
            
            # Lógica de "Rescate"
            method = "REJECTED"
            is_match = False
            
            if final_score >= CONFIG['threshold_hybrid']:
                method = "HYBRID_MATCH"
                is_match = True
            elif visual_score >= 0.92: # Muy parecidos visualmente
                method = "VISUAL_Rescue"
                is_match = True
                final_score = max(final_score, visual_score) # Boost score
            elif text_score >= CONFIG['threshold_text_rescue'] and visual_score > 0.6:
                method = "TEXT_Rescue"
                is_match = True
                final_score = max(final_score, text_score)
            
            # Loguear decisión (incluso los rejected para debug)
            # Solo guardamos el mejor log o muestreamos para no llenar la DB?
            # Por ahora guardamos todo "intento serio"
            if is_match or final_score > 0.5:
                 log_decision(pid, c_pid, visual_score, text_score, final_score, 
                              "MATCH" if is_match else "REJECT", 
                              method, title, c_title, CONFIG, img_a, c_image)

            if is_match and final_score > best_score:
                best_score = final_score
                best_match = {
                    "cluster_id": c_cluster_id,
                    "title": c_title,
                    "image": c_image
                }
                match_reason = method
                
                # REGLA DE AUDITORÍA INTELIGENTE:
                # Si es un match, pero no es abrumadoramente obvio (ej: >0.95), márcarlo como "Duda" para auditoría humana.
                # Auto-Pilot: Score > 0.85
                # Human-Review: 0.65 < Score < 0.85 (Zona Gris)
                if final_score < 0.85:
                    match_reason = "NEEDS_AUDIT"

        # 5. Acción Final
        if best_match:
            add_to_cluster(cur, best_match['cluster_id'], pid, match_reason, best_score)
            count_joined += 1
        else:
            # Crear nuevo cluster con 1 solo miembro
            create_cluster(cur, pid, "LOW_DATA", price)
            count_new += 1
            
    logger.info(f"   📊 Resultado Ciclo: {count_joined} unidos, {count_new} nuevos clusters.")
    cur.close()

# ─────── COMMAND ───────

class Command(BaseCommand):
    help = 'Product Clusterizer Daemon V3'

    def handle(self, *args, **options):
        self.stdout.write("🚀 INICIANDO CLUSTERIZER HÍBRIDO (REPARADO)...")
        while True:
            conn = get_db_connection()
            if conn:
                try:
                    run_hybrid_clustering(conn)
                    conn.commit()
                    conn.close()
                    # Dormir un poco pero no tanto
                    time.sleep(10) 
                except Exception as e:
                    self.stderr.write(f"❌ Error CRITICO: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(10)
            else:
                self.stderr.write("⚠️ DB Unreachable, retrying...")
                time.sleep(10)
