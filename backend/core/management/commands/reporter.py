"""
Bot de Reportes Automáticos para Dropi
Este bot automatiza la generación de observaciones en Dropi para productos sin movimiento.
"""

import os
import time
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
import glob

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException,
    ElementClickInterceptedException
)
from django.core.management.base import BaseCommand
from django.conf import settings


class DropiReporterBot:
    """Bot para automatizar reportes en Dropi"""
    
    # Credenciales
    DROPI_EMAIL = "dahellonline@gmail.com"
    DROPI_PASSWORD = "Bigotes2001@"
    DROPI_URL = "https://app.dropi.co/login"
    
    # Estados válidos para procesar (según filtro de Excel)
    VALID_STATES = [
        "BODEGA DESTINO",
        "DESPACHADA",
        "EN BODEGA TRANSPORTADORA",
        "EN BODEGA ORIGEN",
        "EN TRANSITO",
        "EN CAMINO",
        "EN DESPACHO",
        "EN PROCESAMIENTO",
        "EN PROCESO DE DEVOLUCION",
        "EN REPARTO",
        "EN RUTA",
        "ENTREGADA A CONEXIONES",
        "ENTREGADO A TRANSPORTADORA",
        "NOVEDAD SOLUCIONADA",
        "RECOGIDO POR DROPI",
        "TELEMERCADEO"
    ]
    
    # Diccionario de textos de observación variados para evitar detección como spam
    OBSERVATION_TEXTS = [
        "Pedido sin movimiento por mucho tiempo, favor salir a reparto urgente.",
        "Pedido sin avance, requerimos despacho inmediato.",
        "Orden estancada, requerimos envío con urgencia.",
        "Pedido sin movimiento, necesitamos salida a reparto urgente.",
        "Orden detenida, favor procesar envío con prioridad.",
        "Pedido sin avance, requerimos despacho urgente.",
        "Orden estancada, necesitamos salida a reparto inmediato.",
        "Pedido detenido, favor gestionar envío urgente.",
        "Orden sin movimiento, requerimos despacho con urgencia.",
        "Pedido estancado, necesitamos salida a reparto urgente.",
        "Orden sin avance, favor procesar envío inmediato.",
        "Pedido detenido, requerimos despacho urgente por favor.",
        "Orden sin movimiento, necesitamos envío con prioridad.",
        "Pedido estancado, favor gestionar salida a reparto urgente."
    ]
    
    def __init__(self, excel_path, headless=False):
        """
        Inicializa el bot
        
        Args:
            excel_path: Ruta al archivo Excel o CSV con los datos
            headless: Si True, ejecuta el navegador sin interfaz gráfica
        """
        self.excel_path = excel_path
        self.headless = headless
        self.driver = None
        self.wait = None
        self.logger = self._setup_logger()
        self.current_order_row = None  # Para guardar la fila correcta cuando hay múltiples resultados
        self.stats = {
            'total': 0,
            'procesados': 0,
            'ya_tienen_caso': 0,
            'errores': 0,
            'no_encontrados': 0,
            'saltados_por_tiempo': 0,
            'reintentos': 0
        }
        # Timeout global de 15 segundos para detectar sesión expirada
        self.TIMEOUT_SECONDS = 15
        # Estado para tracking de sesión
        self.session_expired = False
        self.current_processing_step = None  # Para saber dónde retomar después de relogear
        
    def _setup_logger(self):
        """Configura el logger para el bot"""
        logger = logging.getLogger('DropiReporterBot')
        logger.setLevel(logging.INFO)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Handler para archivo
        log_dir = Path(__file__).parent.parent.parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_handler = logging.FileHandler(
            log_dir / f'dropi_reporter_{timestamp}.log',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Formato
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def _check_session_expired(self):
        """Verifica si la sesión está expirada"""
        try:
            # Verificar token en localStorage o URL de login
            token_exists = self.driver.execute_script("return !!localStorage.getItem('DROPI_token')")
            is_login_page = "/login" in self.driver.current_url
            
            if not token_exists or is_login_page:
                self.logger.warning("⚠️ Sesión expirada detectada")
                return True
            return False
        except:
            # Si hay error al verificar, asumir que está expirada
            return True
    
    def _relogin_and_retry(self):
        """Reloguea, navega a Mis Pedidos y retorna True si fue exitoso"""
        self.logger.info("="*60)
        self.logger.info("🔄 RELOGUEANDO DESPUÉS DE TIMEOUT")
        self.logger.info("="*60)
        
        try:
            # Cerrar navegador actual
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            
            # Reinicializar navegador
            self._init_driver()
            
            # Relogear
            if not self._login():
                self.logger.error("❌ Error al relogear")
                return False
            
            # SIEMPRE navegar a Mis Pedidos después de relogear
            self.logger.info("📍 Navegando a Mis Pedidos después de relogin...")
            if not self._navigate_to_orders():
                self.logger.error("❌ Error al navegar a Mis Pedidos después de relogin")
                return False
            
            self.session_expired = False
            self.logger.info("✅ Relogin exitoso - Navegado a Mis Pedidos - Continuando desde donde se quedó")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error en relogin: {str(e)}")
            return False
    
    def _get_results_dir(self):
        """Obtiene el directorio de resultados"""
        base_dir = Path(__file__).parent.parent.parent.parent
        results_dir = base_dir / 'results' / 'reporter'
        results_dir.mkdir(parents=True, exist_ok=True)
        return results_dir
    
    def _get_today_results_file(self):
        """Obtiene el archivo de resultados del día actual"""
        results_dir = self._get_results_dir()
        today = datetime.now().strftime('%Y%m%d')
        pattern = f'dropi_reporter_results_{today}*.csv'
        files = list(results_dir.glob(pattern))
        
        if files:
            # Retornar el más reciente
            return max(files, key=lambda f: f.stat().st_mtime)
        return None
    
    def _load_checkpoint(self, df_input):
        """Carga el checkpoint desde el último CSV del día actual"""
        results_file = self._get_today_results_file()
        
        if not results_file:
            self.logger.info("📋 No hay checkpoint - Comenzando desde el inicio")
            return 0
        
        try:
            df_checkpoint = pd.read_csv(results_file)
            
            if df_checkpoint.empty:
                self.logger.info("📋 Checkpoint vacío - Comenzando desde el inicio")
                return 0
            
            # Obtener la última línea procesada
            if 'line_number' not in df_checkpoint.columns:
                self.logger.info("📋 Checkpoint sin line_number - Comenzando desde el inicio")
                return 0
            
            last_line = df_checkpoint['line_number'].max()
            
            if pd.isna(last_line):
                self.logger.info("📋 Checkpoint sin line_number válido - Comenzando desde el inicio")
                return 0
            
            start_line = int(last_line) + 1
            
            if start_line >= len(df_input):
                self.logger.info("📋 Ya se procesaron todas las líneas del CSV")
                return len(df_input)
            
            self.logger.info(f"📋 Checkpoint encontrado: Continuando desde línea {start_line + 1}")
            return start_line
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error al cargar checkpoint: {str(e)} - Comenzando desde el inicio")
            return 0
    
    def _check_order_can_be_processed(self, phone, df_checkpoint):
        """Verifica si una orden puede ser procesada según tiempos requeridos"""
        if df_checkpoint.empty:
            return True, None
        
        # Buscar la orden en el checkpoint
        order_records = df_checkpoint[df_checkpoint['phone'] == str(phone)]
        
        if order_records.empty:
            return True, None
        
        # Obtener el registro más reciente
        latest_record = order_records.iloc[-1]
        
        # Verificar next_attempt_time
        next_attempt_time = latest_record.get('next_attempt_time')
        if pd.notna(next_attempt_time) and str(next_attempt_time).strip() != '':
            try:
                # Convertir a datetime si es string
                if isinstance(next_attempt_time, str):
                    next_attempt = pd.to_datetime(next_attempt_time)
                else:
                    next_attempt = pd.to_datetime(next_attempt_time)
                
                now = datetime.now()
                
                if now < next_attempt:
                    hours_remaining = (next_attempt - now).total_seconds() / 3600
                    return False, {
                        'status': latest_record.get('status', 'unknown'),
                        'hours_remaining': hours_remaining,
                        'next_attempt_time': next_attempt
                    }
            except Exception as e:
                self.logger.warning(f"⚠️ Error al parsear next_attempt_time: {str(e)}")
                pass
        
        return True, None
    
    def _calculate_next_attempt_time(self, status, retry_count=0):
        """Calcula el tiempo del próximo intento según el estado"""
        now = datetime.now()
        
        if status == 'success' or status == 'already_has_case':
            # 46 horas
            return now + timedelta(hours=46)
        elif status == 'cannot_generate_yet':
            # 24 horas
            return now + timedelta(hours=24)
        elif status == 'in_movement':
            # Si ya está en movimiento y falla de nuevo, esperar 46 horas más
            return now + timedelta(hours=46)
        else:
            # Para errores, puede reintentar inmediatamente
            return now
    
    def _init_driver(self):
        """
        Inicializa el driver de Selenium para ejecución LOCAL (no Docker)
        Por defecto muestra el navegador para que puedas ver qué hace
        """
        self.logger.info("="*60)
        self.logger.info("🚀 INICIALIZANDO NAVEGADOR CHROME (LOCAL)")
        self.logger.info("="*60)
        
        options = webdriver.ChromeOptions()
        
        # Configuración para ejecución LOCAL (no Docker)
        if self.headless:
            self.logger.info("🔇 Modo HEADLESS activado (navegador oculto)")
            options.add_argument('--headless=new')
        else:
            self.logger.info("👀 Modo VISIBLE activado (puedes ver el navegador)")
        
        # Optimizaciones para PC local
        options.add_argument('--start-maximized')  # Ventana maximizada
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        
        # Evitar detección de automatización
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Preferencias para mejor rendimiento local
        prefs = {
            "profile.default_content_setting_values.notifications": 2,  # Bloquear notificaciones
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        }
        options.add_experimental_option("prefs", prefs)
        
        self.logger.info("   📦 Creando instancia de Chrome...")
        
        try:
            # Usar ChromeDriver local (se descarga automáticamente si no existe)
            self.driver = webdriver.Chrome(options=options)
            self.logger.info("   ✅ Chrome iniciado correctamente")
        except Exception as e:
            self.logger.error(f"   ❌ Error al iniciar Chrome: {e}")
            self.logger.info("   💡 Asegúrate de tener Chrome instalado")
            raise
        
        # Anti-detección
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Configurar timeouts con máximo de 15 segundos para detectar sesión expirada
        self.wait = WebDriverWait(self.driver, self.TIMEOUT_SECONDS)
        
        self.logger.info(f"   🌐 Navegador listo - Versión: Chrome")
        self.logger.info(f"   💻 Ejecutando en: PC LOCAL (no Docker)")
        self.logger.info("="*60)
    
    def _login(self):
        """Inicia sesión en Dropi con estrategia robusta (basada en scraper)"""
        try:
            self.logger.info("="*60)
            self.logger.info("INICIANDO PROCESO DE LOGIN")
            self.logger.info("="*60)
            
            self.logger.info("1) Abriendo página de login...")
            self.driver.get(self.DROPI_URL)
            self.logger.info(f"   URL cargada: {self.driver.current_url}")
            time.sleep(3)
            
            self.logger.info("2) Buscando campo de email...")
            email_input = self.wait.until(
                EC.visibility_of_element_located((By.NAME, "email"))
            )
            self.logger.info("   Campo email encontrado")
            
            self.logger.info(f"   Escribiendo email: {self.DROPI_EMAIL}")
            email_input.clear()
            email_input.send_keys(self.DROPI_EMAIL)
            time.sleep(1)
            self.logger.info("   Email ingresado")
            
            self.logger.info("   Buscando campo de password...")
            password_input = self.driver.find_element(By.NAME, "password")
            self.logger.info("   Campo password encontrado")
            
            self.logger.info("   Escribiendo password...")
            password_input.clear()
            password_input.send_keys(self.DROPI_PASSWORD)
            time.sleep(1)
            self.logger.info("   Password ingresado")
            
            # Enviar con ENTER en lugar de buscar botón (más robusto)
            self.logger.info("   Presionando ENTER para enviar...")
            password_input.send_keys(Keys.RETURN)
            self.logger.info("   Formulario enviado")
            
            self.logger.info("3) Esperando validación (token o redirección)...")
            # Esperar validación: Token en Storage O Redirección exitosa
            self.wait.until(
                lambda d: d.execute_script("return !!localStorage.getItem('DROPI_token')") or "/dashboard" in d.current_url
            )
            self.logger.info(f"   Validación exitosa - URL actual: {self.driver.current_url}")
            
            # Espera adicional para que cargue completamente
            self.logger.info("   Esperando 15s para carga completa del dashboard...")
            time.sleep(15)
            self.logger.info("   Espera completada")
            
            # Screenshot de éxito
            try:
                screenshot_path = Path(__file__).parent.parent.parent.parent / 'logs' / 'login_success.png'
                screenshot_path.parent.mkdir(exist_ok=True)
                self.driver.save_screenshot(str(screenshot_path))
                self.logger.info(f"   Screenshot guardado: {screenshot_path}")
            except Exception as e:
                self.logger.warning(f"   No se pudo guardar screenshot: {e}")
            
            self.logger.info("="*60)
            self.logger.info("LOGIN EXITOSO")
            self.logger.info("="*60)
            return True
            
        except Exception as e:
            self.logger.error("="*60)
            self.logger.error("LOGIN FALLIDO")
            self.logger.error("="*60)
            self.logger.error(f"Error: {type(e).__name__}: {e}")
            
            try:
                self.logger.error(f"URL actual: {self.driver.current_url}")
                body_text = self.driver.find_element(By.TAG_NAME, "body").text[:300].replace('\n', ' ')
                self.logger.error(f"Contenido de pantalla: {body_text}")
            except:
                pass
            
            # Screenshot del error
            try:
                screenshot_path = Path(__file__).parent.parent.parent.parent / 'logs' / 'login_error.png'
                screenshot_path.parent.mkdir(exist_ok=True)
                self.driver.save_screenshot(str(screenshot_path))
                self.logger.error(f"Screenshot de error guardado: {screenshot_path}")
            except:
                pass
            
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _navigate_to_orders(self, retry_count=0, max_retries=2):
        """
        Navega a la sección de Mis Pedidos con estrategia de fallback
        
        Estrategia:
        1. Intento 1: Navegación por menú (método tradicional)
        2. Intento 2: Navegación directa por URL (fallback robusto)
        3. Intento 3: Navegación directa con espera extendida
        
        Args:
            retry_count: Número de intento actual
            max_retries: Máximo número de reintentos
            
        Returns:
            True si la navegación fue exitosa, False en caso contrario
        """
        self.logger.info("="*60)
        self.logger.info(f"📍 NAVEGANDO A MIS PEDIDOS (Intento {retry_count + 1}/{max_retries + 1})")
        self.logger.info("="*60)
        
        try:
            if retry_count == 0:
                # INTENTO 1: Navegación tradicional por menú
                self.logger.info("🔹 Método: Navegación por menú (tradicional)")
                
                try:
                    self.logger.info("   1) Buscando menú 'Mis Pedidos'...")
                    mis_pedidos_menu = self.wait.until(
                        EC.element_to_be_clickable((
                            By.XPATH, 
                            "//a[contains(@class, 'is-parent') and contains(., 'Mis Pedidos')]"
                        ))
                    )
                    self.logger.info("   ✅ Menú encontrado")
                    
                    self.logger.info("   2) Haciendo click en el menú...")
                    mis_pedidos_menu.click()
                    time.sleep(2)
                    self.logger.info("   ✅ Click exitoso")
                    
                    self.logger.info("   3) Buscando submenú 'Mis Pedidos'...")
                    mis_pedidos_link = self.wait.until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            "//a[@href='/dashboard/orders' and contains(., 'Mis Pedidos')]"
                        ))
                    )
                    self.logger.info("   ✅ Submenú encontrado")
                    
                    self.logger.info("   4) Haciendo click en el submenú...")
                    mis_pedidos_link.click()
                    time.sleep(3)
                    self.logger.info("   ✅ Click exitoso")
                    
                    # Verificar que estamos en la página correcta
                    self.wait.until(EC.url_contains("/dashboard/orders"))
                    self.logger.info(f"   ✅ URL correcta: {self.driver.current_url}")
                    
                    # Esperar a que cargue la tabla de órdenes
                    self.logger.info("   5) Esperando carga de tabla de órdenes...")
                    time.sleep(3)
                    
                    # Screenshot de éxito
                    try:
                        screenshot_path = Path(__file__).parent.parent.parent.parent / 'logs' / 'orders_page_success.png'
                        self.driver.save_screenshot(str(screenshot_path))
                        self.logger.info(f"   📸 Screenshot guardado: {screenshot_path}")
                    except Exception as e:
                        self.logger.warning(f"   ⚠️ No se pudo guardar screenshot: {e}")
                    
                    self.logger.info("✅ Navegación exitosa a Mis Pedidos (método tradicional)")
                    return True
                    
                except Exception as menu_error:
                    self.logger.warning(f"⚠️ Navegación por menú falló: {str(menu_error)}")
                    
                    # Screenshot del error
                    try:
                        screenshot_path = Path(__file__).parent.parent.parent.parent / 'logs' / 'orders_menu_error.png'
                        self.driver.save_screenshot(str(screenshot_path))
                        self.logger.warning(f"   📸 Screenshot de error guardado: {screenshot_path}")
                    except:
                        pass
                    
                    # Reintentar con método directo
                    if retry_count < max_retries:
                        self.logger.info("🔄 Reintentando con navegación directa...")
                        time.sleep(2)
                        return self._navigate_to_orders(retry_count=retry_count + 1, max_retries=max_retries)
                    else:
                        raise menu_error
            
            else:
                # INTENTO 2+: Navegación directa por URL (FALLBACK ROBUSTO)
                wait_time = 5 + (retry_count * 5)  # Espera incremental: 10s, 15s, etc.
                
                self.logger.info(f"🔹 Método: Navegación directa por URL (fallback)")
                self.logger.info(f"   ⏳ Esperando {wait_time}s antes de navegar...")
                
                # Espera incremental
                for i in range(wait_time):
                    if i % 5 == 0:
                        self.logger.info(f"      ⏱️ {i}/{wait_time} segundos...")
                    time.sleep(1)
                self.logger.info("   ✅ Espera completada")
                
                # Navegación directa
                target_url = "https://app.dropi.co/dashboard/orders"
                self.logger.info(f"   🚀 Navegando directamente a: {target_url}")
                self.driver.get(target_url)
                
                # Esperar a que la URL se cargue
                self.logger.info("   ⏳ Validando URL...")
                self.wait.until(EC.url_contains("/dashboard/orders"))
                self.logger.info(f"   ✅ URL validada: {self.driver.current_url}")
                
                # Espera adicional para carga de elementos
                additional_wait = 10 + (retry_count * 5)
                self.logger.info(f"   ⏳ Esperando {additional_wait}s para carga de elementos...")
                time.sleep(additional_wait)
                self.logger.info("   ✅ Elementos cargados")
                
                # Screenshot de éxito
                try:
                    screenshot_path = Path(__file__).parent.parent.parent.parent / 'logs' / f'orders_page_direct_{retry_count}.png'
                    self.driver.save_screenshot(str(screenshot_path))
                    self.logger.info(f"   📸 Screenshot guardado: {screenshot_path}")
                except Exception as e:
                    self.logger.warning(f"   ⚠️ No se pudo guardar screenshot: {e}")
                
                self.logger.info("✅ Navegación exitosa a Mis Pedidos (navegación directa)")
                return True
            
        except Exception as e:
            self.logger.error(f"❌ Error al navegar a Mis Pedidos: {str(e)}")
            
            # Screenshot del error final
            try:
                screenshot_path = Path(__file__).parent.parent.parent.parent / 'logs' / f'orders_error_final_{retry_count}.png'
                self.driver.save_screenshot(str(screenshot_path))
                self.logger.error(f"   📸 Screenshot de error guardado: {screenshot_path}")
            except:
                pass
            
            # Último intento si no hemos alcanzado el máximo
            if retry_count < max_retries:
                self.logger.warning(f"⚠️ Intento {retry_count + 1} falló. Reintentando...")
                time.sleep(3)
                return self._navigate_to_orders(retry_count=retry_count + 1, max_retries=max_retries)
            
            self.logger.error(f"❌ Todos los intentos de navegación fallaron ({max_retries + 1} intentos)")
            return False
    
    def _search_order_by_phone(self, phone):
        """
        Busca una orden por número de teléfono
        
        Args:
            phone: Número de teléfono a buscar
            
        Returns:
            True si se encontró la orden, False en caso contrario
        """
        self.logger.info(f"Buscando orden con teléfono: {phone}")
        
        try:
            # Buscar el input de búsqueda
            self.logger.info("   1) Buscando campo de búsqueda...")
            search_input = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "input[name='textToSearch'], input[placeholder*='Buscar']"
                ))
            )
            self.logger.info("   ✅ Campo de búsqueda encontrado")
            
            # Limpiar búsqueda anterior
            self.logger.info("   2) Limpiando búsqueda anterior...")
            search_input.clear()
            time.sleep(0.5)
            
            # Ingresar teléfono
            self.logger.info(f"   3) Escribiendo teléfono: {phone}")
            search_input.send_keys(str(phone))
            time.sleep(1)
            
            # PRESIONAR ENTER para ejecutar la búsqueda
            self.logger.info("   4) Presionando ENTER para buscar...")
            search_input.send_keys(Keys.RETURN)
            time.sleep(3)  # Esperar a que se ejecute la búsqueda
            self.logger.info("   ✅ Búsqueda ejecutada")
            
            # Verificar si hay resultados
            try:
                self.logger.info("   5) Verificando resultados...")
                # Esperar a que aparezca al menos un resultado
                self.wait.until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "tbody.list tr"
                    ))
                )
                self.logger.info(f"✅ Orden encontrada para teléfono: {phone}")
                return True
                
            except TimeoutException:
                self.logger.warning(f"⚠️ No se encontró orden para teléfono: {phone}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error al buscar orden: {str(e)}")
            return False
    
    def _validate_order_state(self, expected_state):
        """
        Valida que el estado de la orden coincida con el esperado
        ITERA por todas las filas de la tabla si hay múltiples resultados
        
        Args:
            expected_state: Estado esperado de la orden
            
        Returns:
            True si el estado coincide (y hace click en esa fila), False en caso contrario
        """
        try:
            self.logger.info(f"Validando estado esperado: {expected_state}")
            
            # Buscar TODAS las filas de resultados
            rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody.list tr")
            self.logger.info(f"   Se encontraron {len(rows)} órdenes con este teléfono")
            
            # Normalizar estado esperado
            expected_normalized = expected_state.upper().strip()
            
            # Iterar por cada fila para encontrar la que coincida
            for index, row in enumerate(rows, 1):
                try:
                    # Obtener el estado de esta fila
                    state_badge = row.find_element(By.CSS_SELECTOR, "td span.badge")
                    current_state = state_badge.text.strip()
                    current_normalized = current_state.upper().strip()
                    
                    self.logger.info(f"   Fila {index}: Estado = '{current_state}'")
                    
                    # Verificar si coincide
                    if expected_normalized in current_normalized or current_normalized in expected_normalized:
                        self.logger.info(f"   ✅ ¡COINCIDENCIA! Fila {index} tiene el estado correcto: '{current_state}'")
                        
                        # Hacer scroll a esta fila específica
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                        time.sleep(1)
                        
                        # Guardar referencia a esta fila para usarla después
                        self.current_order_row = row
                        
                        return True
                        
                except Exception as row_error:
                    self.logger.warning(f"   ⚠️ Error al leer fila {index}: {str(row_error)}")
                    continue
            
            # Si llegamos aquí, ninguna fila coincidió
            self.logger.warning("="*60)
            self.logger.warning(f"❌ NINGUNA ORDEN COINCIDE CON EL ESTADO: '{expected_state}'")
            self.logger.warning(f"   Se revisaron {len(rows)} órdenes")
            self.logger.warning("="*60)
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error al validar estado: {str(e)}")
            return False
    
    def _click_new_consultation(self):
        """Click en el botón de Nueva Consulta de la fila correcta"""
        self.logger.info("Haciendo click en 'Nueva consulta'...")
        
        try:
            # Si tenemos una fila específica guardada, usarla
            if hasattr(self, 'current_order_row') and self.current_order_row:
                self.logger.info("   Usando la fila correcta identificada anteriormente")
                row = self.current_order_row
            else:
                # Fallback: usar la primera fila
                self.logger.warning("   No hay fila específica, usando la primera")
                row = self.driver.find_element(By.CSS_SELECTOR, "tbody.list tr:first-child")
            
            # Buscar el botón de Nueva consulta EN ESA FILA ESPECÍFICA
            new_consultation_button = row.find_element(
                By.CSS_SELECTOR,
                "a[title='Nueva consulta'] i.fa-headset"
            )
            
            self.logger.info("   ✅ Botón 'Nueva consulta' encontrado en la fila correcta")
            
            # Scroll al elemento
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", new_consultation_button)
            time.sleep(1)
            
            # Click en el padre (el <a>)
            parent_link = new_consultation_button.find_element(By.XPATH, "..")
            
            try:
                parent_link.click()
            except:
                self.driver.execute_script("arguments[0].click();", parent_link)
            
            time.sleep(3)
            
            self.logger.info("✅ Click en 'Nueva consulta' exitoso")
            
            # Limpiar la referencia
            self.current_order_row = None
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error al hacer click en 'Nueva consulta': {str(e)}")
            
            # Screenshot del error
            try:
                screenshot_path = Path(__file__).parent.parent.parent.parent / 'logs' / 'error_new_consultation.png'
                self.driver.save_screenshot(str(screenshot_path))
                self.logger.error(f"   Screenshot guardado: {screenshot_path}")
            except:
                pass
            
            return False
    
    def _select_consultation_type(self):
        """Selecciona el tipo de consulta: Transportadora"""
        self.logger.info("Seleccionando tipo de consulta: Transportadora...")
        
        try:
            self.logger.info("   1) Buscando dropdown de tipo de consulta...")
            # Click en el dropdown de tipo de consulta
            type_dropdown = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'select-button') and .//p[contains(text(), 'Selecciona el tipo de consulta')]]"
                ))
            )
            self.logger.info("   ✅ Dropdown encontrado")
            
            # Scroll al elemento
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", type_dropdown)
            time.sleep(1)
            
            self.logger.info("   2) Haciendo click en dropdown...")
            # Intentar click normal, si falla usar JavaScript
            try:
                type_dropdown.click()
            except:
                self.driver.execute_script("arguments[0].click();", type_dropdown)
            time.sleep(1)  # Reducido de 2s a 1s
            self.logger.info("   ✅ Dropdown abierto")
            
            # Seleccionar "Transportadora"
            self.logger.info("   3) Buscando opción 'Transportadora'...")
            transportadora_option = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'option') and contains(., 'Transportadora')]"
                ))
            )
            self.logger.info("   ✅ Opción encontrada")
            
            self.logger.info("   4) Seleccionando 'Transportadora'...")
            # Scroll y click
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", transportadora_option)
            time.sleep(0.5)
            try:
                transportadora_option.click()
            except:
                self.driver.execute_script("arguments[0].click();", transportadora_option)
            time.sleep(1)  # Reducido de 2s a 1s
            
            self.logger.info("✅ Tipo de consulta seleccionado: Transportadora")
            self.current_processing_step = None
            return True
            
        except TimeoutException:
            self.logger.error("❌ Timeout al seleccionar tipo de consulta - Sesión probablemente expirada")
            self.session_expired = True
            return False
        except Exception as e:
            self.logger.error(f"❌ Error al seleccionar tipo de consulta: {str(e)}")
            
            # Screenshot del error
            try:
                screenshot_path = Path(__file__).parent.parent.parent.parent / 'logs' / 'error_select_type.png'
                self.driver.save_screenshot(str(screenshot_path))
                self.logger.error(f"   Screenshot guardado: {screenshot_path}")
            except:
                pass
            
            return False
    
    def _select_consultation_reason(self):
        """Selecciona el motivo de consulta: Ordenes sin movimiento"""
        self.logger.info("Seleccionando motivo: Ordenes sin movimiento...")
        self.current_processing_step = 'select_consultation_reason'
        
        try:
            self.logger.info("   1) Buscando dropdown de motivo...")
            # Click en el dropdown de motivo
            reason_dropdown = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'select-button') and .//div[contains(text(), 'Selecciona el motivo de consulta')]]"
                ))
            )
            self.logger.info("   ✅ Dropdown encontrado")
            
            # Scroll al elemento
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", reason_dropdown)
            time.sleep(0.5)
            
            self.logger.info("   2) Haciendo click en dropdown...")
            try:
                reason_dropdown.click()
            except:
                self.driver.execute_script("arguments[0].click();", reason_dropdown)
            time.sleep(1)  # Reducido de 2s a 1s
            self.logger.info("   ✅ Dropdown abierto")
            
            # Seleccionar "Ordenes sin movimiento"
            self.logger.info("   3) Buscando opción 'Ordenes sin movimiento'...")
            no_movement_option = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'option') and contains(., 'Ordenes sin movimiento')]"
                ))
            )
            self.logger.info("   ✅ Opción encontrada")
            
            self.logger.info("   4) Seleccionando 'Ordenes sin movimiento'...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", no_movement_option)
            time.sleep(0.5)
            try:
                no_movement_option.click()
            except:
                self.driver.execute_script("arguments[0].click();", no_movement_option)
            time.sleep(1)  # Reducido de 2s a 1s
            
            self.logger.info("✅ Motivo seleccionado: Ordenes sin movimiento")
            
            # Esperar un momento para que aparezca el alert si existe
            time.sleep(1)
            
            # Verificar si aparece el alert de "Debes esperar al menos un día sin movimiento"
            alert_detected = self._check_wait_time_alert()
            
            if alert_detected:
                self.logger.warning("⚠️ Alert detectado: 'Debes esperar al menos un día sin movimiento'")
                self.logger.warning("   El botón 'Siguiente' estará bloqueado - Orden requiere más tiempo")
                self.current_processing_step = None
                return 'wait_required'  # Retornar código especial para indicar que necesita esperar
            
            self.current_processing_step = None
            return True
            
        except TimeoutException:
            self.logger.error("❌ Timeout al seleccionar motivo - Sesión probablemente expirada")
            self.session_expired = True
            return False
        except Exception as e:
            self.logger.error(f"❌ Error al seleccionar motivo: {str(e)}")
            
            # Screenshot del error
            try:
                screenshot_path = Path(__file__).parent.parent.parent.parent / 'logs' / 'error_select_reason.png'
                self.driver.save_screenshot(str(screenshot_path))
                self.logger.error(f"   Screenshot guardado: {screenshot_path}")
            except:
                pass
            
            return False
    
    def _check_wait_time_alert(self):
        """
        Verifica si aparece el alert que indica que se debe esperar un día sin movimiento
        
        Returns:
            True si el alert está presente, False en caso contrario
        """
        try:
            # Buscar el alert con el texto específico
            alert = self.driver.find_element(
                By.XPATH,
                "//app-alert//p[contains(text(), 'Debes esperar al menos un día sin movimiento para iniciar una conversación sobre la orden')]"
            )
            
            if alert.is_displayed():
                return True
            return False
            
        except NoSuchElementException:
            # No se encontró el alert, está bien
            return False
        except Exception as e:
            self.logger.debug(f"   Error al verificar alert: {str(e)}")
            return False
    
    def _click_next_button(self):
        """Click en el botón Siguiente (con fallback a Cancelar si falla en 5 segundos)"""
        self.logger.info("Haciendo click en 'Siguiente'...")
        self.current_processing_step = 'click_next_button'
        
        try:
            self.logger.info("   1) Buscando botón 'Siguiente'...")
            # Usar timeout corto de 5 segundos para evitar esperas innecesarias
            short_wait = WebDriverWait(self.driver, 5)
            next_button = short_wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'btn') and .//span[contains(text(), 'Siguiente')]]"
                ))
            )
            self.logger.info("   ✅ Botón encontrado")
            
            self.logger.info("   2) Haciendo click...")
            # Scroll al botón
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            time.sleep(0.5)
            
            try:
                next_button.click()
            except:
                self.driver.execute_script("arguments[0].click();", next_button)
            time.sleep(1)  # Reducido de 2s a 1s
            
            self.logger.info("✅ Click en 'Siguiente' exitoso")
            self.current_processing_step = None
            return True
            
        except TimeoutException:
            # Timeout de 5 segundos - El botón no está disponible (probablemente bloqueado por alert)
            self.logger.warning("⚠️ Timeout de 5s al buscar botón 'Siguiente' - Probablemente bloqueado por alert")
            self.logger.warning("   Intentando cerrar modal con 'Cancelar'...")
            
            # Intentar hacer click en Cancelar para cerrar el modal
            try:
                cancel_button = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(@class, 'btn') and contains(@class, 'secondary') and .//span[contains(text(), 'Cancelar')]]"
                )
                
                # Scroll y click
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cancel_button)
                time.sleep(0.5)
                
                try:
                    cancel_button.click()
                except:
                    self.driver.execute_script("arguments[0].click();", cancel_button)
                
                time.sleep(1)
                self.logger.info("   ✅ Click en 'Cancelar' exitoso - Modal cerrado")
                
                # Screenshot del estado
                try:
                    screenshot_path = Path(__file__).parent.parent.parent.parent / 'logs' / 'canceled_modal_timeout.png'
                    self.driver.save_screenshot(str(screenshot_path))
                    self.logger.debug(f"   📸 Screenshot guardado: {screenshot_path}")
                except:
                    pass
                
            except Exception as cancel_error:
                self.logger.error(f"   ❌ No se pudo hacer click en 'Cancelar': {str(cancel_error)}")
            
            self.current_processing_step = None
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error al hacer click en 'Siguiente': {str(e)}")
            
            # Si falla, intentar hacer click en Cancelar para cerrar el modal
            try:
                self.logger.warning("   ⚠️ Intentando hacer click en 'Cancelar' para cerrar el modal...")
                cancel_button = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(@class, 'btn') and contains(@class, 'secondary') and .//span[contains(text(), 'Cancelar')]]"
                )
                
                # Scroll y click
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cancel_button)
                time.sleep(0.5)
                
                try:
                    cancel_button.click()
                except:
                    self.driver.execute_script("arguments[0].click();", cancel_button)
                
                time.sleep(1)
                self.logger.info("   ✅ Click en 'Cancelar' exitoso - Modal cerrado")
                
            except Exception as cancel_error:
                self.logger.error(f"   ❌ No se pudo hacer click en 'Cancelar': {str(cancel_error)}")
            
            self.current_processing_step = None
            return False
    
    def _get_random_observation_text(self):
        """
        Selecciona un texto de observación aleatorio del diccionario
        
        Returns:
            str: Texto de observación seleccionado aleatoriamente
        """
        return random.choice(self.OBSERVATION_TEXTS)
    
    def _enter_observation_text(self):
        """Ingresa el texto de observación (seleccionado aleatoriamente del diccionario)"""
        self.logger.info("Ingresando texto de observación...")
        
        try:
            # Seleccionar texto aleatorio del diccionario
            observation_text = self._get_random_observation_text()
            self.logger.info(f"   Texto seleccionado (aleatorio): '{observation_text}'")
            
            # Buscar el textarea
            textarea = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "textarea[id='description'], textarea[placeholder*='transportadora']"
                ))
            )
            
            # Limpiar y escribir el texto
            textarea.clear()
            time.sleep(0.5)
            textarea.send_keys(observation_text)
            time.sleep(1)
            
            self.logger.info(f"✓ Texto ingresado: '{observation_text}'")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Error al ingresar texto: {str(e)}")
            return False
    
    def _start_conversation(self):
        """Click en el botón 'Iniciar una conversación'"""
        self.logger.info("Iniciando conversación...")
        
        try:
            start_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'btn') and .//span[contains(text(), 'Iniciar un conversación')]]"
                ))
            )
            start_button.click()
            time.sleep(2)
            
            self.logger.info("✓ Conversación iniciada")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Error al iniciar conversación: {str(e)}")
            return False
    
    def _handle_existing_case_popup(self):
        """
        Maneja los popups que pueden aparecer al intentar crear una consulta.
        
        Hay dos tipos de popups:
        1. "Orden ya tiene un caso" → Click en "Cancelar"
        2. "¡Oops! Aún no es posible" (estado no permite conversación) → Click en "Aceptar"
        
        Returns:
            dict con 'found' (bool) y 'type' (str) del popup encontrado
        """
        try:
            # Esperar un poco para ver si aparece algún popup
            self.logger.info("   Verificando si hay popups...")
            time.sleep(1)  # Reducido de 3s a 1s
            
            # TIPO 1: Buscar popup "Orden ya tiene un caso"
            try:
                popup_caso_existente = self.driver.find_element(
                    By.XPATH,
                    "//div[contains(@class, 'swal2-popup') and .//h2[contains(text(), 'Orden ya tiene un caso')]]"
                )
                
                if popup_caso_existente.is_displayed():
                    self.logger.warning("="*60)
                    self.logger.warning("⚠️  POPUP TIPO 1: ORDEN YA TIENE UN CASO ABIERTO")
                    self.logger.warning("="*60)
                    
                    # Buscar el botón Cancelar
                    self.logger.info("   Buscando botón 'Cancelar' en el popup...")
                    cancel_button = self.driver.find_element(
                        By.CSS_SELECTOR,
                        "button.swal2-cancel"
                    )
                    self.logger.info("   ✅ Botón 'Cancelar' encontrado")
                    
                    # Hacer click en Cancelar (con fallback a JavaScript)
                    self.logger.info("   Haciendo click en 'Cancelar'...")
                    try:
                        cancel_button.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", cancel_button)
                    
                    time.sleep(1)  # Reducido de 2s a 1s
                    
                    self.logger.info("   ✅ Popup cerrado exitosamente")
                    self.logger.info("   ➡️  Continuando con siguiente orden...")
                    
                    # Screenshot del estado
                    try:
                        screenshot_path = Path(__file__).parent.parent.parent.parent / 'logs' / 'popup_caso_existente.png'
                        self.driver.save_screenshot(str(screenshot_path))
                        self.logger.info(f"   📸 Screenshot guardado: {screenshot_path}")
                    except:
                        pass
                    
                    return {'found': True, 'type': 'caso_existente'}
                    
            except NoSuchElementException:
                pass  # No es este tipo de popup
            
            # TIPO 2: Buscar popup "¡Oops! Aún no es posible"
            try:
                popup_estado_invalido = self.driver.find_element(
                    By.XPATH,
                    "//div[contains(@class, 'p-dialog') and .//h2[contains(text(), '¡Oops! Aún no es posible')]]"
                )
                
                if popup_estado_invalido.is_displayed():
                    self.logger.warning("="*60)
                    self.logger.warning("⚠️  POPUP TIPO 2: ESTADO NO PERMITE CONVERSACIÓN")
                    self.logger.warning("="*60)
                    
                    # Buscar el botón Aceptar
                    self.logger.info("   Buscando botón 'Aceptar' en el popup...")
                    
                    # Intentar varios selectores para el botón Aceptar
                    accept_button = None
                    selectors = [
                        "//button[contains(@class, 'btn') and .//span[contains(text(), 'Aceptar')]]",
                        "//dropi-button//button[.//span[contains(text(), 'Aceptar')]]",
                        "//button[contains(., 'Aceptar')]"
                    ]
                    
                    for selector in selectors:
                        try:
                            accept_button = self.driver.find_element(By.XPATH, selector)
                            if accept_button.is_displayed():
                                break
                        except:
                            continue
                    
                    if accept_button:
                        self.logger.info("   ✅ Botón 'Aceptar' encontrado")
                        
                        # Hacer click en Aceptar (con fallback a JavaScript)
                        self.logger.info("   Haciendo click en 'Aceptar'...")
                        try:
                            accept_button.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", accept_button)
                        
                        time.sleep(1)  # Reducido de 2s a 1s
                        
                        self.logger.info("   ✅ Popup cerrado exitosamente")
                        self.logger.info("   ➡️  Continuando con siguiente orden...")
                        
                        # Screenshot del estado
                        try:
                            screenshot_path = Path(__file__).parent.parent.parent.parent / 'logs' / 'popup_estado_invalido.png'
                            self.driver.save_screenshot(str(screenshot_path))
                            self.logger.info(f"   📸 Screenshot guardado: {screenshot_path}")
                        except:
                            pass
                        
                        return {'found': True, 'type': 'estado_invalido'}
                    else:
                        # Si no encontramos el botón, intentar cerrar por la X
                        self.logger.warning("   ⚠️ No se encontró botón 'Aceptar', intentando cerrar por la X...")
                        try:
                            close_button = self.driver.find_element(
                                By.CSS_SELECTOR,
                                "button.p-dialog-header-close"
                            )
                            close_button.click()
                            time.sleep(2)
                            self.logger.info("   ✅ Popup cerrado por la X")
                            return {'found': True, 'type': 'estado_invalido'}
                        except:
                            pass
                    
            except NoSuchElementException:
                pass  # No es este tipo de popup
            
            # No se encontró ningún popup
            self.logger.info("   ✅ No hay popups - Continuando normalmente")
            return {'found': False, 'type': None}
                
        except Exception as e:
            self.logger.error(f"   ❌ Error al manejar popups: {str(e)}")
            
            # Intentar cerrar cualquier popup visible como último recurso
            try:
                self.logger.warning("   Intentando cerrar cualquier popup visible...")
                
                # Intentar botones de SweetAlert2
                cancel_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.swal2-cancel, button.swal2-confirm")
                for btn in cancel_buttons:
                    if btn.is_displayed():
                        try:
                            btn.click()
                            time.sleep(1)
                            self.logger.info("   ✅ Popup cerrado (SweetAlert2)")
                            return {'found': True, 'type': 'unknown'}
                        except:
                            pass
                
                # Intentar botones de PrimeNG Dialog
                dialog_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'p-dialog-header-close')]")
                for btn in dialog_buttons:
                    if btn.is_displayed():
                        try:
                            btn.click()
                            time.sleep(1)
                            self.logger.info("   ✅ Popup cerrado (PrimeNG Dialog)")
                            return {'found': True, 'type': 'unknown'}
                        except:
                            pass
                            
            except:
                pass
            
            return {'found': False, 'type': None}
    
    def _process_single_order(self, phone, expected_state, line_number, is_first_order=False, retry_count=0):
        """
        Procesa una sola orden con manejo de timeouts y relogin
        
        Args:
            phone: Número de teléfono de la orden
            expected_state: Estado esperado de la orden
            line_number: Número de línea en el CSV original
            is_first_order: Si es la primera orden (para navegar a Mis Pedidos)
            retry_count: Número de reintentos para esta orden
            
        Returns:
            dict con el resultado del procesamiento completo con nuevas columnas
        """
        result = {
            'line_number': line_number,
            'phone': str(phone),
            'order_id': '',  # Se llenará si está disponible
            'status': 'error',
            'report_generated': False,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hours_since_last_report': None,
            'next_attempt_time': None,
            'retry_count': retry_count
        }
        
        try:
            # Verificar si hay sesión expirada antes de comenzar
            if self.session_expired or self._check_session_expired():
                self.logger.warning("⚠️ Sesión expirada detectada antes de procesar orden")
                if not self._relogin_and_retry():
                    result['status'] = 'session_expired'
                    return result
                # Después de relogear, _relogin_and_retry ya navegó a Mis Pedidos
                # No necesitamos navegar de nuevo
            
            # Solo navegar a Mis Pedidos en la primera orden (si no se relogueó antes)
            if is_first_order and not self.session_expired:
                self.logger.info("📍 Primera orden - Navegando a Mis Pedidos...")
                self.current_processing_step = 'navigate_to_orders'
                if not self._navigate_to_orders():
                    if self.session_expired:
                        result['status'] = 'session_expired'
                    else:
                        result['status'] = 'error'
                        result['message'] = 'Error al navegar a Mis Pedidos'
                    self.stats['errores'] += 1
                    return result
            else:
                # Verificar que realmente estamos en Mis Pedidos
                current_url = self.driver.current_url
                if '/dashboard/orders' not in current_url:
                    self.logger.warning(f"⚠️ No estamos en Mis Pedidos (URL: {current_url}) - Navegando...")
                    if not self._navigate_to_orders():
                        result['status'] = 'error'
                        result['message'] = 'Error al navegar a Mis Pedidos'
                        self.stats['errores'] += 1
                        return result
                else:
                    self.logger.info("📍 Ya estamos en Mis Pedidos, continuando...")
            
            # Buscar orden por teléfono
            self.current_processing_step = 'search_order'
            if not self._search_order_by_phone(phone):
                if self.session_expired:
                    result['status'] = 'session_expired'
                else:
                    result['status'] = 'not_found'
                    self.stats['no_encontrados'] += 1
                return result
            
            # Validar estado
            self.current_processing_step = 'validate_state'
            if not self._validate_order_state(expected_state):
                if self.session_expired:
                    result['status'] = 'session_expired'
                else:
                    result['status'] = 'error'
                    self.stats['errores'] += 1
                return result
            
            # Click en Nueva Consulta
            self.current_processing_step = 'click_new_consultation'
            if not self._click_new_consultation():
                if self.session_expired:
                    result['status'] = 'session_expired'
                else:
                    result['status'] = 'error'
                    self.stats['errores'] += 1
                return result
            
            # VERIFICAR INMEDIATAMENTE si aparece algún popup
            popup_result = self._handle_existing_case_popup()
            
            if popup_result['found']:
                if popup_result['type'] == 'caso_existente':
                    result['status'] = 'already_has_case'
                    result['report_generated'] = False
                    result['next_attempt_time'] = self._calculate_next_attempt_time('already_has_case', retry_count).strftime('%Y-%m-%d %H:%M:%S')
                    self.stats['ya_tienen_caso'] += 1
                    return result
                elif popup_result['type'] == 'estado_invalido':
                    result['status'] = 'error'
                    self.stats['errores'] += 1
                    return result
            
            # Seleccionar tipo de consulta
            self.current_processing_step = 'select_consultation_type'
            if not self._select_consultation_type():
                if self.session_expired:
                    result['status'] = 'session_expired'
                else:
                    result['status'] = 'error'
                    self.stats['errores'] += 1
                return result
            
            # Seleccionar motivo
            self.current_processing_step = 'select_consultation_reason'
            reason_result = self._select_consultation_reason()
            
            if reason_result == 'wait_required':
                # Se detectó el alert de espera - no intentar buscar botón Siguiente
                # Esto es equivalente a no poder dar siguiente - requiere 24 horas de espera
                self.logger.warning("="*60)
                self.logger.warning("⚠️ ALERT DETECTADO: Orden requiere esperar 24 horas")
                self.logger.warning("="*60)
                
                result['status'] = 'cannot_generate_yet'
                result['report_generated'] = False
                result['next_attempt_time'] = self._calculate_next_attempt_time('cannot_generate_yet', retry_count).strftime('%Y-%m-%d %H:%M:%S')
                
                # Cerrar modal con Cancelar antes de continuar
                self.logger.info("   Cerrando modal con 'Cancelar'...")
                try:
                    cancel_button = self.wait.until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            "//button[contains(@class, 'btn') and contains(@class, 'secondary') and .//span[contains(text(), 'Cancelar')]]"
                        ))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cancel_button)
                    time.sleep(0.5)
                    try:
                        cancel_button.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", cancel_button)
                    time.sleep(1)
                    self.logger.info("   ✅ Modal cerrado exitosamente - Continuando con siguiente orden")
                except Exception as cancel_error:
                    self.logger.warning(f"   ⚠️ No se pudo cerrar modal automáticamente: {str(cancel_error)}")
                    # Intentar con método alternativo
                    try:
                        # Buscar cualquier botón Cancelar
                        cancel_buttons = self.driver.find_elements(By.XPATH, "//button[contains(., 'Cancelar')]")
                        for btn in cancel_buttons:
                            if btn.is_displayed():
                                btn.click()
                                time.sleep(1)
                                self.logger.info("   ✅ Modal cerrado con método alternativo")
                                break
                    except:
                        pass
                
                self.current_processing_step = None
                return result
            elif not reason_result:
                if self.session_expired:
                    result['status'] = 'session_expired'
                else:
                    result['status'] = 'error'
                    self.stats['errores'] += 1
                return result
            
            # Click en Siguiente (solo si no se detectó el alert)
            self.current_processing_step = 'click_next_button'
            next_success = self._click_next_button()
            
            if not next_success:
                if self.session_expired:
                    result['status'] = 'session_expired'
                    return result
                else:
                    # No se pudo dar siguiente - probablemente falta tiempo (24 horas)
                    result['status'] = 'cannot_generate_yet'
                    result['report_generated'] = False
                    result['next_attempt_time'] = self._calculate_next_attempt_time('cannot_generate_yet', retry_count).strftime('%Y-%m-%d %H:%M:%S')
                    self.stats['errores'] += 1
                    return result
            
            # Ingresar observación
            self.current_processing_step = 'enter_observation'
            if not self._enter_observation_text():
                if self.session_expired:
                    result['status'] = 'session_expired'
                else:
                    result['status'] = 'error'
                    self.stats['errores'] += 1
                return result
            
            # Iniciar conversación
            self.current_processing_step = 'start_conversation'
            if not self._start_conversation():
                if self.session_expired:
                    result['status'] = 'session_expired'
                else:
                    result['status'] = 'error'
                    self.stats['errores'] += 1
                return result
            
            # Éxito - Reporte generado
            result['status'] = 'success'
            result['report_generated'] = True
            result['next_attempt_time'] = self._calculate_next_attempt_time('success', retry_count).strftime('%Y-%m-%d %H:%M:%S')
            self.stats['procesados'] += 1
            self.current_processing_step = None
            
        except TimeoutException:
            self.logger.error(f"❌ Timeout procesando orden {phone}")
            result['status'] = 'session_expired'
            self.session_expired = True
            
        except Exception as e:
            result['status'] = 'error'
            self.stats['errores'] += 1
            self.logger.error(f"❌ Error procesando orden {phone}: {str(e)}")
        
        return result
    
    def _load_excel_data(self):
        """
        Carga y filtra los datos del Excel o CSV
        
        Returns:
            DataFrame con los datos filtrados
        """
        self.logger.info(f"Cargando datos desde: {self.excel_path}")
        
        try:
            # Detectar si es CSV o Excel
            file_ext = Path(self.excel_path).suffix.lower()
            
            if file_ext == '.csv':
                self.logger.info("   Detectado formato CSV")
                df = pd.read_csv(self.excel_path, encoding='utf-8-sig')
            elif file_ext in ['.xlsx', '.xls']:
                self.logger.info("   Detectado formato Excel")
                df = pd.read_excel(self.excel_path)
            else:
                # Intentar leer como Excel primero, luego CSV
                try:
                    df = pd.read_excel(self.excel_path)
                    self.logger.info("   Leído como Excel")
                except:
                    df = pd.read_csv(self.excel_path, encoding='utf-8-sig')
                    self.logger.info("   Leído como CSV")
            
            self.logger.info(f"Total de registros cargados: {len(df)}")
            
            # Filtrar por estados válidos
            df_filtered = df[df['Estado Actual'].isin(self.VALID_STATES)]
            
            self.logger.info(f"Registros con estados válidos: {len(df_filtered)}")
            
            # Verificar que tenga la columna de teléfono
            if 'Teléfono' not in df_filtered.columns:
                raise ValueError("El archivo no tiene la columna 'Teléfono'")
            
            # Eliminar duplicados por teléfono
            df_filtered = df_filtered.drop_duplicates(subset=['Teléfono'])
            
            self.logger.info(f"Registros únicos a procesar: {len(df_filtered)}")
            
            return df_filtered
            
        except Exception as e:
            self.logger.error(f"✗ Error al cargar archivo: {str(e)}")
            raise
    
    def run(self):
        """Ejecuta el bot completo con checkpoint y verificación de tiempos"""
        self.logger.info("="*80)
        self.logger.info("INICIANDO BOT DE REPORTES DROPI")
        self.logger.info("="*80)
        
        try:
            # Cargar datos
            df = self._load_excel_data()
            self.stats['total'] = len(df)
            
            # Cargar checkpoint del día actual
            df_checkpoint = pd.DataFrame()
            checkpoint_file = self._get_today_results_file()
            if checkpoint_file:
                try:
                    df_checkpoint = pd.read_csv(checkpoint_file)
                    self.logger.info(f"📋 Checkpoint cargado: {len(df_checkpoint)} registros")
                except:
                    self.logger.warning("⚠️ No se pudo cargar checkpoint")
            
            # Obtener línea de inicio desde checkpoint
            start_line = self._load_checkpoint(df)
            
            # Inicializar navegador
            self._init_driver()
            
            # Login
            if not self._login():
                raise Exception("No se pudo iniciar sesión")
            
            # SIEMPRE navegar a Mis Pedidos después del login inicial
            self.logger.info("")
            self.logger.info("📍 Navegando a Mis Pedidos después del login...")
            if not self._navigate_to_orders():
                raise Exception("No se pudo navegar a Mis Pedidos después del login")
            self.logger.info("✅ Navegado a Mis Pedidos exitosamente")
            self.logger.info("")
            
            # Procesar cada orden desde el checkpoint
            results = []
            df_to_process = df.iloc[start_line:].reset_index(drop=True)
            
            self.logger.info("")
            self.logger.info(f"📊 Procesando {len(df_to_process)} órdenes (desde línea {start_line + 1})")
            self.logger.info("")
            
            for idx, (index, row) in enumerate(df_to_process.iterrows()):
                phone = row['Teléfono']
                state = row['Estado Actual']
                line_number = start_line + idx
                
                self.logger.info("")
                self.logger.info(f"{'='*80}")
                self.logger.info(f"Procesando orden {idx + 1}/{len(df_to_process)} (Línea {line_number + 1})")
                self.logger.info(f"Teléfono: {phone} | Estado: {state}")
                self.logger.info(f"{'='*80}")
                
                # Verificar si la orden puede ser procesada según tiempos
                can_process, time_info = self._check_order_can_be_processed(phone, df_checkpoint)
                
                if not can_process:
                    self.logger.warning(f"⏳ Orden saltada - Falta tiempo para reintentar")
                    self.logger.warning(f"   Status anterior: {time_info['status']}")
                    self.logger.warning(f"   Horas restantes: {time_info['hours_remaining']:.2f}")
                    self.logger.warning(f"   Próximo intento: {time_info['next_attempt_time']}")
                    
                    # Agregar registro con información de tiempo
                    result = {
                        'line_number': line_number,
                        'phone': str(phone),
                        'order_id': '',
                        'status': time_info['status'],
                        'report_generated': False,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'hours_since_last_report': None,
                        'next_attempt_time': time_info['next_attempt_time'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(time_info['next_attempt_time'], datetime) else str(time_info['next_attempt_time']),
                        'retry_count': 0
                    }
                    results.append(result)
                    self.stats['saltados_por_tiempo'] += 1
                    # Guardar en tiempo real
                    self._save_results([result], append=True)
                    continue
                
                # Verificar si hay reintentos previos
                retry_count = 0
                if not df_checkpoint.empty:
                    prev_records = df_checkpoint[df_checkpoint['phone'] == str(phone)]
                    if not prev_records.empty:
                        retry_count = int(prev_records.iloc[-1].get('retry_count', 0)) + 1
                
                # Indicar si es la primera orden procesada
                is_first = (idx == 0 and start_line == 0)
                
                # Procesar orden
                result = self._process_single_order(phone, state, line_number, is_first_order=is_first, retry_count=retry_count)
                
                # Si hubo timeout y sesión expirada, relogear y reintentar
                if result['status'] == 'session_expired':
                    self.logger.warning("⚠️ Sesión expirada durante procesamiento - Relogueando...")
                    if self._relogin_and_retry():
                        # _relogin_and_retry ya navegó a Mis Pedidos, solo reintentar la orden
                        self.logger.info(f"🔄 Reintentando orden después de relogin...")
                        # Reintentar la misma orden (ya estamos en Mis Pedidos)
                        result = self._process_single_order(phone, state, line_number, is_first_order=False, retry_count=retry_count)
                        self.stats['reintentos'] += 1
                    else:
                        self.logger.error("❌ No se pudo relogear - Abortando")
                        break
                
                # Verificar si después de reintentar falló de nuevo después del tiempo requerido
                if result['status'] in ['cannot_generate_yet', 'already_has_case'] and retry_count > 0:
                    # Si ya había intentado antes y vuelve a fallar, marcar como en movimiento
                    prev_status = None
                    if not df_checkpoint.empty:
                        prev_records = df_checkpoint[df_checkpoint['phone'] == str(phone)]
                        if not prev_records.empty:
                            prev_status = prev_records.iloc[-1].get('status')
                    
                    if prev_status in ['cannot_generate_yet', 'already_has_case']:
                        self.logger.warning(f"⚠️ Orden {phone} falló de nuevo después de tiempo requerido - Marcando como en movimiento")
                        result['status'] = 'in_movement'
                        result['next_attempt_time'] = self._calculate_next_attempt_time('in_movement', retry_count).strftime('%Y-%m-%d %H:%M:%S')
                
                # Log del resultado
                if result['status'] == 'success':
                    self.logger.info(f"✅ ÉXITO: Reporte generado exitosamente")
                elif result['status'] == 'already_has_case':
                    self.logger.warning(f"⚠️ Orden ya tiene caso - Próximo intento: {result.get('next_attempt_time', 'N/A')}")
                elif result['status'] == 'cannot_generate_yet':
                    self.logger.warning(f"⚠️ No se puede generar aún - Próximo intento: {result.get('next_attempt_time', 'N/A')}")
                elif result['status'] == 'in_movement':
                    self.logger.warning(f"⚠️ Orden en movimiento - Próximo intento: {result.get('next_attempt_time', 'N/A')}")
                else:
                    self.logger.warning(f"⚠️ FALLO: {result.get('status', 'error')}")
                
                # Guardar en tiempo real INMEDIATAMENTE después de procesar cada orden
                # Esto permite monitoreo en vivo y evita pérdida de datos si falla
                # El guardado debe ser síncrono para asegurar que se escriba antes de continuar
                self._save_results([result], append=True)
                
                # Agregar a lista después de guardar (para estadísticas finales)
                results.append(result)
                
                # Pequeña pausa entre órdenes
                time.sleep(1)  # Reducido de 2s a 1s
            
            # Mostrar estadísticas finales
            self._print_final_stats()
            
        except Exception as e:
            self.logger.error(f"✗ Error fatal: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise
            
        finally:
            # Cerrar navegador
            if self.driver:
                self.logger.info("Cerrando navegador...")
                self.driver.quit()
    
    def _save_results(self, results):
        """Guarda los resultados en un archivo CSV"""
        try:
            base_dir = Path(__file__).parent.parent.parent.parent
            results_dir = base_dir / 'results' / 'reporter'
            results_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_file = results_dir / f'dropi_reporter_results_{timestamp}.csv'
            
            df_results = pd.DataFrame(results)
            df_results.to_csv(results_file, index=False, encoding='utf-8-sig')
            
            self.logger.info(f"✓ Resultados guardados en: {results_file}")
            
        except Exception as e:
            self.logger.error(f"✗ Error al guardar resultados: {str(e)}")
    
    def _print_final_stats(self):
        """Imprime las estadísticas finales"""
        self.logger.info("")
        self.logger.info("="*80)
        self.logger.info("ESTADÍSTICAS FINALES")
        self.logger.info("="*80)
        self.logger.info(f"Total de órdenes:           {self.stats['total']}")
        self.logger.info(f"Procesados exitosamente:    {self.stats['procesados']}")
        self.logger.info(f"Ya tenían caso abierto:     {self.stats['ya_tienen_caso']}")
        self.logger.info(f"No encontrados:             {self.stats['no_encontrados']}")
        self.logger.info(f"Saltados por tiempo:        {self.stats['saltados_por_tiempo']}")
        self.logger.info(f"Reintentos:                  {self.stats['reintentos']}")
        self.logger.info(f"Errores:                    {self.stats['errores']}")
        self.logger.info("="*80)
        
        # Calcular tasa de éxito
        if self.stats['total'] > 0:
            success_rate = (self.stats['procesados'] / self.stats['total']) * 100
            self.logger.info(f"Tasa de éxito: {success_rate:.2f}%")
        
        self.logger.info("="*80)


class Command(BaseCommand):
    """Comando de Django para ejecutar el bot de reportes"""
    
    help = 'Ejecuta el bot de reportes automáticos para Dropi'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--excel',
            type=str,
            required=True,
            help='Ruta al archivo Excel o CSV con los datos de trazabilidad'
        )
        
        parser.add_argument(
            '--headless',
            action='store_true',
            help='Ejecutar el navegador en modo headless (sin interfaz gráfica)'
        )
    
    def handle(self, *args, **options):
        excel_path = options['excel']
        headless = options['headless']
        
        # Verificar que el archivo existe
        if not os.path.exists(excel_path):
            self.stdout.write(
                self.style.ERROR(f'El archivo no existe: {excel_path}')
            )
            return
        
        # Crear y ejecutar el bot
        bot = DropiReporterBot(excel_path=excel_path, headless=headless)
        
        try:
            bot.run()
            self.stdout.write(
                self.style.SUCCESS('✓ Bot ejecutado exitosamente')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error al ejecutar el bot: {str(e)}')
            )
            raise