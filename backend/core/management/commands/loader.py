"""
Módulo de carga ETL (Django Command).
"""
import os
import json
import logging
import pathlib
import time
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("loader")
load_dotenv()

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
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                if not line.strip(): continue
                try:
                    record = json.loads(line)
                    self.ingest_record(record, session)
                    count += 1
                    if count % 100 == 0: session.commit()
                except Exception:
                    errors_count += 1
                    session.rollback()
        
        session.commit()
        logger.info(f"Done. Valid: {count}, Errors: {errors_count}")

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
                    product_id, supplier_id, sku, title, 
                    sale_price, suggested_price, product_type, 
                    url_image_s3, updated_at
                ) VALUES (
                    :pid, :sid, :sku, :title, 
                    :price, :sugg, :type, 
                    :img, NOW()
                )
                ON CONFLICT (product_id) DO UPDATE
                SET sale_price = EXCLUDED.sale_price,
                    suggested_price = EXCLUDED.suggested_price,
                    updated_at = NOW(),
                    url_image_s3 = COALESCE(EXCLUDED.url_image_s3, products.url_image_s3)
            """), {
                "pid": prod_id,
                "sid": supp.get("id") if supp else None,
                "sku": data.get("sku"),
                "title": data.get("name"),
                "price": data.get("sale_price"),
                "sugg": data.get("suggested_price"),
                "type": data.get("type"),
                "img": data.get("image_url")
            })

            if wh_id:
                try:
                    qty = int(data.get("stock") or 0)
                    session.execute(text("""
                        INSERT INTO product_stock_log (product_id, warehouse_id, stock_qty)
                        VALUES (:pid, :wid, :qty)
                    """), {"pid": prod_id, "wid": wh_id, "qty": qty})
                except: pass
