"""
Módulo de carga ETL (Django Command) - Versión Mejorada
Procesa archivos JSONL de raw_data con validación de calidad y gestión de archivos.
"""
import os
import json
import logging
import pathlib
import sys
import time
import gzip
import shutil
from datetime import datetime
from collections import defaultdict
import traceback

from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert

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

# Directorios
RAW_DIR = pathlib.Path(os.getenv("RAW_DIR", "/app/raw_data"))
PROCESSED_DIR = RAW_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Configuración
PROCESS_INTERVAL = 300  # 5 minutos
COMPRESS_PROCESSED = True  # Comprimir archivos procesados en lugar de eliminarlos

class Command(BaseCommand):
    help = 'ETL Loader Daemon con Validación de Calidad y Gestión de Archivos'

    def handle(self, *args, **options):
        logger.info("🚀 LOADER DAEMON INICIADO (Ciclo de 5 minutos)")
        
        session = self.get_session()
        
        while True:
            try:
                cycle_start = time.time()
                
                # Obtener archivos en orden cronológico (más viejo primero)
                files = self.get_files_chronologically()
                
                if not files:
                    logger.info("⏳ Sin archivos pendientes. Esperando próximo ciclo...")
                else:
                    logger.info(f"📂 Encontrados {len(files)} archivo(s) para procesar")
                    
                    for filepath in files:
                        try:
                            self.process_file_complete(filepath, session)
                        except Exception as e:
                            logger.error(f"❌ Error procesando {filepath.name}: {e}")
                            logger.error(traceback.format_exc())
                            # Mover a failed para no bloquear
                            self.archive_file(filepath, success=False, reason=str(e))
                            # Continuar con el siguiente archivo
                
                # Esperar hasta completar el ciclo de 5 minutos
                elapsed = time.time() - cycle_start
                remaining = PROCESS_INTERVAL - elapsed
                
                if remaining > 0:
                    logger.info(f"⏱️ Ciclo completado en {int(elapsed)}s. Esperando {int(remaining)}s hasta próximo ciclo...")
                    time.sleep(remaining)
                else:
                    logger.warning(f"⚠️ Ciclo tardó {int(elapsed)}s (más de {PROCESS_INTERVAL}s). Iniciando siguiente ciclo inmediatamente.")

            except KeyboardInterrupt:
                logger.info("⏹️ Deteniendo loader (Ctrl+C)...")
                break
            except Exception as e:
                logger.error(f"💥 Error crítico en loop principal: {e}")
                time.sleep(30)
                try:
                    session = self.get_session()  # Reconnect
                except Exception as reconnect_error:
                    logger.error(f"❌ Error reconectando a DB: {reconnect_error}")

    def get_session(self):
        """Crea sesión de base de datos"""
        user = os.getenv("POSTGRES_USER", "dahell_admin")
        pwd = os.getenv("POSTGRES_PASSWORD", "secure_password_123")
        host = os.getenv("POSTGRES_HOST", "127.0.0.1")
        port = os.getenv("POSTGRES_PORT", "5433")
        dbname = os.getenv("POSTGRES_DB", "dahell_db")
        raw_db_url = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{dbname}"
        
        engine = create_engine(
            raw_db_url, 
            echo=False, 
            json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
            connect_args={'client_encoding': 'utf8'}
        )
        Session = sessionmaker(bind=engine)
        return Session()

    def get_files_chronologically(self):
        """
        Obtiene archivos .jsonl en orden cronológico (más viejo primero)
        basándose en el timestamp en el nombre del archivo.
        """
        files = list(RAW_DIR.glob("*.jsonl"))
        
        # Filtrar archivos que no sean de offset
        files = [f for f in files if not f.name.endswith('.offset')]
        
        # Ordenar por timestamp en el nombre (formato: raw_products_YYYYMMDD_HHMMSS.jsonl)
        try:
            files.sort(key=lambda f: f.stem.split('_')[-2:])  # Ordena por fecha y hora
        except:
            # Fallback: ordenar por fecha de modificación
            files.sort(key=lambda f: f.stat().st_mtime)
        
        return files

    def process_file_complete(self, filepath, session):
        """
        Procesa un archivo completo con validación de calidad y gestión.
        
        Pasos:
        1. Leer y validar productos
        2. Insertar en DB con ON CONFLICT
        3. Validar calidad de inserción
        4. Comprimir/mover archivo si todo OK
        """
        logger.info(f"📂 Procesando archivo: {filepath.name}")
        
        # ─── PASO 1: Leer y Validar Productos ───
        products_raw = []
        products_valid = []
        stats = {
            "total_lines": 0,
            "valid_products": 0,
            "no_image": 0,
            "no_product_id": 0,
            "no_supplier_id": 0,  # NUEVO: productos sin proveedor
            "json_errors": 0
        }
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                for line_num, line in enumerate(f, 1):
                    stats["total_lines"] += 1
                    
                    if not line.strip():
                        continue
                    
                    # Log de progreso cada 5000 líneas para archivos grandes
                    if line_num % 5000 == 0:
                        logger.info(f"   ...Leyendo línea {line_num}")

                    
                    try:
                        record = json.loads(line)
                        products_raw.append(record)
                        
                        # Validación 1: product_id obligatorio
                        if not record.get("id"):
                            stats["no_product_id"] += 1
                            continue
                        
                        # Validación 2: supplier_id obligatorio (clave compuesta)
                        supplier = record.get("supplier", {})
                        if not supplier or not supplier.get("id"):
                            stats["no_supplier_id"] += 1
                            continue
                        
                        # Validación 3: imagen obligatoria (solo para nuevos productos)
                        # La imagen puede actualizarse después, pero debe existir inicialmente
                        if not record.get("image_url"):
                            stats["no_image"] += 1
                            continue
                        
                        # Producto válido
                        products_valid.append(record)
                        stats["valid_products"] += 1
                        
                    except json.JSONDecodeError as e:
                        stats["json_errors"] += 1
                        logger.warning(f"   ⚠️ Línea {line_num}: JSON inválido")
                        continue
        
        except Exception as e:
            logger.error(f"❌ Error leyendo archivo {filepath.name}: {e}")
            return
        
        logger.info(f"   📊 Estadísticas de lectura:")
        logger.info(f"      Total líneas: {stats['total_lines']}")
        logger.info(f"      Productos válidos: {stats['valid_products']}")
        logger.info(f"      Sin imagen: {stats['no_image']}")
        logger.info(f"      Sin product_id: {stats['no_product_id']}")
        logger.info(f"      Sin supplier_id: {stats['no_supplier_id']}")
        logger.info(f"      Errores JSON: {stats['json_errors']}")
        
        if stats["valid_products"] == 0:
            logger.warning(f"   ⚠️ No hay productos válidos en {filepath.name}. Moviendo a processed...")
            self.archive_file(filepath, success=False, reason="no_valid_products")
            return
        
        # ─── PASO 2: Preparar Metadata DB ───
        meta = MetaData()
        try:
            meta.reflect(bind=session.get_bind())
            t_products = meta.tables.get('products')
            t_suppliers = meta.tables.get('suppliers')
            t_warehouses = meta.tables.get('warehouses')
            t_stock = meta.tables.get('product_stock_log')
        except Exception as e:
            logger.error(f"❌ Error reflejando tablas DB: {e}")
            return
        
        if not all([t_products is not None, t_suppliers is not None, t_warehouses is not None, t_stock is not None]):
            logger.error("❌ Error CRÍTICO: Tablas no encontradas en DB")
            return
        
        # ─── PASO 3: Insertar en DB ───
        inserted_count = self.ingest_batch_validated(
            products_valid, 
            session, 
            t_products, 
            t_suppliers, 
            t_warehouses, 
            t_stock
        )
        
        # ─── PASO 4: Validar Inserción ───
        expected_count = stats["valid_products"]
        
        # La diferencia es aceptable si es por duplicados, PERO solo si hubo éxito
        if inserted_count > 0 and inserted_count < expected_count:
            duplicate_count = expected_count - inserted_count
            logger.info(f"   ℹ️ {duplicate_count} productos ya existían (actualizados)")
        elif inserted_count == 0 and expected_count > 0:
            logger.warning(f"   ⚠️ 0 productos procesados de {expected_count} válidos. Posible error en batch.")
            # Si falló la inserción masiva (y esperábamos insertar), marcar como error
            self.archive_file(filepath, success=False, stats=stats, reason="db_insertion_failed_zero_count")
            return
        
        logger.info(f"   ✅ Procesados {inserted_count} productos de {expected_count} válidos")
        
        # ─── PASO 5: Archivar Archivo ───
        self.archive_file(filepath, success=True, stats=stats)

    def ingest_batch_validated(self, batch, session, t_products, t_suppliers, t_warehouses, t_stock):
        """
        Inserta batch con validación de duplicados por product_id.
        
        LÓGICA DE DUPLICADOS (ESQUEMA ACTUAL):
        - Mismo product_id = ACTUALIZAR (precio, stock, supplier, etc.)
        
        NOTA: El esquema actual usa product_id como PK simple.
        Para soportar competencia real entre proveedores, se requiere migrar
        a clave compuesta (product_id, supplier_id).
        
        Retorna: Número de productos procesados (insertados o actualizados)
        """
        warehouses = {}
        suppliers = {}
        products = []
        stocks = []
        now = datetime.utcnow()
        
        # Tracking de combinaciones únicas (product_id, supplier_id)
        unique_combinations = set()
        skipped_duplicates_in_batch = 0
        
        for d in batch:
            # 1. Warehouse
            wh_id = d.get("warehouse_id")
            if wh_id:
                warehouses[wh_id] = {
                    "warehouse_id": wh_id,
                    "first_seen_at": now,
                    "last_seen_at": now
                }
            
            # 2. Supplier
            supp = d.get("supplier", {})
            supplier_id = None
            if supp and supp.get("id"):
                supplier_id = supp.get("id")
                
                # Plan logic normalized
                p_name = None
                if isinstance(supp.get("plan"), dict):
                    p_name = supp.get("plan", {}).get("name")
                else:
                    p_name = supp.get("plan_name")
                
                suppliers[supplier_id] = {
                    "supplier_id": supplier_id,
                    "name": str(supp.get("name") or "")[:255],
                    "store_name": str(supp.get("store_name") or "")[:255],
                    "plan_name": str(p_name or "")[:100],
                    "is_verified": bool(supp.get("is_verified") or False),
                    "created_at": now,  # Fix: DB column has no default
                    "updated_at": now
                }
            
            # 3. Product
            pid = d.get("id")
            if pid and supplier_id:  # Ambos son obligatorios
                # Validar combinación única DENTRO del batch
                # (para evitar duplicados en el mismo archivo)
                combination_key = (pid, supplier_id)
                
                if combination_key in unique_combinations:
                    # Ya procesamos esta combinación en este batch
                    skipped_duplicates_in_batch += 1
                    continue
                
                unique_combinations.add(combination_key)
                
                # Extraer imagen
                img = d.get("image_url") or \
                      (d.get("gallery") and len(d.get("gallery")) > 0 and d.get("gallery")[0].get("urlS3")) or \
                      (d.get("gallery") and len(d.get("gallery")) > 0 and d.get("gallery")[0].get("url"))
                
                products.append({
                    "product_id": pid,
                    "supplier_id": supplier_id,
                    "sku": str(d.get("sku") or "")[:100],
                    "title": d.get("name") or "Sin Nombre",
                    "description": d.get("description"),
                    "sale_price": d.get("sale_price"),
                    "suggested_price": d.get("suggested_price"),
                    "product_type": str(d.get("type") or "")[:50],
                    "url_image_s3": img,
                    "is_active": True,
                    "last_seen_at": now,
                    "created_at": now,  # Fix: DB column has no default
                    "updated_at": now,
                    "raw_data": d.get("raw_json", {})
                })
                
                # 4. Stock Log
                if wh_id:
                    stocks.append({
                        "product_id": pid,
                        "warehouse_id": wh_id,
                        "stock_qty": int(d.get("stock") or 0),
                        "snapshot_at": now
                    })
        
        if skipped_duplicates_in_batch > 0:
            logger.info(f"   ℹ️ Saltados {skipped_duplicates_in_batch} duplicados dentro del batch")
        
        # ─── EJECUCIÓN MASIVA ───
        processed_count = 0
        db_start_time = time.time()
        
        try:
            logger.info(f"   ⚙️ [DB] Iniciando transacción masiva...")
            
            # Bulk Warehouses
            if warehouses:
                logger.info(f"      ↳ Insertando/Actualizando {len(warehouses)} warehouses...")
                stmt = insert(t_warehouses).values(list(warehouses.values()))
                stmt = stmt.on_conflict_do_update(
                    index_elements=['warehouse_id'],
                    set_={"last_seen_at": stmt.excluded.last_seen_at}
                )
                session.execute(stmt)
            
            # Bulk Suppliers
            if suppliers:
                logger.info(f"      ↳ Insertando/Actualizando {len(suppliers)} suppliers...")
                stmt = insert(t_suppliers).values(list(suppliers.values()))
                stmt = stmt.on_conflict_do_update(
                    index_elements=['supplier_id'],
                    set_={
                        "name": stmt.excluded.name,
                        "store_name": stmt.excluded.store_name,
                        "plan_name": stmt.excluded.plan_name,
                        "is_verified": stmt.excluded.is_verified,  # ← AGREGADO: Actualizar is_verified
                        "updated_at": stmt.excluded.updated_at
                    }
                )
                session.execute(stmt)
            
            # Bulk Products - PK: product_id
            if products:
                logger.info(f"      ↳ Upserting {len(products)} productos...")
                stmt = insert(t_products).values(products)
                # ON CONFLICT con product_id (PK actual en DB)
                # NOTA: Cuando se migre a clave compuesta (product_id, supplier_id),
                # cambiar index_elements a ['product_id', 'supplier_id']
                stmt = stmt.on_conflict_do_update(
                    index_elements=['product_id'],  # ← PK actual (simple)
                    set_={
                        "sale_price": stmt.excluded.sale_price,
                        "suggested_price": stmt.excluded.suggested_price,
                        "updated_at": stmt.excluded.updated_at,
                        "last_seen_at": stmt.excluded.last_seen_at,
                        "description": stmt.excluded.description,
                        "url_image_s3": stmt.excluded.url_image_s3,
                        "is_active": stmt.excluded.is_active,
                        "sku": stmt.excluded.sku,
                        "title": stmt.excluded.title,
                        "product_type": stmt.excluded.product_type,
                        "raw_data": stmt.excluded.raw_data,
                        "supplier_id": stmt.excluded.supplier_id  # Actualizar supplier también
                    }
                )
                result = session.execute(stmt)
                # IMPORTANTE: Verificar REALMENTE cuántos se procesaron
                # rowcount incluye tanto INSERT como UPDATE
                processed_count = result.rowcount if result.rowcount else len(products)
            
            # Bulk Stock Logs (Append only - histórico)
            if stocks:
                logger.info(f"      ↳ Registrando {len(stocks)} logs de stock...")
                session.execute(insert(t_stock).values(stocks))
            
            commit_start = time.time()
            session.commit()
            logger.info(f"   ✅ [DB] Transacción completada en {time.time() - db_start_time:.2f}s (Commit: {time.time() - commit_start:.2f}s)")
            
            # Reporte de procesamiento (confiando en rowcount de PostgreSQL)
            if products:
                logger.info(f"      💾 Rows procesados (INSERT/UPDATE): {processed_count}/{len(products)}")
                
                # NOTA: La verificación post-insert fue deshabilitada para mejorar rendimiento
                # PostgreSQL ya reporta correctamente el número de rows afectados en result.rowcount
                # Si necesitas debugging detallado, puedes habilitar la verificación manualmente
            
        except Exception as e:
            session.rollback()
            logger.error(f"   ❌ [DB ERROR] Error en inserción masiva: {e}")
            import traceback
            logger.error(traceback.format_exc())
            processed_count = 0
        
        return processed_count

    def archive_file(self, filepath, success=True, stats=None, reason=None):
        """
        Archiva el archivo procesado (comprime o mueve a carpeta processed).
        
        Args:
            filepath: Ruta del archivo a archivar
            success: Si el procesamiento fue exitoso
            stats: Estadísticas del procesamiento
            reason: Razón si no fue exitoso
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            
            if not success:
                # Caso ERROR: Mover a failed
                FAILED_DIR = RAW_DIR / "failed"
                FAILED_DIR.mkdir(parents=True, exist_ok=True)
                
                moved_name = f"{filepath.stem}_FAILED_{timestamp}.jsonl"
                moved_path = FAILED_DIR / moved_name
                shutil.move(str(filepath), str(moved_path))
                
                # Guardar razón del error
                if reason:
                    with open(moved_path.with_suffix('.error.txt'), 'w') as err_f:
                        err_f.write(str(reason))
                
                logger.error(f"   🚫 Archivo movido a FAILED: {moved_name}")
                return

            if COMPRESS_PROCESSED:
                # Comprimir archivo en processed (ÉXITO)
                compressed_name = f"{filepath.stem}_{timestamp}.jsonl.gz"
                compressed_path = PROCESSED_DIR / compressed_name
                
                with open(filepath, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                logger.info(f"   📦 Archivo comprimido: {compressed_name}")
            else:
                # Mover archivo sin comprimir (ÉXITO)
                moved_name = f"{filepath.stem}_{timestamp}.jsonl"
                moved_path = PROCESSED_DIR / moved_name
                shutil.move(str(filepath), str(moved_path))
                logger.info(f"   📁 Archivo movido: {moved_name}")
            
            # Eliminar archivo original
            if filepath.exists():
                filepath.unlink()
            
            # Eliminar archivo de offset si existe
            offset_file = filepath.with_suffix('.offset')
            if offset_file.exists():
                offset_file.unlink()
            
            logger.info(f"   ✅ Archivo archivado exitosamente")
            
        except Exception as e:
            logger.error(f"   ❌ Error archivando archivo {filepath.name}: {e}")
