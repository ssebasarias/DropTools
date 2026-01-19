"""
Módulo principal de scraping para Dropi (Django Command).
"""
import os
import logging
import sys
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback
from selenium.webdriver.remote.webdriver import WebDriver
from datetime import datetime
from urllib.parse import quote
import pathlib

# ─────── Cargar variables de entorno ───────
load_dotenv()

EMAIL       = os.getenv("DROPI_EMAIL")
PASSWORD    = os.getenv("DROPI_PASSWORD")
HEADLESS    = os.getenv("HEADLESS", "True").lower() in ("1", "true", "yes")
RAW_DIR_PATH = pathlib.Path(os.getenv("RAW_DIR", "raw_data"))
RAW_DIR_PATH.mkdir(parents=True, exist_ok=True)

# ─────── Configuración de Logs (Centralizada) ───────
# Creamos carpeta logs dentro del contenedor (montada a host)
LOG_DIR = pathlib.Path("/app/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("scraper")
logger.setLevel(logging.INFO)

# Formatter bonito
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# 1. File Handler (Para visualización en Frontend)
file_handler = logging.FileHandler(LOG_DIR / "scraper.log", encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 2. Console Handler (Para Docker standard logs)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# ─────── Helper Functions ───────

def build_driver() -> webdriver.Chrome:
    opts = Options()
    # Modo headless activado (ahorra RAM)
    if HEADLESS:
        opts.add_argument("--headless=new")
        logger.info("🔇 MODO HEADLESS ACTIVADO - Navegador oculto (ahorra RAM)")
    else:
        logger.info("🔍 MODO VISIBLE ACTIVADO - Navegador visible")
    opts.add_argument("--window-size=1920,1080")
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    
    # Docker friendly options
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    # 1. Intentar usar driver del sistema (Docker)
    system_driver = os.environ.get("CHROMEDRIVER")
    if system_driver and os.path.exists(system_driver):
        logger.info(f"Using system chromedriver: {system_driver}")
        service = Service(system_driver)
    else:
        # 2. Fallback a webdriver_manager
        logger.info("Using webdriver_manager...")
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)

    return webdriver.Chrome(service=service, options=opts)

def login(driver: webdriver.Chrome, timeout: int = 60) -> bool:
    try:
        logger.info("=" * 60)
        logger.info("🔐 INICIANDO PROCESO DE LOGIN")
        logger.info("=" * 60)
        
        logger.info("1) Abriendo página de login…")
        driver.get("https://app.dropi.co/login")
        logger.info(f"   ✅ Página cargada: {driver.current_url}")
        wait = WebDriverWait(driver, timeout)

        logger.info("2) Buscando campo de email...")
        email_el = wait.until(EC.visibility_of_element_located((By.NAME, "email")))
        logger.info("   ✅ Campo email encontrado")
        
        logger.info(f"   📧 Escribiendo email: {EMAIL}")
        email_el.clear()
        email_el.send_keys(EMAIL)
        logger.info("   ✅ Email ingresado")

        logger.info("   🔑 Buscando campo de password...")
        pwd_el = driver.find_element(By.NAME, "password")
        logger.info("   ✅ Campo password encontrado")
        
        logger.info("   🔑 Escribiendo password...")
        pwd_el.clear()
        pwd_el.send_keys(PASSWORD)
        logger.info("   ✅ Password ingresado")
        
        logger.info("   ⏎ Presionando ENTER para enviar...")
        pwd_el.send_keys(Keys.RETURN)
        logger.info("   ✅ Formulario enviado")

        logger.info("3) Esperando validación (token o redirección)...")
        # Esperar validación: Token en Storage O Redirección exitosa
        wait.until(lambda d: d.execute_script("return !!localStorage.getItem('DROPI_token')") or "/dashboard" in d.current_url)
        logger.info(f"   ✅ Validación exitosa - URL actual: {driver.current_url}")
        
        driver.get_log("performance") # Limpiar logs
        logger.info("✅ Login exitoso - Esperando 20s para que cargue completamente...")
        logger.info("   ⏳ Esperando... (ventana de carga de Dropi)")
        time.sleep(20)  # Aumentado a 20s para Docker (era 15s)
        logger.info("   ✅ Espera completada")
        
        # Screenshot para debugging en Docker
        try:
            screenshot_path = "/app/logs/01_after_login.png"
            driver.save_screenshot(screenshot_path)
            logger.info(f"   📸 Screenshot guardado: {screenshot_path}")
        except Exception as e:
            logger.warning(f"   ⚠️ No se pudo guardar screenshot: {e}")
        
        logger.info("=" * 60)
        return True
    except Exception as e:
        import traceback
        logger.error(f"Login fallido: {type(e).__name__}: {e}")
        try:
            logger.error(f"URL Failed: {driver.current_url}")
            text = driver.find_element(By.TAG_NAME, "body").text[:300].replace('\n', ' ')
            logger.error(f"Pantalla: {text}")
        except: pass
        logger.error(traceback.format_exc())
        return False

def navigate_to_catalog(driver: webdriver.Chrome, wait_time: int = 10) -> None:
    """
    Navega al catálogo DIRECTAMENTE por URL, esperando primero para asegurar sesión.
    
    Args:
        driver: Instancia de Chrome WebDriver
        wait_time: Tiempo de espera inicial antes de navegar
    """
    logger.info("=" * 60)
    logger.info("🗂️ NAVEGANDO AL CATÁLOGO (Direct URL)")
    logger.info("=" * 60)
    logger.info(f"⏳ Esperando {wait_time}s antes de navegar (ventana de carga)...")
    
    # Espera inicial para que la ventana de carga termine
    for i in range(wait_time):
        logger.info(f"   ⏱️ {i+1}/{wait_time} segundos...")
        time.sleep(1)
    logger.info("   ✅ Espera completada")
    
    try:
        # Navegación Directa
        target_url = "https://app.dropi.co/dashboard/search"
        logger.info(f"   🚀 Navegando directamente a: {target_url}")
        driver.get(target_url)
        
        wait = WebDriverWait(driver, 40) # 40s timeout para seguridad en Docker
        
        # Validar que estemos en la URL correcta
        # A veces Dropi redirecciona, así que aseguramos que se mantenga o cargue
        wait.until(EC.url_contains("/dashboard/search"))
        
        # Esperar carga de elementos (productos)
        logger.info("   ⏳ Esperando 15s adicionales para carga de lista de productos...")
        time.sleep(15)
        logger.info("   ✅ Catálogo cargado exitosamente (Direct URL)")
        
        # Screenshot del catálogo cargado
        try:
            screenshot_path = "/app/logs/04_catalog_loaded_direct.png"
            driver.save_screenshot(screenshot_path)
            logger.info(f"   📸 Screenshot guardado: {screenshot_path}")
        except Exception as e:
            logger.warning(f"   ⚠️ No se pudo guardar screenshot: {e}")
            
    except Exception as e:
        logger.error(f"❌ FALLÓ LA NAVEGACIÓN DIRECTA: {e}")
        
        # Screenshot del error
        try:
            screenshot_path = "/app/logs/ERROR_navigation.png"
            driver.save_screenshot(screenshot_path)
            logger.error(f"   📸 Screenshot de error guardado: {screenshot_path}")
        except:
            pass
        
        raise e
        



def grab_new_products(driver: WebDriver, seen: set) -> list:
    new = []
    logs = driver.get_log("performance")
    for entry in logs: 
        try:
            msg = json.loads(entry["message"])["message"]
            if msg.get("method") != "Network.responseReceived": continue
            
            url = msg["params"]["response"]["url"]
            if "/api/products/v4/index" not in url: continue

            request_id = msg["params"]["requestId"]
            body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})["body"]
            payload = json.loads(body)
            objs = payload.get("objects") or payload.get("data", {}).get("objects", [])
            
            for p in objs:
                pid = p.get("id")
                if pid and pid not in seen:
                    seen.add(pid)
                    new.append(p)
        except:
            continue
    return new

