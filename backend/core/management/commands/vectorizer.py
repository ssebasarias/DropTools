v"""
Módulo de Vectorización (Django Command).
"""

import os
import time
import requests
import logging
import pathlib
import sys
from io import BytesIO
import torch
from PIL import Image
from transformers import AutoProcessor, SiglipModel
import psycopg2
from psycopg2.extensions import register_adapter, AsIs
import numpy as np
from django.core.management.base import BaseCommand
from dotenv import load_dotenv

load_dotenv()

# ─────── Configuración de Logs ───────
LOG_DIR = pathlib.Path("/app/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("vectorizer")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

fh = logging.FileHandler(LOG_DIR / "vectorizer.log", encoding='utf-8')
fh.setFormatter(formatter)
logger.addHandler(fh)

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)

def addapt_numpy_array(numpy_array):
    return AsIs(list(numpy_array))

register_adapter(np.ndarray, addapt_numpy_array)

# Configuración DB
user = os.getenv("POSTGRES_USER", "dahell_admin")
# SECURITY: Never hardcode passwords. Ensure ENV var is set.
pwd = os.getenv("POSTGRES_PASSWORD") 
host = os.getenv("POSTGRES_HOST", "127.0.0.1")
port = os.getenv("POSTGRES_PORT", "5433")
dbname = os.getenv("POSTGRES_DB", "dahell_db")

if not pwd:
    # Fallback inseguro eliminado. Loguear warning crítico si estamos en local, o error.
    # Para desarrollo local rápido, a veces se deja, pero mejor lo limpiamos.
    pass 


MODEL_NAME = "google/siglip-so400m-patch14-384" # 384px - Estado del Arte (1152 dims)

