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

# Modificado para apuntar a la ruta correcta en Docker
RAW_DIR = pathlib.Path(os.getenv("RAW_DIR", "/app/raw_data"))

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
        logger.info(f"📂 Procesando: {filepath.name}")
        
        stats = {"ok": 0, "error": 0, "total": 0}
        
        # Estrategia de lectura robusta
        encoding_strategy = 'utf-8'
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                f.read(1024)
        except UnicodeDecodeError:
             encoding_strategy = 'latin-1'

        try:
            with open(filepath, 'r', encoding=encoding_strategy, errors='replace') as f:
                for line in f:
                    if not line.strip(): continue
                    stats["total"] += 1
                    
                    try:
                        record = json.loads(line)
                        self.ingest_record(record, session)
                        stats["ok"] += 1
                        
                        # Commit por lotes
                        if stats["ok"] % 100 == 0: 
                            session.commit()
                            self.print_batch_summary(filepath.name, stats)
                            
                    except Exception as e:
                        # Si es error de DB, rollback y cuenta como error sin ensuciar log
                        # La mayoria son Transaction Aborted o Datos Sucios.
                        stats["error"] += 1
                        session.rollback()

            session.commit()
            self.print_batch_summary(filepath.name, stats, final=True)

        except Exception as e:
            logger.error(f"❌ Error fatal en archivo {filepath.name}: {e}")

    def print_batch_summary(self, filename, stats, final=False):
        """Imprime una tabla bonita en el log"""
        icon = "🏁" if final else "📦"
        status = "COMPLETADO" if final else "EN PROGRESO"
        
        msg = (
            f"\n{icon} Lote {filename} [{status}]\n"
            f"✅ Insertados/Actualizados: {stats['ok']}\n"
            f"⚠️  Omitidos (Errores/Sucios): {stats['error']}\n"
            f"----------------------------------------"
        )
        logger.info(msg)


    def ingest_record(self, data, session):
        # --- 1. Bodega ---
        wh_id = data.get("warehouse_id")
        if wh_id:
            try:
                session.execute(text("""
                    INSERT INTO warehouses (warehouse_id, first_seen_at, last_seen_at) 
                    VALUES (:wid, NOW(), NOW())
                    ON CONFLICT (warehouse_id) DO UPDATE SET last_seen_at = NOW()
                """), {"wid": wh_id})
            except Exception:
                pass 

        # --- 2. Proveedor ---
        supp = data.get("supplier", {})
        if supp and supp.get("id"):
            p_name = None
            if isinstance(supp.get("plan"), dict):
                p_name = supp.get("plan", {}).get("name")
            else:
                p_name = supp.get("plan_name")

            session.execute(text("""
                INSERT INTO suppliers (supplier_id, name, store_name, plan_name, is_verified, created_at, updated_at)
                VALUES (:sid, :name, :store, :plan, FALSE, NOW(), NOW())
                ON CONFLICT (supplier_id) DO UPDATE
                SET name = EXCLUDED.name, store_name = EXCLUDED.store_name, plan_name = EXCLUDED.plan_name, updated_at = NOW()
            """), {
                "sid": supp.get("id"),
                "name": str(supp.get("name") or "")[:255],
                "store": str(supp.get("store_name") or "")[:255],
                "plan": str(p_name or "")[:100]
            })

        # --- 3. Producto ---
        prod_id = data.get("id")
        if prod_id:
            session.execute(text("""
                INSERT INTO products (
                    product_id, supplier_id, sku, title, description,
                    sale_price, suggested_price, product_type, 
                    url_image_s3, is_active, created_at, updated_at
                ) VALUES (
                    :pid, :sid, :sku, :title, :desc,
                    :price, :sugg, :type, 
                    :img, TRUE, NOW(), NOW()
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
                "sku": str(data.get("sku") or "")[:100],
                "title": data.get("name") or "Sin Nombre",
                "desc": data.get("description"),
                "price": data.get("sale_price"),
                "sugg": data.get("suggested_price"),
                "type": str(data.get("type") or "")[:50],
                "img": data.get("image_url") 
                       or (data.get("gallery") and data.get("gallery")[0].get("urlS3"))
                       or (data.get("gallery") and data.get("gallery")[0].get("url"))
            })

            # --- 4. Stock ---
            if wh_id:
                try:
                    qty = int(data.get("stock") or 0)
                    session.execute(text("""
                        INSERT INTO product_stock_log (product_id, warehouse_id, stock_qty)
                        VALUES (:pid, :wid, :qty)
                    """), {"pid": prod_id, "wid": wh_id, "qty": qty})
                except: pass
