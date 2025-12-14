"""
Módulo principal de scraping para Dropi (Django Command).
"""
import os
import logging
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─────── Helper Functions ───────

def jsonl_path():
    fname = f"raw_products_{datetime.utcnow():%Y%m%d}.jsonl"
    return RAW_DIR_PATH / fname

def build_driver() -> webdriver.Chrome:
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    
    # Docker friendly options
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    driver_path = ChromeDriverManager().install()
    service = Service(driver_path)
    return webdriver.Chrome(service=service, options=opts)

def login(driver: webdriver.Chrome, timeout: int = 30) -> bool:
    try:
        logger.info("1) Abriendo página de login…")
        driver.get("https://app.dropi.co/login")
        wait = WebDriverWait(driver, timeout)

        logger.info("2) Escribiendo credenciales...")
        email_el = wait.until(EC.visibility_of_element_located((By.NAME, "email")))
        email_el.clear()
        email_el.send_keys(EMAIL)

        pwd_el = driver.find_element(By.NAME, "password")
        pwd_el.clear()
        pwd_el.send_keys(PASSWORD)
        pwd_el.send_keys(Keys.RETURN)

        logger.info("3) Esperando token...")
        wait.until(lambda d: d.execute_script("return !!localStorage.getItem('DROPI_token')"))
        
        driver.get_log("performance") # Limpiar logs
        logger.info("✅ Login exitoso")
        return True
    except Exception as e:
        logger.error(f"Login fallido: {e}")
        return False

def navigate_to_catalog(driver: webdriver.Chrome) -> None:
    logger.info("4) Navegando al catálogo...")
    time.sleep(5)
    wait = WebDriverWait(driver, 20)
    
    # Clic en "Productos"
    try:
        prod_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[normalize-space()='Productos']/ancestor::a")))
        prod_btn.click()
        time.sleep(1)
        
        # Clic en "Catálogo"
        cat_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href='/dashboard/search' and normalize-space()='Catálogo']")))
        cat_btn.click()
        
        time.sleep(5)
        logger.info("🔍 Catálogo abierto.")
    except Exception as e:
        logger.warning(f"Error navegando menú: {e}. Intentando ir directo a URL...")
        driver.get("https://app.dropi.co/dashboard/search")
        time.sleep(5)

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

    def handle(self, *args, **options):
        self.stdout.write("🚀 SCRAPER DAEMON INICIADO (Modo Infinito)")
        
        while True:
            driver = None
            try:
                self.stdout.write("🔄 Iniciando ciclo de scraping...")
                driver = build_driver()
                driver.execute_cdp_cmd("Network.enable", {})

                if not login(driver):
                    raise Exception("Login fallido")

                navigate_to_catalog(driver)
                
                seen = set()
                consecutive_no_button = 0

                with open(jsonl_path(), 'a', encoding='utf-8') as f:
                    while True:
                        nuevos = grab_new_products(driver, seen)
                        if nuevos:
                            for p in nuevos:
                                record = self.process_product(p)
                                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                                f.flush()
                            self.stdout.write(f"📦 +{len(nuevos)} productos (Total: {len(seen)})")
                        
                        # Navegación
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
                                self.stdout.write("🛑 Fin del catálogo o error. Reiniciando...")
                                break
                        else:
                            consecutive_no_button = 0
                        
                        time.sleep(1)

            except Exception as e:
                self.stderr.write(f"💥 Error: {e}")
                time.sleep(60)
            finally:
                if driver: driver.quit()

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