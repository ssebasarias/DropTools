"""
Módulo de carga ETL (Django Command).
"""
import os
import json
import logging
import pathlib
import sys
import time
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote

load_dotenv()

# ─────── Configuración de Logs ───────
LOG_DIR = pathlib.Path("/app/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("loader")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

fh = logging.FileHandler(LOG_DIR / "loader.log", encoding='utf-8')
fh.setFormatter(formatter)
logger.addHandler(fh)

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)

RAW_DIR = pathlib.Path(os.getenv("RAW_DIR", "raw_data"))

class Command(BaseCommand):
    help = 'ETL Loader Daemon'

    def handle(self, *args, **options):
        self.stdout.write("🚀 LOADER DAEMON INICIADO (Modo Infinito)")
        
        # Setup DB connection once (or Reconnect on fail)
        session = self.get_session()
        
        while True:
            try:
                files = list(RAW_DIR.glob("*.jsonl"))
                if not files:
                    logger.info("⏳ Sin archivos. Esperando 60s...")
                else:
                    for f in files:
                        self.process_file(f, session)
                
                logger.info("💤 Durmiendo 60 segundos...")
                time.sleep(60)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"❌ Error crítico: {e}")
                session = self.get_session() # Reconnect attempt
                time.sleep(60)

    def get_session(self):
        # Configuración DB
        user = os.getenv("POSTGRES_USER", "dahell_admin")
        pwd = os.getenv("POSTGRES_PASSWORD", "secure_password_123")
        host = os.getenv("POSTGRES_HOST", "127.0.0.1")
        port = os.getenv("POSTGRES_PORT", "5433")
        dbname = os.getenv("POSTGRES_DB", "dahell_db")
        raw_db_url = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{dbname}"
        
        engine = create_engine(raw_db_url, echo=False, connect_args={'client_encoding': 'utf8'})
        Session = sessionmaker(bind=engine)
        return Session()

    def process_file(self, filepath, session):
        logger.info(f"Processing: {filepath.name}")
        count = 0
        errors_count = 0
        
        # Estrategia de "Filtro de Entrada":
        # 1. Intentamos leer como UTF-8 estricto (ideal).
        # 2. Si falla, caemos a Latin-1 (común en Windows/Excel aniguos).
        # 3. Forzamos conversión a UTF-8 válido para Python y la DB.
        
        encoding_strategy = 'utf-8'
        try:
            # Prueba rápida de lectura para detectar encoding
            with open(filepath, 'r', encoding='utf-8') as f:
                for i, _ in enumerate(f):
                    if i > 500: break # Muestreo de las primeras 500 lineas
        except UnicodeDecodeError:
            logger.warning(f"⚠️  Detectado encoding LEGACY (Latin-1/CP1252) en {filepath.name}. Normalizando...")
            encoding_strategy = 'latin-1' # Fallback seguro
        
        try:
            with open(filepath, 'r', encoding=encoding_strategy, errors='replace') as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        # Decodificamos el JSON
                        record = json.loads(line)
                        
                        # PASO CRUCIAL: "Lavado" de Strings
                        # Recorremos el diccionario recursivamente para asegurar que todo sea string limpio
                        clean_record = self._sanitize_record(record)

                        self.ingest_record(clean_record, session)
                        count += 1
                        if count % 100 == 0: session.commit()
                    except json.JSONDecodeError:
                        errors_count += 1
                        continue # Salta lineas corruptas de JSON
                    except Exception as e:
                        # Logueamos error pero NO detenemos el proceso completo, solo esa linea
                        # logger.warning(f"Error en linea: {e}") 
                        errors_count += 1
                        session.rollback()
            
            session.commit()
            logger.info(f"✅ Finalizado {filepath.name}. Insertados: {count}, Errores/Saltados: {errors_count}")

        except Exception as e:
             logger.error(f"❌ Error fatal leyendo archivo {filepath.name}: {e}")

    def _sanitize_record(self, data):
        """
        Recursivamente limpia strings para asegurar compatibilidad UTF-8 perfecta.
        """
        if isinstance(data, dict):
            return {k: self._sanitize_record(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_record(v) for v in data]
        elif isinstance(data, str):
            # Normalizar unicode (quitar caracteres fantasma) y quitar espacios extra
            return data.strip()
        else:
            return data


    def ingest_record(self, data, session):
        # --- 1. Bodega ---
        wh_id = data.get("warehouse_id")
        if wh_id:
            session.execute(text("""
                INSERT INTO warehouses (warehouse_id, last_seen_at) 
                VALUES (:wid, NOW())
                ON CONFLICT (warehouse_id) DO UPDATE SET last_seen_at = NOW()
            """), {"wid": wh_id})

        # --- 2. Proveedor ---
        supp = data.get("supplier", {})
        if supp and supp.get("id"):
            session.execute(text("""
                INSERT INTO suppliers (supplier_id, name, store_name, plan_name, updated_at)
                VALUES (:sid, :name, :store, :plan, NOW())
                ON CONFLICT (supplier_id) DO UPDATE
                SET name = EXCLUDED.name, store_name = EXCLUDED.store_name, plan_name = EXCLUDED.plan_name, updated_at = NOW()
            """), {
                "sid": supp.get("id"),
                "name": supp.get("name"),
                "store": supp.get("store_name"),
                "plan": supp.get("plan_name")
            })

        # --- 3. Producto ---
        prod_id = data.get("id")
        if prod_id:
            session.execute(text("""
                INSERT INTO products (
                    product_id, supplier_id, sku, title, description,
                    sale_price, suggested_price, product_type, 
                    url_image_s3, updated_at
                ) VALUES (
                    :pid, :sid, :sku, :title, :desc,
                    :price, :sugg, :type, 
                    :img, NOW()
                )
                ON CONFLICT (product_id) DO UPDATE
                SET sale_price = EXCLUDED.sale_price,
                    suggested_price = EXCLUDED.suggested_price,
                    description = COALESCE(EXCLUDED.description, products.description),
                    updated_at = NOW(),
                    url_image_s3 = COALESCE(EXCLUDED.url_image_s3, products.url_image_s3)
            """), {
                "pid": prod_id,
                "sid": supp.get("id") if supp else None,
                "sku": data.get("sku"),
                "title": data.get("name"),
                "desc": data.get("description") or None, # <-- Send None if empty, so COALESCE keeps existing DB value
                "price": data.get("sale_price"),
                "sugg": data.get("suggested_price"),
                "type": data.get("type"),
                "img": self._extract_image(data)
            })

            # --- 4. Categorías ---
            self.process_categories(session, prod_id, data.get("categories", []))

            # --- 5. Stock ---
            if wh_id:
                try:
                    qty = int(data.get("stock") or 0)
                    session.execute(text("""
                        INSERT INTO product_stock_log (product_id, warehouse_id, stock_qty)
                        VALUES (:pid, :wid, :qty)
                    """), {"pid": prod_id, "wid": wh_id, "qty": qty})
                except: pass

    def _extract_image(self, data):
        # 1. Try processed field
        img = data.get("image_url")
        if img: return img

        # 2. Try raw gallery
        gallery = data.get("gallery", [])
        if gallery and isinstance(gallery, list):
            first = gallery[0]
            if isinstance(first, dict):
                raw = first.get("urlS3") or first.get("url")
                if raw:
                    # Cloudfront domain from scraper.py
                    return f"https://d39ru7awumhhs2.cloudfront.net/{quote(raw, safe='/')}"
        return None

    def _extract_category_name(self, item):
        if isinstance(item, str):
            return item
        if isinstance(item, dict):
            return item.get("name")
        return None

    def process_categories(self, session, prod_id, categories):
        if not categories or not isinstance(categories, list):
            return

        for item in categories:
            cat_name = self._extract_category_name(item)
            if not cat_name: continue
            
            cat_name = cat_name.strip()
            if not cat_name: continue
            
            # Insertar categoría si no existe
            try:
                session.execute(text("""
                    INSERT INTO categories (name)
                    VALUES (:name)
                    ON CONFLICT (name) DO NOTHING
                """), {"name": cat_name})
            except: pass
            
            # Obtener el ID y Relacionar
            try:
                result = session.execute(text("""
                    SELECT id FROM categories WHERE name = :name
                """), {"name": cat_name})
                row = result.fetchone()
                if row:
                    cat_id = row[0]
                    session.execute(text("""
                        INSERT INTO product_categories (product_id, category_id)
                        VALUES (:pid, :cid)
                        ON CONFLICT (product_id, category_id) DO NOTHING
                    """), {"pid": prod_id, "cid": cat_id})
            except: pass

    # Refactored ingest_record call for categories (replace logic inside ingest_record)