class Vectorizer:
    def __init__(self):
        logger.info(f"🧠 Cargando modelo SigLIP ({MODEL_NAME})...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"   Hardware detectado: {self.device.upper()}")
        
        # Usamos AutoProcessor para manejar automáticamente el resize a 384x384
        self.model = SiglipModel.from_pretrained(MODEL_NAME).to(self.device)
        self.processor = AutoProcessor.from_pretrained(MODEL_NAME)
        logger.info("✅ Modelo SigLIP cargado y listo para alta resolución.")

    def get_db_connection(self):
        return psycopg2.connect(
            dbname=str(dbname), 
            user=str(user), 
            password=str(pwd), 
            host=str(host), 
            port=str(port),
            client_encoding='UTF8'
        )

    def fetch_image(self, url):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGB")
            return image
        except Exception:
            return None

    def generate_embedding(self, image):
        # Wrapper legacy para compatibilidad si fuera necesario, o para procesar 1 sola
        return self.generate_embedding_batch([image])[0]

    def generate_embedding_batch(self, images):
        """
        Procesa una lista de imágenes de golpe (Batch) con SigLIP
        Retorna: numpy array de shape [N, 1152]
        """
        # SigLIP AutoProcessor maneja el resize y normalización
        inputs = self.processor(images=images, return_tensors="pt", padding=True).to(self.device)
        
        with torch.no_grad():
            # SigLIP: get_image_features retorna los embeddings ya proyectados
            image_features = self.model.get_image_features(**inputs)
        
        # Normalización L2 (Importante para búsqueda por coseno)
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        return image_features.cpu().numpy()

    def run(self):
        while True:
            conn = None
            try:
                conn = self.get_db_connection()
                cur = conn.cursor()

                sql_queue = """
                    SELECT p.product_id, p.url_image_s3 
                    FROM products p
                    LEFT JOIN product_embeddings pe ON p.product_id = pe.product_id
                    WHERE p.url_image_s3 IS NOT NULL 
                    AND p.url_image_s3 != ''
                    AND (
                        pe.product_id IS NULL 
                        OR (
                            pe.embedding_visual IS NULL 
                            AND p.updated_at > pe.processed_at
                            -- COOLDOWN: If it failed recently (processed_at is new but embedding is null), 
                            -- don't retry immediately even if product updated. Wait 15 mins.
                            AND pe.processed_at < (NOW() - INTERVAL '15 minutes')
                        )
                    )
                    LIMIT 100;
                """
                cur.execute(sql_queue)
                rows = cur.fetchall()

                if not rows:
                    logger.info("💤 Todo al día. Durmiendo 30s...")
                    time.sleep(30)
                    if conn: conn.close()
                    continue

                logger.info(f"🔨 Procesando lote de {len(rows)} imágenes (Modo Batch)...")
                
                # --- OPTIMIZACIÓN PARALELA ---
                from concurrent.futures import ThreadPoolExecutor
                
                # 1. Descarga Paralela de Imágenes (I/O Bound)
                images_map = {} # { product_id: PIL.Image }
                failed_ids = []
                
                def download_task(row):
                    pid, url = row
                    img = self.fetch_image(url)
                    return pid, img

                with ThreadPoolExecutor(max_workers=20) as executor:
                    futures = [executor.submit(download_task, r) for r in rows]
                    for f in futures:
                        pid, img = f.result()
                        if img:
                            images_map[pid] = img
                        else:
                            failed_ids.append(pid)
                
                # 2. Procesamiento Batch IA (GPU/CPU Bound)
                if images_map:
                    # Crear listas ordenadas para el batch
                    valid_pids = list(images_map.keys())
                    valid_images = list(images_map.values())
                    
                    try:
                        # Inferencia en Batch (Mucho más rápido que 1 a 1)
                        # Nota: Se asume que 100 imágenes caben en VRAM. Si falla, reduce el LIMIT del SQL.
                        vectors = self.generate_embedding_batch(valid_images) # Nueva función batch
                        
                        # 3. Guardado en DB
                        sql_upsert = """
                            INSERT INTO product_embeddings (product_id, embedding_visual, processed_at)
                            VALUES (%s, %s, NOW())
                            ON CONFLICT (product_id) 
                            DO UPDATE SET embedding_visual = EXCLUDED.embedding_visual, processed_at = NOW();
                        """
                        
                        # Preparar datos para executemany (o loop rápido)
                        upsert_data = []
                        for i, pid in enumerate(valid_pids):
                            vec_list = vectors[i].tolist()
                            upsert_data.append((pid, vec_list))
                            
                        # Usamos loop con execute por seguridad con el adaptador pgvector manual,
                        # executemany a veces da problemas con listas complejas si no está bien configurado el adapter.
                        for pid, vec in upsert_data:
                            cur.execute(sql_upsert, (pid, vec))
                            
                        logger.info(f"✅ Vectorizados {len(valid_pids)} productos en paralelo.")
                        
                    except Exception as e:
                        logger.error(f"Error en batch IA: {e}")
                        # Fallback a dummy para no bloquear
                        failed_ids.extend(valid_pids)

                # 4. Marcar fallidos para no reintentar inmediatamente (o marcar como procesados sin vector)
                if failed_ids:
                     sql_upsert_dummy = """
                        INSERT INTO product_embeddings (product_id, processed_at)
                        VALUES (%s, NOW())
                        ON CONFLICT (product_id) DO UPDATE SET processed_at = NOW();
                    """
                     # Batch update for failed
                     for pid in failed_ids:
                         cur.execute(sql_upsert_dummy, (pid,))
                     logger.info(f"⚠️ Marcados {len(failed_ids)} fallidos o sin imagen.")

                conn.commit()
                cur.close()
                conn.close()

            except Exception as e:
                logger.error(f"❌ Error en ciclo vectorizer: {e}")
                time.sleep(10)
                if conn: conn.close()

class Command(BaseCommand):
    help = 'AI Vectorizer Daemon'

    def handle(self, *args, **options):
        self.stdout.write("🚀 VECTORIZER DAEMON INICIADO")
        v = Vectorizer()
        v.run()
