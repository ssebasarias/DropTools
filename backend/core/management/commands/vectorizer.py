"""
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
from transformers import CLIPProcessor, CLIPModel
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
pwd = os.getenv("POSTGRES_PASSWORD", "secure_password_123")
host = os.getenv("POSTGRES_HOST", "127.0.0.1")
port = os.getenv("POSTGRES_PORT", "5433")
dbname = os.getenv("POSTGRES_DB", "dahell_db")

MODEL_NAME = "openai/clip-vit-base-patch32"

class Vectorizer:
    def __init__(self):
        logger.info(f"🧠 Cargando modelo de IA ({MODEL_NAME})...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"   Hardware detectado: {self.device.upper()}")
        
        self.model = CLIPModel.from_pretrained(MODEL_NAME).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        logger.info("✅ Modelo cargado y listo.")

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
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        return image_features.cpu().numpy()[0]

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
                    AND (pe.embedding_visual IS NULL)
                    LIMIT 100;
                """
                cur.execute(sql_queue)
                rows = cur.fetchall()

                if not rows:
                    logger.info("💤 Todo al día. Durmiendo 30s...")
                    time.sleep(30)
                    if conn: conn.close()
                    continue

                logger.info(f"🔨 Procesando lote de {len(rows)} imágenes...")
                
                processed_count = 0
                for pid, url in rows:
                    img = self.fetch_image(url)
                    vector = None
                    if img:
                        vector = self.generate_embedding(img)
                        vector_list = vector.tolist() if vector is not None else None
                    
                    if vector is not None:
                        sql_upsert = """
                            INSERT INTO product_embeddings (product_id, embedding_visual, processed_at)
                            VALUES (%s, %s, NOW())
                            ON CONFLICT (product_id) 
                            DO UPDATE SET embedding_visual = EXCLUDED.embedding_visual, processed_at = NOW();
                        """
                        cur.execute(sql_upsert, (pid, vector_list))
                        processed_count += 1
                        print(".", end="", flush=True)
                    else:
                         sql_upsert_dummy = """
                            INSERT INTO product_embeddings (product_id, processed_at)
                            VALUES (%s, NOW())
                            ON CONFLICT (product_id) DO NOTHING;
                        """
                         cur.execute(sql_upsert_dummy, (pid,))
                         print("x", end="", flush=True)

                conn.commit()
                print(f" -> Lote terminado ({processed_count} vectores generados).")
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
