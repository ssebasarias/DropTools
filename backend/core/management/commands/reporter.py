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
from core.models import User, OrderReport, ReportBatch, OrderMovementReport, RawOrderSnapshot
from django.utils import timezone
from core.utils.stdio import configure_utf8_stdio


class DropiReporterBot:
    """Bot para automatizar reportes en Dropi"""
    
    # Credenciales (NO hardcodeadas; se cargan desde BD o ENV)
    DROPI_EMAIL = None
    DROPI_PASSWORD = None
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
    
    def __init__(self, excel_path=None, headless=False, user_id=None, dropi_label="reporter", email=None, password=None):
        """
        Inicializa el bot
        
        Args:
            excel_path: (Opcional) Ruta al archivo Excel o CSV. Si es None, carga de BD.
            headless: Si True, ejecuta el navegador sin interfaz gráfica
            user_id: ID del usuario (tabla users.id) para cargar credenciales de Dropi desde BD
            dropi_label: etiqueta de la cuenta Dropi a usar (default: reporter).
            email: Email de DropiAccount a usar directamente.
            password: Password de DropiAccount a usar directamente.
        """
        self.excel_path = excel_path
        self.headless = headless
        self.user_id = user_id
        self.dropi_label = dropi_label
        self.dropi_email_direct = email
        self.dropi_password_direct = password
        self.driver = None
        self.wait = None
        self.logger = self._setup_logger()
        self.current_order_row = None
        self.df_data = None
        self.stats = {
            'total': 0,
            'procesados': 0,
            'ya_tienen_caso': 0,
            'errores': 0,
            'no_encontrados': 0,
            'saltados_por_tiempo': 0,
            'reintentos': 0
        }
        self.TIMEOUT_SECONDS = 15
        self.session_expired = False
        self.current_processing_step = None

        if not self.user_id:
            raise ValueError("user_id es requerido para usar el sistema de reportes en BD")

        self._load_dropi_credentials()
        
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

    def _load_dropi_credentials(self):
        """
        Prioridad de carga de credenciales:
        1) Si vienen email/password directamente (desde argumentos): usarlos
        2) Si viene user_id: buscar DropiAccount de ese usuario (primero por label, si no por is_default)
        3) Si no hay user_id o no hay cuenta: fallback a ENV (DROPI_EMAIL/DROPI_PASSWORD)
        """
        # Prioridad 1: Credenciales directas (pasadas desde orquestador)
        if self.dropi_email_direct and self.dropi_password_direct:
            self.DROPI_EMAIL = self.dropi_email_direct
            self.DROPI_PASSWORD = self.dropi_password_direct
            self.logger.info("✅ Dropi creds desde argumentos directos (--email/--password)")
            return

        # Prioridad 2: Intentar desde BD (ahora las credenciales están en User directamente)
        if self.user_id:
            user = User.objects.filter(id=self.user_id).first()
            if not user:
                raise ValueError(f"user_id={self.user_id} no existe")

            if user.dropi_email and user.dropi_password:
                self.DROPI_EMAIL = user.dropi_email
                self.DROPI_PASSWORD = user.get_dropi_password_plain()
                self.logger.info(f"✅ Dropi creds desde BD (user_id={self.user_id}, email={user.dropi_email})")
                return

        # Prioridad 3: Fallback ENV
        self.DROPI_EMAIL = os.getenv("DROPI_EMAIL")
        self.DROPI_PASSWORD = os.getenv("DROPI_PASSWORD")
        if self.DROPI_EMAIL and self.DROPI_PASSWORD:
            self.logger.info("✅ Dropi creds desde ENV (DROPI_EMAIL/DROPI_PASSWORD)")
            return

        raise ValueError(
            "No hay credenciales Dropi. Proporciona --email/--password, configura DropiAccount en BD "
            "para ese usuario, o define DROPI_EMAIL/DROPI_PASSWORD en el entorno."
        )
    
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
            
            # Navegar a Mis Pedidos después de relogear (la función ya verifica si ya está ahí)
            self.logger.info("📍 Verificando navegación a Mis Pedidos después de relogin...")
            if not self._navigate_to_orders():
                self.logger.error("❌ Error al navegar a Mis Pedidos después de relogin")
                return False
            
            self.session_expired = False
            self.logger.info("✅ Relogin exitoso - En Mis Pedidos - Continuando desde donde se quedó")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error en relogin: {str(e)}")
            return False
    
    def _check_order_already_reported(self, phone):
        """
        Verifica si una orden ya fue reportada exitosamente (no se puede volver a reportar)
        
        Returns:
            OrderReport si existe y está reportada, None en caso contrario
        """
        try:
            user = User.objects.get(id=self.user_id)
            report = OrderReport.objects.filter(
                user=user,
                order_phone=str(phone),
                status='reportado'
            ).first()
            
            if report:
                self.logger.info(f"✅ Orden {phone} ya fue reportada exitosamente (ID: {report.id})")
                return report
            return None
        except Exception as e:
            self.logger.warning(f"⚠️ Error al verificar orden reportada: {str(e)}")
            return None
    
    def _get_order_report(self, phone):
        """
        Obtiene el reporte más reciente de una orden (si existe)
        
        Returns:
            OrderReport o None
        """
        try:
            user = User.objects.get(id=self.user_id)
            report = OrderReport.objects.filter(
                user=user,
                order_phone=str(phone)
            ).order_by('-created_at').first()
            
            return report
        except Exception as e:
            self.logger.warning(f"⚠️ Error al obtener reporte: {str(e)}")
            return None
    
    def _check_order_can_be_processed(self, phone):
        """
        Verifica si una orden puede ser procesada según tiempos requeridos y estado
        
        Returns:
            (can_process: bool, time_info: dict o None)
        """
        # Primero verificar si ya fue reportada exitosamente (no se puede volver a reportar)
        if self._check_order_already_reported(phone):
            return False, {
                'status': 'reportado',
                'reason': 'already_reported',
                'message': 'Orden ya fue reportada exitosamente'
            }
        
        # Obtener el reporte más reciente
        report = self._get_order_report(phone)
        
        if not report:
            # No hay reporte previo, se puede procesar
            return True, None
        
        # Verificar si tiene next_attempt_time y aún no ha llegado
        if report.next_attempt_time:
            now = timezone.now()
            if now < report.next_attempt_time:
                hours_remaining = (report.next_attempt_time - now).total_seconds() / 3600
                return False, {
                    'status': report.status,
                    'hours_remaining': hours_remaining,
                    'next_attempt_time': report.next_attempt_time,
                    'reason': 'waiting_time'
                }
        
        # Si el estado es 'reportado', no se puede procesar
        if report.status == 'reportado':
            return False, {
                'status': 'reportado',
                'reason': 'already_reported',
                'message': 'Orden ya fue reportada exitosamente'
            }
        
        # En otros casos, se puede procesar
        return True, None
    
    def _calculate_next_attempt_time(self, status, retry_count=0):
        """
        Calcula el tiempo del próximo intento según el estado
        
        Nota: 
        - 'success' y 'already_has_case' → No se calcula (se marca como 'reportado' y no se reintenta)
        - 'cannot_generate_yet' → 24 horas
        - Otros estados → No se calcula (puede reintentar inmediatamente)
        """
        now = timezone.now()
        
        if status == 'cannot_generate_yet':
            # 24 horas para órdenes que aún no cumplen el tiempo requerido
            return now + timedelta(hours=24)
        else:
            # Para otros estados, no se calcula (None = puede reintentar inmediatamente)
            return None
    
    def _init_driver(self):
        """
        Inicializa el driver de Selenium con configuración robusta para Docker y Local
        """
        self.logger.info("="*60)
        self.logger.info("🚀 INICIALIZANDO NAVEGADOR CHROME")
        self.logger.info("="*60)
        
        options = webdriver.ChromeOptions()
        
        # Configuración base
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-notifications')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--disable-popup-blocking')
        
        # Anti-detección básico
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Modo Headless (siempre recomendado en Docker)
        if self.headless:
            self.logger.info("🔇 Modo HEADLESS activado (navegador oculto)")
            options.add_argument('--headless=new')
        else:
            self.logger.info("👀 Modo VISIBLE activado")

        # Configuración de perfil temporal (evita problemas de permisos)
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix='chrome_selenium_')
        options.add_argument(f'--user-data-dir={temp_dir}')
        self.logger.info(f"   📁 Usando perfil temporal: {temp_dir}")
        
        # Preferencias
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        }
        options.add_experimental_option("prefs", prefs)
        
        self.logger.info("   📦 Creando instancia de Chrome...")
        
        try:
            # Intentar usar chromedriver del sistema (típico en Docker alpine/debian)
            from selenium.webdriver.chrome.service import Service
            
            chromedriver_path = None
            # Rutas comunes en Linux/Docker
            possible_paths = ['/usr/bin/chromedriver', '/usr/local/bin/chromedriver', '/usr/lib/chromium/chromedriver']
            
            for path in possible_paths:
                if os.path.exists(path):
                    chromedriver_path = path
                    self.logger.info(f"   📍 Chromedriver encontrado en: {path}")
                    break
            
            if chromedriver_path:
                service = Service(chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
                self.logger.info("   ✅ Chrome iniciado correctamente (con driver del sistema)")
            else:
                # Fallback: dejar que selenium manager lo descargue (puede fallar en docker sin internet/permisos)
                self.logger.info("   ⚠️ No se encontró driver del sistema, intentando Selenium Manager...")
                self.driver = webdriver.Chrome(options=options)
                self.logger.info("   ✅ Chrome iniciado correctamente (Selenium Manager)")
                
        except Exception as e:
            self.logger.error(f"   ❌ Error al iniciar Chrome: {e}")
            self.logger.info("   💡 Verificando instalación de Chrome/Chromium...")
            try:
                # Debug info
                import subprocess
                res = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
                self.logger.info(f"   which google-chrome: {res.stdout.strip()}")
                res = subprocess.run(['which', 'chromium'], capture_output=True, text=True)
                self.logger.info(f"   which chromium: {res.stdout.strip()}")
                res = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True)
                self.logger.info(f"   which chromedriver: {res.stdout.strip()}")
            except: pass
            raise e
        
        # Anti-detección adicional
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Configurar timeouts
        self.wait = WebDriverWait(self.driver, self.TIMEOUT_SECONDS)
        
        self.logger.info(f"   🌐 Navegador listo")
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
        1. Verificar si ya está en la página correcta (evita navegación innecesaria)
        2. Intento 1: Navegación por menú (método tradicional)
        3. Intento 2: Navegación directa por URL (fallback robusto)
        4. Intento 3: Navegación directa con espera extendida
        
        Args:
            retry_count: Número de intento actual
            max_retries: Máximo número de reintentos
            
        Returns:
            True si la navegación fue exitosa, False en caso contrario
        """
        # VERIFICACIÓN INICIAL: Si ya estamos en la página correcta, no navegar
        try:
            current_url = self.driver.current_url
            if '/dashboard/orders' in current_url:
                self.logger.info("="*60)
                self.logger.info("📍 VERIFICACIÓN: Ya estamos en Mis Pedidos")
                self.logger.info("="*60)
                self.logger.info(f"   ✅ URL actual: {current_url}")
                self.logger.info("   ✅ No es necesario navegar - Continuando...")
                return True
        except Exception:
            # Si hay error al obtener la URL, continuar con la navegación normal
            pass
        
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
            # Intentar múltiples selectores para robustez (Español, Inglés, Clases)
            new_consultation_button = None
            
            selectors_to_try = [
                "a[title='Nueva consulta'] i.fa-headset",         # Español Exacto
                "a[title='New request'] i.fa-headset",            # Inglés Exacto (Corregido)
                "a[title='Nueva consulta'] i.fas.fa-headset",     # Español con clase completa
                "a[title='New request'] i.fas.fa-headset",       # Inglés con clase completa
                "a i.fa-headset",                                 # Genérico
                "a i.fas.fa-headset"                              # Genérico completo
            ]
            
            for selector in selectors_to_try:
                try:
                    new_consultation_button = row.find_element(By.CSS_SELECTOR, selector)
                    self.logger.info(f"   ✅ Botón encontrado con selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not new_consultation_button:
                # Intento final: buscar cualquier botón en la última columna que no sea Editar/Ver
                self.logger.warning("   ⚠️ No se encontró por selectores específicos, buscando genérico...")
                try:
                    # Buscar todos los botones de acción en la fila
                    actions = row.find_elements(By.CSS_SELECTOR, "td a.btn")
                    for action in actions:
                        # Si tiene icono de headset, es ese
                        if action.find_elements(By.CSS_SELECTOR, "i.fa-headset"):
                            new_consultation_button = action.find_element(By.CSS_SELECTOR, "i")
                            self.logger.info("   ✅ Botón encontrado por búsqueda genérica")
                            break
                except: pass
            
            if not new_consultation_button:
                raise NoSuchElementException("No se pudo encontrar el botón de Nueva Consulta con ningún selector")
            
            self.logger.info("   ✅ Botón 'Nueva consulta' encontrado en la fila correcta")
            
            # Scroll al elemento
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", new_consultation_button)
            time.sleep(1)
            
            # Click en el padre (el <a>) si encontramos el <i>, o directo si encontramos el <a>
            if new_consultation_button.tag_name == 'i':
                parent_link = new_consultation_button.find_element(By.XPATH, "..")
            else:
                parent_link = new_consultation_button
            
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
        """Selecciona el tipo de consulta: Transportadora / Carrier"""
        self.logger.info("Seleccionando tipo de consulta: Transportadora/Carrier...")
        
        try:
            self.logger.info("   1) Buscando dropdown de tipo de consulta...")
            
            # Selector robusto multilingüe para el dropdown "Type of inquiry"
            # Busca un botón con clase 'select-button' que tenga un hermano label o p cercano con el texto
            dropdown_xpath = "//button[contains(@class, 'select-button') and (descendant::p[contains(text(), 'Select the type')] or descendant::p[contains(text(), 'Selecciona el tipo')] or preceding-sibling::span[contains(text(), 'Type of inquiry')] or preceding-sibling::span[contains(text(), 'Tipo de consulta')])]"
            
            # Alternativa CSS si XPath falla
            dropdown_css = ".select-container:first-child .select-button" 
            
            try:
                type_dropdown = self.wait.until(EC.element_to_be_clickable((By.XPATH, dropdown_xpath)))
            except:
                type_dropdown = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, dropdown_css)))
                
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
            time.sleep(1) 
            self.logger.info("   ✅ Dropdown abierto")
            
            # Seleccionar "Transportadora" o "Carrier"
            self.logger.info("   3) Buscando opción 'Transportadora'/'Carrier'...")
            
            carrier_xpath = "//button[contains(@class, 'option') and (contains(., 'Transportadora') or contains(., 'Carrier'))]"
            
            transportadora_option = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, carrier_xpath))
            )
            self.logger.info("   ✅ Opción encontrada")
            
            self.logger.info("   4) Seleccionando 'Transportadora'/'Carrier'...")
            # Scroll y click
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", transportadora_option)
            time.sleep(0.5)
            try:
                transportadora_option.click()
            except:
                self.driver.execute_script("arguments[0].click();", transportadora_option)
            time.sleep(1)
            
            self.logger.info("✅ Tipo de consulta seleccionado: Transportadora/Carrier")
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
            
            # Selector robusto multilingüe
            dropdown_xpath = "//button[contains(@class, 'select-button') and (descendant::div[contains(text(), 'Select the reason')] or descendant::div[contains(text(), 'Selecciona el motivo')] or preceding-sibling::span[contains(text(), 'Reason for query')] or preceding-sibling::span[contains(text(), 'Motivo de consulta')])]"
            
            # Alternativa CSS (es el segundo .ticket-selector o similar)
            dropdown_css = ".ticket-selector:nth-of-type(2) .select-button"
            
            try:
                reason_dropdown = self.wait.until(EC.element_to_be_clickable((By.XPATH, dropdown_xpath)))
            except:
                reason_dropdown = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, dropdown_css)))
                
            self.logger.info("   ✅ Dropdown encontrado")
            
            # Scroll al elemento
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", reason_dropdown)
            time.sleep(0.5)
            
            self.logger.info("   2) Haciendo click en dropdown...")
            try:
                reason_dropdown.click()
            except:
                self.driver.execute_script("arguments[0].click();", reason_dropdown)
            time.sleep(1)
            self.logger.info("   ✅ Dropdown abierto")
            
            # Seleccionar "Ordenes sin movimiento"
            self.logger.info("   3) Buscando opción 'Ordenes sin movimiento'...")
            
            # Busca texto en español o varias variantes en inglés
            option_xpath = "//button[contains(@class, 'option') and (contains(., 'Ordenes sin movimiento') or contains(., 'No movement') or contains(., 'without movement'))]"
            
            no_movement_option = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, option_xpath))
            )
            self.logger.info("   ✅ Opción encontrada")
            
            self.logger.info("   4) Seleccionando 'Ordenes sin movimiento'...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", no_movement_option)
            time.sleep(0.5)
            try:
                no_movement_option.click()
            except:
                self.driver.execute_script("arguments[0].click();", no_movement_option)
            time.sleep(1)
            
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
            
            # Selector multilingüe para botón "Siguiente" / "Next"
            next_xpath = "//button[contains(@class, 'btn') and (descendant::span[contains(text(), 'Siguiente')] or descendant::span[contains(text(), 'Next')])]"
            
            next_button = short_wait.until(
                EC.element_to_be_clickable((By.XPATH, next_xpath))
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
            
            # Buscar el textarea (Multilingüe: ID o Placeholder)
            textarea = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "textarea[id='description'], textarea[placeholder*='Tell the conveyor'], textarea[placeholder*='transportadora']"
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
            # Selector multilingüe para botón "Iniciar..." / "Start..."
            start_xpath = "//button[contains(@class, 'btn') and (descendant::span[contains(text(), 'Iniciar un')] or descendant::span[contains(text(), 'Start a conversation')])]"
            
            start_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, start_xpath))
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
                    # Orden ya tiene caso → marcar como 'reportado' (no se puede volver a reportar)
                    result['status'] = 'reportado'  # Cambiado de 'already_has_case' a 'reportado'
                    result['report_generated'] = True  # Se considera reportado aunque ya tenía caso
                    result['next_attempt_time'] = None  # No se reintenta
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
                next_attempt = self._calculate_next_attempt_time('cannot_generate_yet', retry_count)
                result['next_attempt_time'] = next_attempt.strftime('%Y-%m-%d %H:%M:%S') if next_attempt else None
                
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
                    next_attempt = self._calculate_next_attempt_time('cannot_generate_yet', retry_count)
                    result['next_attempt_time'] = next_attempt.strftime('%Y-%m-%d %H:%M:%S') if next_attempt else None
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
            result['status'] = 'reportado'  # Cambiado de 'success' a 'reportado'
            result['report_generated'] = True
            result['next_attempt_time'] = None  # No se reintenta (ya está reportado)
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
            tel_col = None
            for col in df_filtered.columns:
                if 'tel' in col.lower() or 'fono' in col.lower():
                    tel_col = col
                    break
            
            if not tel_col:
                raise ValueError("El archivo no tiene la columna 'Teléfono'")
            
            # Renombrar columna de teléfono para consistencia
            if tel_col != 'Teléfono':
                df_filtered = df_filtered.rename(columns={tel_col: 'Teléfono'})
            
            # FILTRAR ÓRDENES MUY RECIENTES (menos de 2 días desde la orden)
            # Esto optimiza el tiempo evitando procesar órdenes que definitivamente requerirán espera
            # Basado en análisis: órdenes con <2 días siempre requieren espera de 24h
            dias_col = None
            for col in df_filtered.columns:
                col_lower = col.lower()
                if 'dias' in col_lower or 'día' in col_lower or 'dia' in col_lower or 'dias desde' in col_lower:
                    dias_col = col
                    break
            
            if dias_col:
                antes_filtro = len(df_filtered)
                # Asegurar que la columna sea numérica
                df_filtered[dias_col] = pd.to_numeric(df_filtered[dias_col], errors='coerce')
                df_filtered = df_filtered[df_filtered[dias_col] >= 2]
                filtradas = antes_filtro - len(df_filtered)
                if filtradas > 0:
                    self.logger.info(f"   ⚡ Órdenes filtradas (muy recientes, <2 días): {filtradas}")
                    self.logger.info(f"   ✅ Órdenes elegibles para procesar (≥2 días): {len(df_filtered)}")
            elif 'Fecha' in df_filtered.columns:
                # Calcular días desde orden si no existe la columna
                try:
                    from datetime import datetime as dt
                    now = datetime.now()
                    df_filtered['Fecha_parsed'] = pd.to_datetime(df_filtered['Fecha'], errors='coerce', dayfirst=True)
                    df_filtered['Días desde Orden'] = (now - df_filtered['Fecha_parsed']).dt.days
                    
                    antes_filtro = len(df_filtered)
                    df_filtered = df_filtered[df_filtered['Días desde Orden'] >= 2]
                    filtradas = antes_filtro - len(df_filtered)
                    if filtradas > 0:
                        self.logger.info(f"   ⚡ Órdenes filtradas (muy recientes, <2 días): {filtradas}")
                        self.logger.info(f"   ✅ Órdenes elegibles para procesar (≥2 días): {len(df_filtered)}")
                    
                    df_filtered = df_filtered.drop(columns=['Fecha_parsed'], errors='ignore')
                except Exception as e:
                    self.logger.warning(f"   ⚠️ No se pudo filtrar por días: {str(e)}")
            
            # Eliminar duplicados por teléfono
            antes_dup = len(df_filtered)
            df_filtered = df_filtered.drop_duplicates(subset=['Teléfono'])
            duplicados = antes_dup - len(df_filtered)
            if duplicados > 0:
                self.logger.info(f"   📋 Duplicados eliminados: {duplicados}")
            
            self.logger.info(f"   ✅ Registros únicos a procesar: {len(df_filtered)}")
            
            return df_filtered
            
        except Exception as e:
            self.logger.error(f"✗ Error al cargar archivo: {str(e)}")
            raise
    
    def _load_db_data(self):
        """
        Carga las órdenes pendientes desde OrderMovementReport en lugar de un archivo.
        
        Returns:
            DataFrame con las columnas esperadas por el bot
        """
        self.logger.info("🔍 CONSULTANDO BASE DE DATOS (OrderMovementReport)...")
        
        # 1. Buscar último Batch exitoso del usuario
        try:
            latest_batch = ReportBatch.objects.filter(
                user_id=self.user_id,
                status='SUCCESS'
            ).order_by('-created_at').first()
            
            if not latest_batch:
                self.logger.error("❌ No se encontraron lotes de reportes para este usuario.")
                return pd.DataFrame() # Vacío
            
            self.logger.info(f"   📅 Lote encontrado: ID {latest_batch.id} ({latest_batch.created_at})")
            
            # 2. Buscar órdenes pendientes no resueltas
            pending_items = OrderMovementReport.objects.filter(
                batch=latest_batch,
                is_resolved=False
            ).select_related('snapshot')
            
            count = pending_items.count()
            self.logger.info(f"   📊 Órdenes pendientes por resolver: {count}")
            
            if count == 0:
                self.logger.info("   ✅ Nada pendiente. Todo está limpio.")
                return pd.DataFrame()

            # 3. Construir lista de diccionarios con el formato esperado
            data_list = []
            for item in pending_items:
                snap = item.snapshot
                data_list.append({
                    'Teléfono': snap.customer_phone,
                    'Estado Actual': snap.current_status,
                    'ID Orden': snap.dropi_order_id,
                    'Cliente': snap.customer_name,
                    'Producto': snap.product_name,
                    'Días desde Orden': item.days_since_order,
                    # COLUMNAS NUEVAS PARA CONTROL INTERNO
                    '_db_report_id': item.id,  # Para marcar resolved después
                })
            
            # 4. Crear DataFrame
            df = pd.DataFrame(data_list)
            
            # Asegurar tipos
            df['Teléfono'] = df['Teléfono'].astype(str)
            
            self.logger.info(f"   ✅ DataFrame construido con {len(df)} registros.")
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error al consultar DB: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise

    def run(self):
        """Ejecuta el bot completo usando BD o Archivo según configuración"""
        self.logger.info("="*80)
        self.logger.info("INICIANDO BOT DE REPORTES DROPI")
        self.logger.info("="*80)
        
        try:
            # 1. Cargar datos (DB o Excel)
            if self.excel_path:
                self.logger.info("📂 Modo: Archivo Excel/CSV")
                df = self._load_excel_data()
            else:
                self.logger.info("🗄️ Modo: Base de Datos")
                df = self._load_db_data()
            
            if df.empty:
                self.logger.info("⚠️ No hay datos para procesar.")
                return 

            # Filtrar si todavía no está filtrado (solo aplica si viene de Excel/CSV a veces, 
            # pero desde DB ya viene filtrado is_resolved=False. 
            # El filtro de estados validos ya se aplicó en ReportComparer, pero no daña re-checkear)
            # Reutilizamos validación de estados por seguridad
            if 'Estado Actual' in df.columns:
                 df = df[df['Estado Actual'].isin(self.VALID_STATES)]
            
            self.stats['total'] = len(df)
            
            # Guardar DataFrame completo para acceso rápido a información
            self.df_data = df.set_index('Teléfono', drop=False)
            
            # Obtener usuario
            user = User.objects.get(id=self.user_id)
            self.logger.info(f"👤 Usuario: {user.email} (ID: {user.id})")
            
            # Contar órdenes ya reportadas en BD (Histórico legado)
            reported_count = OrderReport.objects.filter(user=user, status='reportado').count()
            self.logger.info(f"📊 Histórico global reportado: {reported_count}")
            
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
            
            # Procesar cada orden
            results = []
            
            self.logger.info("")
            self.logger.info(f"📊 Procesando {len(df)} órdenes")
            self.logger.info("")
            
            for idx, (index, row) in enumerate(df.iterrows()):
                phone = row['Teléfono']
                state = row['Estado Actual']
                
                # Obtener ID de DB si existe
                db_report_id = row.get('_db_report_id')
                
                self.logger.info("")
                self.logger.info(f"{'='*80}")
                self.logger.info(f"Procesando orden {idx + 1}/{len(df)}")
                self.logger.info(f"Teléfono: {phone} | Estado: {state}")
                self.logger.info(f"{'='*80}")
                
                # Verificar si la orden puede ser procesada (BD check)
                can_process, time_info = self._check_order_can_be_processed(phone)
                
                if not can_process:
                    reason = time_info.get('reason', 'unknown')
                    if reason == 'already_reported':
                        self.logger.info(f"⏭️  Orden saltada - Ya fue reportada exitosamente")
                    elif reason == 'waiting_time':
                        self.logger.warning(f"⏳ Orden saltada - Falta tiempo para reintentar")
                    self.stats['saltados_por_tiempo'] += 1
                    continue
                
                # Obtener reporte previo si existe
                prev_report = self._get_order_report(phone)
                retry_count = 0
                if prev_report:
                    retry_count = OrderReport.objects.filter(user=user, order_phone=phone).exclude(status='reportado').count()
                
                # Indicar si es la primera orden procesada
                is_first = (idx == 0)
                
                # Procesar orden (Selenium Logic)
                result = self._process_single_order(phone, state, idx, is_first_order=is_first, retry_count=retry_count)
                
                # ACTUALIZACIÓN EN BASE DE DATOS (OrderMovementReport)
                if result['status'] == 'reportado' and db_report_id:
                    self.logger.info(f"   💾 Marcando registro DB {db_report_id} como RESUELTO.")
                    try:
                        OrderMovementReport.objects.filter(id=db_report_id).update(
                            is_resolved=True,
                            resolved_at=timezone.now(),
                            resolution_note="Reportado exitosamente por Bot"
                        )
                    except Exception as db_err:
                        self.logger.error(f"   ❌ Error actualizando OrderMovementReport: {db_err}")

                # Guardar en BD (Legacy Tracker)
                # Extraer info adicional
                order_info = {
                    'customer_name': row.get('Cliente'),
                    'product_name': row.get('Producto'),
                    'order_id': row.get('ID Orden')
                }
                result['order_info'] = order_info # Para que _save_results lo use
                
                self._save_results([result], append=True)
                results.append(result)
                
                # Si hubo timeout y sesión expirada, relogear y reintentar
                if result['status'] == 'session_expired':
                    self.logger.warning("⚠️ Sesión expirada durante procesamiento - Relogueando...")
                    if self._relogin_and_retry():
                        self.logger.info(f"🔄 Reintentando orden después de relogin...")
                        result = self._process_single_order(phone, state, idx, is_first_order=False, retry_count=retry_count)
                        if result['status'] == 'reportado' and db_report_id:
                             OrderMovementReport.objects.filter(id=db_report_id).update(is_resolved=True, resolved_at=timezone.now(), resolution_note="Reportado tras retry")
                        
                        result['order_info'] = order_info
                        self._save_results([result], append=True)
                        self.stats['reintentos'] += 1
                    else:
                        break
                
                time.sleep(1)
            
            self._print_final_stats()
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error fatal: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise
            
        finally:
            if self.driver:
                self.logger.info("Cerrando navegador...")
                self.driver.quit()
    
    def _extract_order_info(self, phone):
        """
        Extrae información adicional de la orden desde el CSV (más confiable que la página web)
        
        Returns:
            dict con customer_name, product_name, order_id si están disponibles
        """
        info = {
            'customer_name': None,
            'product_name': None,
            'order_id': None
        }
        
        try:
            # Primero intentar desde el DataFrame del CSV (más confiable)
            if hasattr(self, 'df_data') and self.df_data is not None:
                try:
                    phone_str = str(phone).strip()
                    # Normalizar teléfono: remover espacios, guiones, paréntesis
                    phone_normalized = ''.join(filter(str.isdigit, phone_str))
                    
                    # Buscar por columna 'Teléfono' en lugar del índice
                    if 'Teléfono' in self.df_data.columns:
                        # Normalizar también los teléfonos del DataFrame para comparación
                        df_phones_normalized = self.df_data['Teléfono'].astype(str).apply(
                            lambda x: ''.join(filter(str.isdigit, str(x)))
                        )
                        
                        # Buscar la fila que coincida con el teléfono normalizado
                        matches = self.df_data[df_phones_normalized == phone_normalized]
                        
                        if len(matches) > 0:
                            row = matches.iloc[0]  # Tomar la primera coincidencia
                            
                            # Obtener Cliente
                            if 'Cliente' in self.df_data.columns:
                                customer = row['Cliente']
                                if pd.notna(customer) and str(customer).strip():
                                    info['customer_name'] = str(customer).strip()[:255]
                            
                            # Obtener Producto
                            if 'Producto' in self.df_data.columns:
                                product = row['Producto']
                                if pd.notna(product) and str(product).strip():
                                    info['product_name'] = str(product).strip()[:500]
                            
                            # Obtener ID Orden
                            if 'ID Orden' in self.df_data.columns:
                                order_id = row['ID Orden']
                                if pd.notna(order_id):
                                    info['order_id'] = str(order_id).strip()[:100]
                            
                            self.logger.info(f"   ✅ Información extraída del CSV: Cliente={info['customer_name']}, Producto={info['product_name'][:50] if info['product_name'] else None}...")
                        else:
                            self.logger.warning(f"   ⚠️ No se encontró teléfono {phone_str} en el CSV")
                except Exception as e:
                    self.logger.warning(f"   ⚠️ Error al obtener datos del CSV: {str(e)}")
                    import traceback
                    self.logger.debug(traceback.format_exc())
            
            # Fallback: Intentar desde la página web si no se encontró en CSV
            if not info['customer_name'] or not info['product_name']:
                try:
                    if hasattr(self, 'current_order_row') and self.current_order_row:
                        row = self.current_order_row
                    else:
                        row = self.driver.find_element(By.CSS_SELECTOR, "tbody.list tr:first-child")
                    
                    # Intentar encontrar nombre del cliente en la fila
                    if not info['customer_name']:
                        try:
                            customer_cell = row.find_element(By.CSS_SELECTOR, "td:nth-child(2), td:nth-child(3)")
                            info['customer_name'] = customer_cell.text.strip()[:255] if customer_cell.text else None
                        except:
                            pass
                    
                    # Intentar encontrar ID de orden
                    if not info['order_id']:
                        try:
                            order_id_cell = row.find_element(By.CSS_SELECTOR, "td:first-child, td a")
                            info['order_id'] = order_id_cell.text.strip()[:100] if order_id_cell.text else None
                        except:
                            pass
                    
                    # Intentar encontrar producto
                    if not info['product_name']:
                        try:
                            product_cell = row.find_element(By.CSS_SELECTOR, "td:nth-child(4), td:nth-child(5)")
                            info['product_name'] = product_cell.text.strip()[:500] if product_cell.text else None
                        except:
                            pass
                except Exception as e:
                    self.logger.debug(f"   No se pudo extraer información de la página: {str(e)}")
                    
        except Exception as e:
            self.logger.debug(f"   Error general al extraer información: {str(e)}")
        
        return info
    
    def _save_results(self, results, append=False):
        """
        Guarda los resultados en la base de datos (OrderReport)
        
        Args:
            results: Lista de diccionarios con los resultados
            append: Ignorado (siempre actualiza/crea en BD)
        """
        try:
            user = User.objects.get(id=self.user_id)
            
            for result in results:
                phone = str(result.get('phone', ''))
                if not phone:
                    continue
                
                # Extraer información adicional si está disponible
                order_info = result.get('order_info', {})
                customer_name = order_info.get('customer_name') or result.get('customer_name')
                product_name = order_info.get('product_name') or result.get('product_name')
                order_id = order_info.get('order_id') or result.get('order_id', '')
                
                # Convertir next_attempt_time si existe
                next_attempt_time = None
                if result.get('next_attempt_time'):
                    try:
                        if isinstance(result['next_attempt_time'], str):
                            next_attempt_time = datetime.strptime(result['next_attempt_time'], '%Y-%m-%d %H:%M:%S')
                            next_attempt_time = timezone.make_aware(next_attempt_time)
                        elif isinstance(result['next_attempt_time'], datetime):
                            next_attempt_time = timezone.make_aware(result['next_attempt_time']) if timezone.is_naive(result['next_attempt_time']) else result['next_attempt_time']
                    except:
                        pass
                
                # Obtener o crear el reporte
                report, created = OrderReport.objects.update_or_create(
                    user=user,
                    order_phone=phone,
                    defaults={
                        'order_id': order_id,
                        'status': result.get('status', 'error'),
                        'report_generated': result.get('report_generated', False),
                        'customer_name': customer_name,
                        'product_name': product_name,
                        'order_state': result.get('order_state'),
                        'next_attempt_time': next_attempt_time,
                    }
                )
                
                if created:
                    self.logger.info(f"[OK] Reporte creado en BD: {phone} ({result.get('status')})")
                else:
                    self.logger.info(f"[OK] Reporte actualizado en BD: {phone} ({result.get('status')})")
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error al guardar resultados en BD: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
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
            default=None,
            help='(Opcional) Ruta al archivo Excel o CSV con los datos de trazabilidad. Si no se provee, usa la BD.'
        )
        
        parser.add_argument(
            '--headless',
            action='store_true',
            help='Ejecutar el navegador en modo headless (sin interfaz gráfica)'
        )

        parser.add_argument(
            '--user-id',
            type=int,
            required=True,
            help='ID del usuario (tabla users.id) - REQUERIDO para usar el sistema de reportes en BD'
        )

        parser.add_argument(
            '--dropi-label',
            type=str,
            default='reporter',
            help='Etiqueta de la cuenta Dropi a usar (default: reporter)'
        )

        parser.add_argument(
            '--email',
            type=str,
            default=None,
            help='Email de DropiAccount a usar directamente (sobrescribe user-id/dropi-label)'
        )

        parser.add_argument(
            '--password',
            type=str,
            default=None,
            help='Password de DropiAccount a usar directamente (sobrescribe user-id/dropi-label)'
        )
    
    def handle(self, *args, **options):
        configure_utf8_stdio()
        excel_path = options.get('excel')
        headless = options['headless']
        user_id = options.get('user_id')
        dropi_label = options.get('dropi_label', 'reporter')
        email = options.get('email')
        password = options.get('password')
        
        # Verificar que el archivo existe si se proporcionó
        if excel_path and not os.path.exists(excel_path):
            self.stdout.write(
                self.style.ERROR(f'El archivo no existe: {excel_path}')
            )
            return
        
        # Crear y ejecutar el bot
        bot = DropiReporterBot(
            excel_path=excel_path,
            headless=headless,
            user_id=user_id,
            dropi_label=dropi_label,
            email=email,
            password=password,
        )
        
        try:
            bot.run()
            self.stdout.write(
                self.style.SUCCESS('[OK] Bot ejecutado exitosamente')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error al ejecutar el bot: {str(e)}')
            )
            raise