def scroll_to_bottom(driver: WebDriver) -> None:
    driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
    time.sleep(1)
    # Scroll en contenedor interno si existe
    driver.execute_script("""
        var c = document.querySelector('.simplebar-content') || document.querySelector('.products-list');
        if (c) c.scrollTop = c.scrollHeight;
    """)

def click_show_more(driver: WebDriver) -> bool:
    try:
        btn = driver.find_element(By.XPATH, "//div[contains(text(),'Mostrar más productos')]")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        driver.execute_script("arguments[0].click();", btn)
        return True
    except:
        return False

# ─────── Django Command ───────

class Command(BaseCommand):
    help = 'Scraper de Dropi (Daemon)'
    
    def generate_batch_filename(self):
        """Genera nombre de archivo con timestamp para fácil lectura y ordenamiento"""
        fname = f"raw_products_{datetime.utcnow():%Y%m%d_%H%M%S}.jsonl"
        return RAW_DIR_PATH / fname

    def handle(self, *args, **options):
        logger.info("🚀 SCRAPER DAEMON INICIADO (Modo Infinito)")
        
        while True:
            driver = None
            try:
                logger.info("🔄 Iniciando ciclo de scraping...")
                driver = build_driver()
                driver.execute_cdp_cmd("Network.enable", {})

                if not login(driver):
                    raise Exception("Login fallido")

                # Intentar navegar al catálogo con retry
                navigation_success = False
                for attempt, wait_time in enumerate([25, 30], start=1):  # Aumentado: 25s y 30s (era 15s y 20s)
                    try:
                        logger.info(f"📍 Intento {attempt} de navegación al catálogo (espera: {wait_time}s)...")
                        navigate_to_catalog(driver, wait_time=wait_time)
                        navigation_success = True
                        break
                    except Exception as nav_error:
                        if attempt == 1:
                            logger.warning(f"⚠️ Primer intento falló. Reintentando con 30s de espera...")
                            # Cerrar sesión y volver a intentar
                            try:
                                driver.quit()
                            except:
                                pass
                            time.sleep(5)
                            driver = build_driver()
                            driver.execute_cdp_cmd("Network.enable", {})
                            if not login(driver):
                                raise Exception("Login fallido en retry")
                        else:
                            logger.error(f"❌ Navegación falló después de {attempt} intentos")
                            raise nav_error
                
                if not navigation_success:
                    raise Exception("No se pudo navegar al catálogo")
                
                seen = set()
                consecutive_no_button = 0
                
                # Batch control vars
                BATCH_TIME_LIMIT = 300  # 5 minutos
                
                # Variables para control de archivo
                current_batch_file = None
                batch_file_handle = None
                batch_start_time = None
                batch_count = 0

                while True:  # Main Scraping Loop (Chrome session active)
                    # 1. Scraping Logic (capturar productos)
                    nuevos = grab_new_products(driver, seen)
                    
                    if nuevos:
                        # Si es el primer producto del batch, abrir nuevo archivo e iniciar cronómetro
                        if batch_file_handle is None:
                            current_batch_file = self.generate_batch_filename()
                            batch_file_handle = open(current_batch_file, 'a', encoding='utf-8')
                            batch_start_time = time.time()
                            batch_count = 0
                            logger.info(f"📂 Nuevo archivo abierto: {current_batch_file.name}")
                        
                        # Escribir productos al archivo
                        for p in nuevos:
                            record = self.process_product(p)
                            batch_file_handle.write(json.dumps(record, ensure_ascii=False) + '\n')
                            batch_file_handle.flush()
                            batch_count += 1
                        
                        logger.info(f"📦 +{len(nuevos)} productos (Lote: {batch_count} | Total: {len(seen)})")
                        
                        # 2. Check Rotation Conditions (solo si hay archivo abierto)
                        if batch_start_time is not None:
                            elapsed = time.time() - batch_start_time
                            if elapsed > BATCH_TIME_LIMIT:
                                logger.info(f"⏱️ Rotando archivo por tiempo ({int(elapsed)}s, {batch_count} productos)...")
                                # Cerrar archivo actual
                                if batch_file_handle:
                                    batch_file_handle.close()
                                    logger.info(f"✅ Archivo cerrado: {current_batch_file.name}")
                                # Resetear variables para el próximo batch
                                batch_file_handle = None
                                batch_start_time = None
                                current_batch_file = None
                                batch_count = 0

                    # 3. Navigation
                    scroll_to_bottom(driver)
                    found = False
                    for _ in range(3):
                        if click_show_more(driver):
                            found = True
                            break
                        time.sleep(1)
                    
                    if not found:
                        consecutive_no_button += 1
                        if consecutive_no_button >= 5:
                            logger.info("🛑 Fin del catálogo o error. Reiniciando sesión...")
                            # Cerrar archivo si está abierto
                            if batch_file_handle:
                                batch_file_handle.close()
                                logger.info(f"✅ Archivo cerrado antes de reiniciar: {current_batch_file.name}")
                            raise Exception("End of catalog or navigation stuck")  # Force restart driver
                    else:
                        consecutive_no_button = 0
                    
                    time.sleep(1)
                    
                    # Check for Driver Restart (Long running maintenance)
                    if len(seen) % 1000 == 0 and len(seen) > 0:
                        logger.info(f"🔄 Reiniciando Chrome (mantenimiento preventivo - {len(seen)} productos)...")
                        # Cerrar archivo si está abierto
                        if batch_file_handle:
                            batch_file_handle.close()
                            logger.info(f"✅ Archivo cerrado antes de mantenimiento: {current_batch_file.name}")
                        break  # Break Main Loop -> Rebuild Driver

            except KeyboardInterrupt:
                logger.info("⏹️ Deteniendo scraper (Ctrl+C)...")
                break
            except Exception as e:
                error_msg = str(e)
                logger.error(f"💥 Error: {error_msg}")
                
                # Logging especial para errores conocidos
                if "tab crashed" in error_msg.lower():
                    logger.error("💥 Chrome crash detectado. Reiniciando navegador...")
                elif "session deleted" in error_msg.lower():
                    logger.error("💥 Sesión perdida. Reiniciando navegador...")
                
                logger.info("🔄 Reiniciando en 60 segundos...")
                time.sleep(60)
            finally:
                if driver:
                    try:
                        driver.quit()
                        logger.info("✅ Driver cerrado correctamente")
                    except Exception as e:
                        logger.warning(f"⚠️ Error al cerrar driver: {e}")
                    driver = None

    def process_product(self, p):
        # Lógica de extracción simplificada
        img_url = None
        gallery = p.get('gallery', [])
        if gallery:
            raw = gallery[0].get('urlS3') or gallery[0].get('url')
            if raw: img_url = f"https://d39ru7awumhhs2.cloudfront.net/{quote(raw, safe='/')}"

        wh_list = p.get('warehouse_product', [])
        wh_id = wh_list[0].get('warehouse_id') if wh_list else None
        stock = wh_list[0].get('stock', 0) if wh_list else 0

        return {
            "id": p.get('id'),
            "sku": p.get('sku'),
            "name": p.get('name', 'Sin Nombre'),
            "description": p.get('description', ''), # <-- Contexto para IA
            "type": p.get('type', 'SIMPLE'),
            "sale_price": p.get('sale_price'),
            "suggested_price": p.get('suggested_price'),
            "supplier": p.get('user', {}),
            "warehouse_id": wh_id,
            "stock": stock,
            "image_url": img_url,
            "categories": [c.get('name') for c in p.get('categories', [])],
            "capture_timestamp": datetime.utcnow().isoformat(),
            "raw_json": p
        }