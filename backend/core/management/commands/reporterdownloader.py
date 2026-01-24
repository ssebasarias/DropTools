"""
Bot Descargador de Reportes para Dropi

Este bot descarga reportes de órdenes de un mes exacto (día X a día X del mes siguiente).

Lógica de ejecución:
- Si la carpeta está vacía: descarga 2 reportes (día anterior y día actual)
- Si la carpeta tiene archivos: descarga solo 1 reporte (día actual)

Ejemplo si hoy es 20/01/2026:
- Si carpeta vacía: descarga reporte del 19 (19/12/2025 a 19/01/2026) y del 20 (20/12/2025 a 20/01/2026)
- Si carpeta tiene archivos: descarga solo reporte del 20 (20/12/2025 a 20/01/2026)

Los archivos se guardan con formato: reporte_YYYYMMDD.xlsx
Ejemplo: reporte_20260120.xlsx (generado el 20/01/2026)

Para comparar los reportes y generar el Excel con órdenes sin movimiento,
usa el comando: python manage.py reportcomparer
"""

import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import glob
import pandas as pd
from django.utils import timezone
from core.models import ReportBatch, RawOrderSnapshot

from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.service import Service
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
from core.utils.stdio import configure_utf8_stdio
from django.conf import settings


class DropiDownloaderReporterBot:
    """
    Bot para descargar reportes de Dropi
    
    Funcionalidad:
    1. Descarga reportes de un mes exacto (día X a día X del mes siguiente)
    2. Detecta si la carpeta está vacía para decidir cuántos reportes descargar
    3. Nombra los archivos con formato: reporte_YYYYMMDD.xlsx (solo la fecha de generación)
    4. Los reportes pueden ser comparados posteriormente con reportcomparer
    """
    
    # Credenciales
    DROPI_EMAIL = "dahellonline@gmail.com"
    DROPI_PASSWORD = "Bigotes2001@"
    DROPI_URL = "https://app.dropi.co/login"
    
    # URLs importantes
    ORDERS_URL = "https://app.dropi.co/dashboard/orders"
    REPORTS_URL = "https://app.dropi.co/dashboard/reports/downloads"
    
    def __init__(self, headless=False, download_dir=None, use_chrome_fallback=False, email=None, password=None, user=None):
        """
        Inicializa el bot
        
        Args:
            headless: Si True, ejecuta el navegador sin interfaz gráfica
            download_dir: Directorio base donde se guardarán los archivos descargados (results/downloads)
            use_chrome_fallback: Si True, usa Chrome en lugar de Edge (útil si Edge no funciona)
            email: Email para login (opcional, sobrescribe default)
            password: Password para login (opcional, sobrescribe default)
        """
        self.headless = headless
        self.use_chrome_fallback = use_chrome_fallback
        self.driver = None
        self.wait = None
        self.logger = self._setup_logger()

        # Update credentials if provided
        if email:
            self.DROPI_EMAIL = email
        if password:
            self.DROPI_PASSWORD = password
        
        # Configurar directorio base de descargas
        if download_dir is None:
            # Directorio por defecto: results/downloads
            base_dir = Path(__file__).parent.parent.parent.parent
            download_dir = base_dir / 'results' / 'downloads'
        
        self.download_dir_base = Path(download_dir)
        self.download_dir_base.mkdir(parents=True, exist_ok=True)
        
        # El directorio de descarga será siempre el base
        self.download_dir = self.download_dir_base
        
        # Las preferencias de descarga se configurarán después
        self.download_prefs = {
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        
        # Estadísticas
        self.stats = {
            'reporte_actual_descargado': False,
            'reporte_anterior_descargado': False,
            'ordenes_sin_movimiento': 0,
            'ordenes_comparadas': 0,
            'errores': 0
        }
        
        # Rutas de archivos descargados
        self.reporte_actual_path = None
        self.reporte_anterior_path = None
        self.excel_resultante_path = None
        
        self.user = user
        
    def _setup_logger(self):
        """Configura el logger para el bot con salida a consola y archivo"""
        logger = logging.getLogger('DropiDownloaderReporterBot')
        logger.setLevel(logging.INFO)
        
        # Limpiar handlers existentes
        logger.handlers.clear()
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Handler para archivo
        log_dir = Path(__file__).parent.parent.parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_handler = logging.FileHandler(
            log_dir / f'reporterdownloader_{timestamp}.log',
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
    
    def _init_driver(self):
        """
        Inicializa el driver de Selenium con configuración para descargas
        
        PASO 1: Configurar Edge (o Chrome como fallback) con preferencias de descarga
        Edge es más permisivo con descargas automáticas que Chrome
        """
        # Decidir qué navegador usar
        # Chrome en modo incógnito es más confiable para descargas y permisos
        if self.use_chrome_fallback:
            return self._init_chrome_driver()
        else:
            # Intentar Edge primero, si falla usar Chrome automáticamente
            try:
                return self._init_edge_driver()
            except Exception as e:
                self.logger.warning(f"   ⚠️ Edge falló, cambiando a Chrome en modo incógnito: {str(e)}")
                return self._init_chrome_driver()
    
    def _init_edge_driver(self):
        """Inicializa Edge WebDriver"""
        self.logger.info("="*80)
        self.logger.info("🚀 PASO 1: INICIALIZANDO NAVEGADOR EDGE")
        self.logger.info("="*80)
        self.logger.info("   ℹ️ Usando Edge (más permisivo con descargas automáticas)")
        
        # Crear instancia de EdgeOptions de forma compatible
        try:
            # Usar EdgeOptions importado directamente (línea 29)
            options = EdgeOptions()
        except Exception as e:
            self.logger.warning(f"   ⚠️ Error creando EdgeOptions estándar: {str(e)}")
            # Si falla, intentar usar Chrome como fallback
            self.logger.info("   🔄 Cambiando a Chrome como fallback...")
            return self._init_chrome_driver()
        
        # Configuración para ejecución LOCAL
        if self.headless:
            self.logger.info("   🔇 Modo HEADLESS activado (navegador oculto)")
            options.add_argument('--headless=new')
        else:
            self.logger.info("   👀 Modo VISIBLE activado (puedes ver el navegador)")
        
        # Optimizaciones
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        
        # Configuraciones críticas para permitir descargas automáticas sin permisos
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-features=DownloadBubble,DownloadBubbleV2')
        options.add_argument('--disable-prompt-on-repost')
        
        # Evitar detección de automatización
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Verificar que el directorio de descarga esté configurado
        if self.download_dir is None:
            self.logger.warning("   ⚠️ Directorio del mes no configurado, usando directorio base temporalmente")
            download_directory = str(self.download_dir_base)
        else:
            self.logger.info(f"   📁 Directorio de descarga configurado: {self.download_dir}")
            download_directory = str(self.download_dir)
        
        # Preferencias incluyendo descargas (actualizar con el directorio correcto)
        # Configuraciones críticas para descargas automáticas sin permisos
        prefs = {
            "profile.default_content_setting_values.notifications": 2,  # Bloquear notificaciones
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            # Configuraciones de descarga críticas
            "download.default_directory": download_directory,
            "download.prompt_for_download": False,  # No pedir confirmación
            "download.directory_upgrade": True,  # Permitir actualizar directorio
            "safebrowsing.enabled": False,  # Deshabilitar Safe Browsing que puede bloquear descargas
            "safebrowsing.disable_download_protection": True,  # Deshabilitar protección de descargas
            # Permitir descargas automáticas
            "profile.default_content_settings.popups": 0,  # Permitir popups (algunos sitios los usan para descargas)
            "profile.content_settings.exceptions.automatic_downloads": {
                "*": {
                    "setting": 1  # Permitir descargas automáticas para todos los sitios
                }
            },
            # Configuración adicional para evitar bloqueos
            "profile.default_content_setting_values.automatic_downloads": 1,  # Permitir descargas automáticas
        }
        options.add_experimental_option("prefs", prefs)
        
        self.logger.info(f"   📂 Directorio de descarga para Edge: {download_directory}")
        self.logger.info("   📦 Creando instancia de Edge...")
        
        try:
            # Intentar inicializar Edge sin Service primero (Selenium 4+ lo maneja automáticamente)
            try:
                self.driver = webdriver.Edge(options=options)
                self.logger.info("   ✅ Edge iniciado correctamente (driver automático)")
            except Exception as auto_error:
                self.logger.warning(f"   ⚠️ Inicialización automática falló: {str(auto_error)}")
                self.logger.info("   🔄 Intentando con webdriver-manager...")
                
                # Intentar con webdriver-manager como fallback
                try:
                    from webdriver_manager.microsoft import EdgeChromiumDriverManager
                    from selenium.webdriver.edge.service import Service
                    
                    service = Service(EdgeChromiumDriverManager().install())
                    self.driver = webdriver.Edge(service=service, options=options)
                    self.logger.info("   ✅ Edge iniciado correctamente (con webdriver-manager)")
                except ImportError:
                    self.logger.error("   ❌ webdriver-manager no está instalado")
                    self.logger.info("   💡 Instala con: pip install webdriver-manager")
                    raise auto_error  # Re-lanzar el error original
                except Exception as manager_error:
                    self.logger.error(f"   ❌ Error con webdriver-manager: {str(manager_error)}")
                    raise auto_error  # Re-lanzar el error original
                    
        except Exception as e:
            self.logger.error("="*80)
            self.logger.error(f"   ❌ ERROR AL INICIALIZAR EDGE")
            self.logger.error("="*80)
            self.logger.error(f"   Error: {str(e)}")
            self.logger.error(f"   Tipo: {type(e).__name__}")
            self.logger.error("")
            self.logger.error("   💡 SOLUCIONES POSIBLES:")
            self.logger.error("   1. Asegúrate de tener Microsoft Edge instalado")
            self.logger.error("   2. Instala webdriver-manager: pip install webdriver-manager")
            self.logger.error("   3. Verifica que Edge esté actualizado")
            self.logger.error("   4. Si el problema persiste, vuelve a Chrome con configuraciones adicionales")
            self.logger.error("="*80)
            raise
        
        # Configurar permisos de descarga explícitamente usando Edge DevTools Protocol
        # Edge es más permisivo que Chrome, pero aún así configuramos explícitamente
        try:
            self.logger.info("   🔧 Configurando permisos de descarga...")
            # Habilitar descargas automáticas para todos los sitios
            self.driver.execute_cdp_cmd('Browser.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': download_directory
            })
            self.logger.info("   ✅ Permisos de descarga configurados")
        except Exception as e:
            self.logger.warning(f"   ⚠️ No se pudo configurar permisos CDP (puede ser normal): {str(e)}")
            # Continuar de todas formas, Edge es más permisivo por defecto
        
        # Anti-detección
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Configurar timeouts
        self.wait = WebDriverWait(self.driver, 30)
        
        self.logger.info(f"   🌐 Navegador listo")
        self.logger.info("="*80)
    
    def _init_chrome_driver(self):
        """Inicializa Chrome WebDriver como fallback (con solución mejorada para permisos)"""
        self.logger.info("="*80)
        self.logger.info("🚀 PASO 1: INICIALIZANDO NAVEGADOR CHROME")
        self.logger.info("="*80)
        self.logger.info("   ℹ️ Usando Chrome en modo incógnito para evitar bloqueos de permisos y ubicación")
        
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        
        options = ChromeOptions()
        
        # Configuración para ejecución LOCAL
        if self.headless:
            self.logger.info("   🔇 Modo HEADLESS activado (navegador oculto)")
            options.add_argument('--headless=new')
        else:
            self.logger.info("   👀 Modo VISIBLE activado (puedes ver el navegador)")
        
        # Usar perfil temporal limpio (similar a incógnito pero más estable)
        import tempfile
        import os
        temp_profile = tempfile.mkdtemp(prefix='chrome_selenium_')
        options.add_argument(f'--user-data-dir={temp_profile}')
        self.logger.info(f"   📁 Usando perfil temporal limpio: {temp_profile}")
        self.logger.info("   🔒 Perfil temporal evita problemas de permisos y ubicación (similar a incógnito)")
        
        # Flags de estabilidad para evitar crashes
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Optimizaciones
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        
        # Configuraciones críticas para permitir descargas automáticas sin permisos
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-features=DownloadBubble,DownloadBubbleV2')
        options.add_argument('--disable-prompt-on-repost')
        
        # Evitar detección de automatización
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Verificar que el directorio de descarga esté configurado
        if self.download_dir is None:
            self.logger.warning("   ⚠️ Directorio del mes no configurado, usando directorio base temporalmente")
            download_directory = str(self.download_dir_base)
        else:
            self.logger.info(f"   📁 Directorio de descarga configurado: {self.download_dir}")
            download_directory = str(self.download_dir)
        
        # Preferencias incluyendo descargas (mismas que Edge)
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "download.default_directory": download_directory,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "safebrowsing.disable_download_protection": True,
            "profile.default_content_settings.popups": 0,
            "profile.content_settings.exceptions.automatic_downloads": {
                "*": {
                    "setting": 1
                }
            },
            "profile.default_content_setting_values.automatic_downloads": 1,
        }
        options.add_experimental_option("prefs", prefs)
        
        self.logger.info(f"   📂 Directorio de descarga para Chrome: {download_directory}")
        self.logger.info("   📦 Creando instancia de Chrome...")
        
        # Detectar si estamos en Docker
        is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'
        
        try:
            if is_docker:
                # En Docker: usar chromedriver instalado en el sistema
                from selenium.webdriver.chrome.service import Service
                service = Service(executable_path='/usr/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=options)
                self.logger.info("   ✅ Chrome iniciado correctamente (Docker con chromedriver del sistema)")
            else:
                # En local: dejar que Selenium lo encuentre automáticamente
                self.driver = webdriver.Chrome(options=options)
                self.logger.info("   ✅ Chrome iniciado correctamente")
        except Exception as e:
            self.logger.error(f"   ❌ Error al iniciar Chrome: {e}")
            self.logger.info("   💡 Asegúrate de tener Chrome instalado")
            raise
        
        # Configurar permisos de descarga explícitamente usando Chrome DevTools Protocol
        try:
            self.logger.info("   🔧 Configurando permisos de descarga...")
            self.driver.execute_cdp_cmd('Browser.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': download_directory
            })
            self.logger.info("   ✅ Permisos de descarga configurados")
        except Exception as e:
            self.logger.warning(f"   ⚠️ No se pudo configurar permisos CDP: {str(e)}")
        
        # Anti-detección
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Configurar timeouts
        self.wait = WebDriverWait(self.driver, 30)
        
        self.logger.info(f"   🌐 Navegador listo")
        self.logger.info("="*80)
    
    def _login(self):
        """
        Inicia sesión en Dropi
        
        PASO 2: Login en la plataforma Dropi
        """
        try:
            self.logger.info("="*80)
            self.logger.info("🔐 PASO 2: INICIANDO PROCESO DE LOGIN")
            self.logger.info("="*80)
            
            self.logger.info("   1) Abriendo página de login...")
            self.driver.get(self.DROPI_URL)
            self.logger.info(f"      ✅ URL cargada: {self.driver.current_url}")
            time.sleep(3)
            
            self.logger.info("   2) Buscando campo de email...")
            email_input = self.wait.until(
                EC.visibility_of_element_located((By.NAME, "email"))
            )
            self.logger.info("      ✅ Campo email encontrado")
            
            self.logger.info(f"   3) Escribiendo email: {self.DROPI_EMAIL}")
            email_input.clear()
            email_input.send_keys(self.DROPI_EMAIL)
            time.sleep(1)
            self.logger.info("      ✅ Email ingresado")
            
            self.logger.info("   4) Buscando campo de password...")
            password_input = self.driver.find_element(By.NAME, "password")
            self.logger.info("      ✅ Campo password encontrado")
            
            self.logger.info("   5) Escribiendo password...")
            password_input.clear()
            password_input.send_keys(self.DROPI_PASSWORD)
            time.sleep(1)
            self.logger.info("      ✅ Password ingresado")
            
            self.logger.info("   6) Presionando ENTER para enviar...")
            password_input.send_keys(Keys.RETURN)
            self.logger.info("      ✅ Formulario enviado")
            
            self.logger.info("   7) Esperando validación (token o redirección)...")
            self.wait.until(
                lambda d: d.execute_script("return !!localStorage.getItem('DROPI_token')") or "/dashboard" in d.current_url
            )
            self.logger.info(f"      ✅ Validación exitosa - URL actual: {self.driver.current_url}")
            
            self.logger.info("   8) Esperando 15s para carga completa del dashboard...")
            time.sleep(15)
            self.logger.info("      ✅ Espera completada")
            
            self.logger.info("="*80)
            self.logger.info("✅ LOGIN EXITOSO")
            self.logger.info("="*80)
            return True
            
        except Exception as e:
            self.logger.error("="*80)
            self.logger.error("❌ LOGIN FALLIDO")
            self.logger.error("="*80)
            self.logger.error(f"Error: {type(e).__name__}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _navigate_to_orders(self):
        """
        Navega a la sección de Mis Pedidos
        
        PASO 3: Navegar a la página de órdenes
        """
        self.logger.info("="*80)
        self.logger.info("📍 PASO 3: NAVEGANDO A MIS PEDIDOS")
        self.logger.info("="*80)
        
        try:
            # Método 1: Intentar navegación por menú
            self.logger.info("   Método 1: Intentando navegación por menú...")
            try:
                mis_pedidos_menu = self.wait.until(
                    EC.element_to_be_clickable((
                        By.XPATH, 
                        "//a[contains(@class, 'is-parent') and contains(., 'Mis Pedidos')]"
                    ))
                )
                self.logger.info("      ✅ Menú encontrado")
                mis_pedidos_menu.click()
                time.sleep(2)
                
                mis_pedidos_link = self.wait.until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//a[@href='/dashboard/orders' and contains(., 'Mis Pedidos')]"
                    ))
                )
                self.logger.info("      ✅ Submenú encontrado")
                mis_pedidos_link.click()
                time.sleep(3)
                
                self.wait.until(EC.url_contains("/dashboard/orders"))
                self.logger.info(f"      ✅ Navegación exitosa: {self.driver.current_url}")
                return True
                
            except Exception as menu_error:
                self.logger.warning(f"      ⚠️ Navegación por menú falló: {str(menu_error)}")
                self.logger.info("   Método 2: Navegando directamente por URL...")
                
                # Método 2: Navegación directa
                self.driver.get(self.ORDERS_URL)
                self.wait.until(EC.url_contains("/dashboard/orders"))
                self.logger.info(f"      ✅ Navegación directa exitosa: {self.driver.current_url}")
                time.sleep(5)  # Esperar carga de elementos
                return True
                
        except Exception as e:
            self.logger.error(f"   ❌ Error al navegar a Mis Pedidos: {str(e)}")
            return False
    
    def _calculate_dates_for_day(self, target_day):
        """
        Calcula las fechas para un reporte de un mes exacto (día X a día X del mes siguiente)
        
        Ejemplo si target_day es 19/01/2026:
        - Fecha inicio: 19/12/2025
        - Fecha fin: 19/01/2026
        - Duración: 1 mes exacto
        
        Args:
            target_day: datetime del día objetivo (ej: hoy o ayer)
        
        Returns:
            tuple: (fecha_inicio, fecha_fin)
        """
        # Obtener el día del mes
        dia_mes = target_day.day
        
        # Calcular fecha de inicio (mismo día del mes anterior)
        if target_day.month == 1:
            fecha_inicio = datetime(target_day.year - 1, 12, dia_mes)
        else:
            # Manejar casos donde el día no existe en el mes anterior (ej: 31 de marzo -> 28/29 de febrero)
            try:
                fecha_inicio = datetime(target_day.year, target_day.month - 1, dia_mes)
            except ValueError:
                # Si el día no existe en el mes anterior, usar el último día de ese mes
                import calendar
                ultimo_dia = calendar.monthrange(target_day.year, target_day.month - 1)[1]
                fecha_inicio = datetime(target_day.year, target_day.month - 1, ultimo_dia)
        
        # Fecha fin es el mismo día del mes actual
        fecha_fin = datetime(target_day.year, target_day.month, dia_mes)
        
        return fecha_inicio, fecha_fin
    
    
    def _is_download_dir_empty(self):
        """
        Verifica si el directorio base de descargas está vacío (sin archivos .xlsx en toda la carpeta)
        
        Busca recursivamente en toda la carpeta downloads/ para verificar si hay algún archivo .xlsx
        
        Returns:
            bool: True si está vacío, False si tiene archivos
        """
        if not self.download_dir_base.exists():
            self.logger.info("   📂 Carpeta base no existe, se considera vacía")
            return True
        
        # Buscar archivos .xlsx recursivamente en toda la carpeta downloads/
        xlsx_files = list(self.download_dir_base.rglob("*.xlsx"))
        
        cantidad_archivos = len(xlsx_files)
        
        if cantidad_archivos == 0:
            self.logger.info("   📂 Carpeta base está vacía (0 archivos .xlsx encontrados)")
            return True
        else:
            self.logger.info(f"   📂 Carpeta base tiene {cantidad_archivos} archivo(s) .xlsx")
            return False
    
    def _open_filters(self):
        """
        Abre el panel de filtros en la página de órdenes
        
        PASO 5.1: Abrir panel de filtros
        """
        self.logger.info("   📋 Abriendo panel de filtros...")
        
        try:
            # Buscar botón de filtros
            filter_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'btn-success') and contains(@title, 'Mostrar Filtros')]"
                ))
            )
            self.logger.info("      ✅ Botón de filtros encontrado")
            
            filter_button.click()
            time.sleep(2)
            self.logger.info("      ✅ Panel de filtros abierto")
            return True
            
        except Exception as e:
            self.logger.error(f"      ❌ Error al abrir filtros: {str(e)}")
            return False
    
    def _set_date_range(self, fecha_inicio, fecha_fin):
        """
        Configura el rango de fechas en el filtro
        
        PASO 5.2: Configurar rango de fechas
        
        Args:
            fecha_inicio: Fecha de inicio (datetime)
            fecha_fin: Fecha de fin (datetime)
        """
        self.logger.info(f"   📅 Configurando rango de fechas...")
        self.logger.info(f"      Desde: {fecha_inicio.strftime('%d/%m/%Y')}")
        self.logger.info(f"      Hasta: {fecha_fin.strftime('%d/%m/%Y')}")
        
        try:
            # Buscar input de fecha "Desde"
            self.logger.info("      1) Buscando campo 'Desde'...")
            desde_input = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//input[@id='date-range' or @placeholder='Desde']"
                ))
            )
            self.logger.info("         ✅ Campo 'Desde' encontrado")
            
            desde_input.click()
            time.sleep(1)
            
            # Navegar al mes correcto en el calendario
            self.logger.info("      2) Navegando al mes correcto en calendario...")
            self._navigate_calendar_to_date(fecha_inicio)
            
            # Seleccionar día de inicio
            self.logger.info(f"      3) Seleccionando día de inicio: {fecha_inicio.day}")
            self._select_day_in_calendar(fecha_inicio.day)
            
            # Esperar más tiempo en modo headless para que el calendario se cierre
            wait_time = 3 if self.headless else 1
            self.logger.info(f"         ⏳ Esperando {wait_time}s para que el calendario se cierre...")
            time.sleep(wait_time)
            
            # El campo "Hasta" viene predeterminado con la fecha actual, no necesitamos configurarlo
            self.logger.info("      4) Campo 'Hasta' viene predeterminado con fecha actual, omitiendo configuración...")
            
            # Cerrar calendario con botón OK (esto cierra el modal automáticamente)
            self.logger.info("      7) Cerrando calendario con botón OK...")
            ok_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'btn-success') and contains(text(), 'Ok')]"
                ))
            )
            ok_button.click()
            time.sleep(2)
            self.logger.info("         ✅ Rango de fechas configurado")
            
            return True
            
        except Exception as e:
            self.logger.error(f"      ❌ Error al configurar fechas: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _navigate_calendar_to_date(self, target_date):
        """
        Navega el calendario hasta el mes y año de la fecha objetivo
        
        Args:
            target_date: Fecha objetivo (datetime)
        """
        try:
            # Esperar a que el calendario esté visible
            self.wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//button[contains(@class, 'p-datepicker-month')]"
                ))
            )
            time.sleep(0.5)  # Pequeña espera adicional para estabilidad
            
            # Obtener mes y año objetivo
            target_month = target_date.month - 1  # Los meses en JavaScript son 0-indexed
            target_year = target_date.year
            
            # Obtener mes y año actual del calendario
            current_month_element = self.wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//button[contains(@class, 'p-datepicker-month')]"
                ))
            )
            current_month_text = current_month_element.text.strip()
            
            current_year_element = self.wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//button[contains(@class, 'p-datepicker-year')]"
                ))
            )
            current_year_text = current_year_element.text.strip()
            
            current_year = int(current_year_text)
            
            # Mapear nombre del mes a número
            meses = {
                'january': 0, 'february': 1, 'march': 2, 'april': 3,
                'may': 4, 'june': 5, 'july': 6, 'august': 7,
                'september': 8, 'october': 9, 'november': 10, 'december': 11
            }
            current_month = meses.get(current_month_text.lower(), 0)
            
            # Calcular diferencia en meses
            months_diff = (target_year - current_year) * 12 + (target_month - current_month)
            
            self.logger.info(f"         📍 Calendario actual: {current_month_text} {current_year}")
            self.logger.info(f"         🎯 Objetivo: {target_date.strftime('%B %Y')} (diferencia: {months_diff} meses)")
            
            # Navegar hacia atrás o adelante
            if months_diff < 0:
                # Ir hacia atrás
                self.logger.info(f"         ⬅️ Navegando {abs(months_diff)} meses hacia atrás...")
                for i in range(abs(months_diff)):
                    prev_button = self.wait.until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            "//button[contains(@class, 'p-datepicker-prev')]"
                        ))
                    )
                    prev_button.click()
                    time.sleep(0.7)  # Esperar un poco más para que el calendario se actualice
            elif months_diff > 0:
                # Ir hacia adelante
                self.logger.info(f"         ➡️ Navegando {months_diff} meses hacia adelante...")
                for i in range(months_diff):
                    next_button = self.wait.until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            "//button[contains(@class, 'p-datepicker-next')]"
                        ))
                    )
                    next_button.click()
                    time.sleep(0.7)  # Esperar un poco más para que el calendario se actualice
            else:
                self.logger.info("         ✅ Ya estamos en el mes correcto")
            
            self.logger.info(f"         ✅ Calendario navegado a {target_date.strftime('%B %Y')}")
            
        except Exception as e:
            self.logger.warning(f"         ⚠️ Error al navegar calendario: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
    
    def _select_day_in_calendar(self, day):
        """
        Selecciona un día específico en el calendario
        
        Args:
            day: Día a seleccionar (1-31)
        """
        try:
            day_element = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    f"//span[contains(@class, 'p-element') and @data-date and contains(text(), '{day}')]"
                ))
            )
            day_element.click()
            time.sleep(0.5)
            
        except Exception as e:
            self.logger.warning(f"         ⚠️ Error al seleccionar día {day}: {str(e)}")
            # Intentar método alternativo
            try:
                day_element = self.driver.find_element(
                    By.XPATH,
                    f"//td[contains(@aria-label, '{day}')]//span"
                )
                day_element.click()
                time.sleep(0.5)
            except:
                pass
    
    def _download_report(self):
        """
        Descarga el reporte "Órdenes con Productos (Un producto por fila)"
        
        PASO 5.3: Descargar reporte desde el menú de acciones
        """
        self.logger.info("   📥 Descargando reporte...")
        
        try:
            # 1. BUSCAR DROPDOWN DE ACCIONES
            self.logger.info("      1) Buscando dropdown (Actions/Acciones)...")
            
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            import time
            
            # Aumentar timeout en modo headless (Docker puede tardar más)
            dropdown_timeout = 90 if self.headless else 30
            dropdown_wait = WebDriverWait(self.driver, dropdown_timeout)
            
            acciones_dropdown = None
            
            # Intentar encontrar el elemento por CSS selector simple primero (más robusto e independiente del idioma)
            try:
                self.logger.info("      1) Buscando dropdown con selector CSS simple...")
                acciones_dropdown = dropdown_wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.dropdown-toggle.btn"))
                )
                self.logger.info("         ✅ Dropdown encontrado por CSS")
            except:
                self.logger.warning("         ⚠️ CSS falló, intentando XPath multilingüe...")
                # XPath que busca Acciones O Actions
                xpath_dropdown = "//a[contains(@class, 'dropdown-toggle') and (contains(normalize-space(.), 'Acciones') or contains(normalize-space(.), 'Actions'))]"
                acciones_dropdown = dropdown_wait.until(
                    EC.presence_of_element_located((By.XPATH, xpath_dropdown))
                )
                self.logger.info("         ✅ Dropdown encontrado por XPath")
            
            # Scroll y Click (Intentar JS si falla normal)
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", acciones_dropdown)
                time.sleep(1)
                
                try:
                    acciones_dropdown.click()
                    self.logger.info("         ✅ Clic normal realizado")
                except:
                    self.logger.warning("         ⚠️ Clic normal falló, intentando JS click...")
                    self.driver.execute_script("arguments[0].click();", acciones_dropdown)
                    self.logger.info("         ✅ Clic JS realizado")
            except Exception as e:
                self.logger.error(f"         ❌ Error al interactuar con dropdown: {e}")
                raise e
            
            time.sleep(2)
            
            # 2. BUSCAR OPCIÓN DE REPORTE (Multilingüe: Español / Inglés)
            self.logger.info("      2) Buscando opción 'Órdenes con Productos' (Multilingüe)...")
            
            # Buscar por clase y texto parcial en inglés o español
            xpath_option = "//button[contains(@class, 'dropdown-item') and (contains(text(), 'Órdenes con Productos') or contains(text(), 'Orders with Products'))]"
            
            report_option = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, xpath_option))
            )
            self.logger.info("         ✅ Opción encontrada")
            
            report_option.click()
            time.sleep(3)
            
            # 3. ESPERAR MODAL DE CONFIRMACIÓN
            self.logger.info("      3) Esperando modal de confirmación...")
            # Busca botón swal2-confirm independientemente del texto (más robusto)
            modal_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "button.swal2-confirm"
                ))
            )
            self.logger.info("         ✅ Modal de confirmación apareció")
            
            # Esperar 10 segundos antes de hacer click (Docker es más lento)
            self.logger.info("      4) Esperando 10 segundos antes de continuar...")
            time.sleep(10)
            
            # Click en "Ver reportes" / "View reports"
            self.logger.info("      5) Haciendo click en botón de modal...")
            modal_button.click()
            time.sleep(3)
            
            # Verificar que redirigió a la página de reportes
            self.wait.until(EC.url_contains("/dashboard/reports/downloads"))
            self.logger.info(f"         ✅ Redirigido a: {self.driver.current_url}")
            
            return True
        
        except Exception as e:
        except Exception as e:
            self.logger.error(f"      ❌ Error al descargar reporte: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False



    def _wait_for_report_and_download(self, max_wait_time=300):
        """
        Espera a que el reporte esté listo y lo descarga
        
        PASO 5.4: Esperar reporte y descargarlo
        
        Args:
            max_wait_time: Tiempo máximo de espera en segundos (default: 5 minutos)
        
        Returns:
            str: Ruta del archivo descargado o None si falló
        """
        self.logger.info("   ⏳ Esperando a que el reporte esté listo...")
        
        start_time = time.time()
        check_interval = 5  # Verificar cada 5 segundos
        refresh_interval = 20 # Refrescar página cada 20 segundos si no aparece
        last_refresh_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # Refrescar página si ha pasado el tiempo
            if time.time() - last_refresh_time > refresh_interval:
                self.logger.info("      🔄 Refrescando página para actualizar lista...")
                self.driver.refresh()
                time.sleep(5) # Esperar a que cargue
                last_refresh_time = time.time()
            
            try:
                # Buscar la primera fila de la tabla (reporte más reciente)
                self.logger.info(f"      Verificando estado del reporte... ({int(time.time() - start_time)}s)")
                
                # Buscar filas de la tabla
                try:
                    rows = self.driver.find_elements(
                        By.XPATH,
                        "//tbody//tr[contains(@class, 'table-row')]"
                    )
                except:
                    rows = []
                
                if rows:
                    # Obtener la primera fila (más reciente)
                    first_row = rows[0]
                    
                    # Verificar estado - buscar "Listo", "Completed", "Done" o icono de check
                    try:
                        # XPath robusto para encontrar el tag de estado
                        estado_xpath = ".//app-dropi-tag//span" 
                        estado_tags = first_row.find_elements(By.XPATH, estado_xpath)
                        
                        estado_texto = ""
                        is_ready = False
                        
                        for tag in estado_tags:
                            txt = tag.text.strip().lower()
                            estado_texto += f"{txt} "
                            if txt in ['listo', 'completed', 'success', 'hecho', 'ready']:
                                is_ready = True
                                break
                        
                        if is_ready:
                            self.logger.info(f"         ✅ Reporte está listo! (Estado: {estado_texto.strip()})")
                            
                            # Intentar obtener nombre de archivo
                            try:
                                filename_element = first_row.find_element(By.XPATH, ".//span[contains(text(), '.xlsx')]")
                                expected_filename = filename_element.text.strip()
                                self.logger.info(f"         📄 Archivo esperado: {expected_filename}")
                            except:
                                expected_filename = None
                            
                            # Buscar botón de descarga
                            download_button = None
                            try:
                                # Busca cualquier elemento que parezca un botón de descarga en la última columna
                                download_button = first_row.find_element(
                                    By.CSS_SELECTOR, 
                                    "app-icon.action-icon"
                                )
                                self.logger.info("         ✅ Botón de descarga encontrado")
                            except: pass
                            
                            if download_button:
                                # Descargar!
                                download_button.click()
                                self.logger.info("         ⬇️ Click en descargar realizado")
                                
                                # Calcular ruta esperada
                                expected_path = self._find_downloaded_file(expected_filename)
                                if expected_path:
                                    return expected_path
                            else:
                                self.logger.warning("         ⚠️ Reporte listo pero sin botón de descarga. Refrescando...")
                                self.driver.refresh()
                                time.sleep(5)
                                last_refresh_time = time.time()
                                continue
                        else:
                            self.logger.info(f"         ⏳ Reporte aún no está listo (Estado: {estado_texto.strip()}), esperando...")
                            
                    except Exception as e:
                        self.logger.warning(f"         ⚠️ Error verificando fila: {e}")
                else:
                    self.logger.info("         ℹ️ No se encontraron reportes en la lista")
                
            except Exception as e:
                self.logger.warning(f"      ⚠️ Error en verificación: {str(e)}")
            
            time.sleep(check_interval)
            
        self.logger.error("   ❌ Tiempo de espera agotado. El reporte no se generó a tiempo.")
        return None


    
    def _find_downloaded_file(self, expected_filename=None):
        """
        Busca el archivo descargado en el directorio de descargas
        
        Args:
            expected_filename: Nombre esperado del archivo (opcional)
        
        Returns:
            str: Ruta completa del archivo o None si no se encuentra
        """
        # Buscar archivos .xlsx en el directorio de descargas
        pattern = str(self.download_dir / "*.xlsx")
        files = glob.glob(pattern)
        
        # Ordenar por fecha de modificación (más reciente primero)
        files.sort(key=os.path.getmtime, reverse=True)
        
        if files:
            # Si se especificó un nombre esperado, buscar coincidencia parcial
            if expected_filename:
                for file in files:
                    if expected_filename in os.path.basename(file):
                        file_time = os.path.getmtime(file)
                        if time.time() - file_time < 120:
                            return file
            
            # Si no se encontró coincidencia o no se especificó nombre, tomar el más reciente
            latest_file = files[0]
            # Verificar que sea reciente (descargado en los últimos 2 minutos)
            file_time = os.path.getmtime(latest_file)
            if time.time() - file_time < 120:
                return latest_file
        
        return None
    
    def _rename_downloaded_file(self, downloaded_file, fecha_inicio, fecha_fin):
        """
        Renombra el archivo descargado con un nombre descriptivo que incluye la fecha de generación
        
        IMPORTANTE: Este método SIEMPRE genera nombres con el formato estandarizado:
        Formato: reporte_YYYYMMDD.xlsx
        Ejemplo: reporte_20260120.xlsx (generado el 20/01/2026)
        
        El formato es estricto y no se permiten variaciones (sin timestamps ni sufijos adicionales).
        Si un archivo con el mismo nombre ya existe, será reemplazado para mantener el formato.
        La fecha usada es la fecha de fin (fecha_fin), que es cuando se genera el reporte.
        
        Args:
            downloaded_file: Ruta del archivo descargado
            fecha_inicio: Fecha de inicio (datetime) - no se usa en el nombre
            fecha_fin: Fecha de fin (datetime) - esta es la fecha de generación del reporte
        
        Returns:
            str: Ruta del archivo renombrado con formato estandarizado
            
        Raises:
            Exception: Si no se puede aplicar el formato estandarizado al archivo
        """
        try:
            # Crear nombre descriptivo con solo la fecha de generación (fecha_fin)
            fecha_generacion_str = fecha_fin.strftime('%Y%m%d')
            nuevo_nombre = f"reporte_{fecha_generacion_str}.xlsx"
            
            # Ruta completa del nuevo archivo
            nuevo_path = self.download_dir / nuevo_nombre
            
            # Verificar si el archivo ya existe (por si acaso)
            # Si existe, lo reemplazamos para mantener el formato estandarizado
            if nuevo_path.exists():
                self.logger.info(f"   ⚠️ Archivo ya existe, será reemplazado: {nuevo_nombre}")
                # Eliminar archivo existente para mantener formato estandarizado
                try:
                    os.remove(nuevo_path)
                    self.logger.info(f"   ✅ Archivo anterior eliminado para mantener formato estandarizado")
                except Exception as e:
                    self.logger.warning(f"   ⚠️ No se pudo eliminar archivo existente: {str(e)}")
            
            # Renombrar archivo - SIEMPRE usar formato estandarizado
            if os.path.exists(downloaded_file):
                try:
                    os.rename(downloaded_file, nuevo_path)
                    self.logger.info(f"   📝 Archivo renombrado: {nuevo_nombre}")
                    self.logger.info(f"      Fecha de generación: {fecha_fin.strftime('%d/%m/%Y')}")
                    self.logger.info(f"      ✅ Formato estandarizado aplicado: reporte_YYYYMMDD.xlsx")
                    return str(nuevo_path)
                except Exception as rename_error:
                    self.logger.error(f"   ❌ Error al renombrar archivo: {str(rename_error)}")
                    # Intentar copiar y luego eliminar el original
                    try:
                        import shutil
                        shutil.copy2(downloaded_file, nuevo_path)
                        os.remove(downloaded_file)
                        self.logger.info(f"   ✅ Archivo renombrado usando método alternativo: {nuevo_nombre}")
                        return str(nuevo_path)
                    except Exception as copy_error:
                        self.logger.error(f"   ❌ Error crítico: No se pudo renombrar el archivo: {str(copy_error)}")
                        raise Exception(f"No se pudo aplicar formato estandarizado al archivo. Error: {str(copy_error)}")
            else:
                self.logger.error(f"   ❌ Archivo original no encontrado: {downloaded_file}")
                raise FileNotFoundError(f"El archivo descargado no existe: {downloaded_file}")
                
        except Exception as e:
            self.logger.error(f"   ❌ Error crítico al renombrar archivo: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            # No devolver el archivo sin renombrar - lanzar excepción para que se maneje arriba
            raise Exception(f"Error al aplicar formato estandarizado al archivo. El archivo debe tener el formato 'reporte_YYYYMMDD.xlsx'. Error: {str(e)}")
    
    def _download_single_report(self, fecha_inicio, fecha_fin):
        """
        Descarga un reporte completo con las fechas especificadas y lo renombra
        
        Este método siempre navega desde cero a Mis Pedidos para asegurar un estado limpio.
        
        Args:
            fecha_inicio: Fecha de inicio (datetime)
            fecha_fin: Fecha de fin (datetime)
        
        Returns:
            str: Ruta del archivo descargado y renombrado o None si falló
        """
        reporte_nombre = f"Reporte desde {fecha_inicio.strftime('%d/%m/%Y')} hasta {fecha_fin.strftime('%d/%m/%Y')}"
        
        self.logger.info("="*80)
        self.logger.info(f"📊 DESCARGANDO REPORTE: {reporte_nombre}")
        self.logger.info("="*80)
        
        # Paso 1: Navegar a órdenes (siempre desde cero para estado limpio)
        if not self._navigate_to_orders():
            self.logger.error("   ❌ No se pudo navegar a órdenes")
            return None
        
        # Paso 2: Abrir filtros
        if not self._open_filters():
            self.logger.error("   ❌ No se pudo abrir filtros")
            return None
        
        # Paso 3: Configurar fechas
        if not self._set_date_range(fecha_inicio, fecha_fin):
            self.logger.error("   ❌ No se pudo configurar fechas")
            return None
        
        # Paso 4: Descargar reporte
        if not self._download_report():
            self.logger.error("   ❌ No se pudo iniciar descarga del reporte")
            return None
        
        # Paso 5: Esperar y descargar archivo
        downloaded_file = self._wait_for_report_and_download()
        
        if downloaded_file:
            # Paso 6: Renombrar archivo con nombre descriptivo
            renamed_file = self._rename_downloaded_file(downloaded_file, fecha_inicio, fecha_fin)
            
            self.logger.info("="*80)
            self.logger.info(f"✅ REPORTE DESCARGADO EXITOSAMENTE: {reporte_nombre}")
            self.logger.info(f"   📁 Archivo: {renamed_file}")
            self.logger.info("="*80)
            return renamed_file
        else:
            self.logger.error("="*80)
            self.logger.error(f"❌ ERROR AL DESCARGAR REPORTE: {reporte_nombre}")
            self.logger.error("="*80)
            return None
    
    
    def run(self):
        """
        Ejecuta el proceso de descarga de reportes
        
        Lógica:
        - Descarga reportes de un mes exacto (día X a día X del mes siguiente)
        - Si la carpeta está vacía: descarga 2 reportes (día anterior y día actual)
        - Si la carpeta tiene archivos: descarga solo 1 reporte (día actual)
        - Los archivos se nombran: reporte_YYYYMMDD.xlsx (solo la fecha de generación)
        """
        self.logger.info("="*80)
        self.logger.info("🤖 INICIANDO BOT DESCARGADOR DE REPORTES")
        self.logger.info("="*80)
        self.logger.info(f"   📁 Directorio base: {self.download_dir_base}")
        self.logger.info("="*80)
        
        try:
            # Paso 1: Verificar estado de la carpeta base
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("📂 PASO 1: VERIFICANDO ESTADO DE LA CARPETA BASE")
            self.logger.info("="*80)
            carpeta_vacia = self._is_download_dir_empty()
            
            if carpeta_vacia:
                self.logger.info("   ✅ RESULTADO: Carpeta vacía")
                self.logger.info("   📋 ACCIÓN: Se descargarán 2 reportes (día anterior y día actual)")
            else:
                self.logger.info("   ✅ RESULTADO: Carpeta con archivos existentes")
                self.logger.info("   📋 ACCIÓN: Se descargará 1 reporte (día actual)")
            self.logger.info("="*80)
            
            # Paso 2: Obtener fecha actual
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("📅 PASO 2: CONFIGURANDO FECHA ACTUAL")
            self.logger.info("="*80)
            hoy = datetime.now()
            self.logger.info(f"   📆 Fecha actual: {hoy.strftime('%d/%m/%Y')}")
            self.logger.info("="*80)
            
            # Paso 3: Inicializar navegador (después de configurar carpeta del mes)
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("🚀 PASO 3: INICIALIZANDO NAVEGADOR")
            self.logger.info("="*80)
            self._init_driver()
            
            # Paso 4: Login
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("🔐 PASO 4: INICIANDO SESIÓN")
            self.logger.info("="*80)
            if not self._login():
                self.logger.error("❌ Login fallido. Abortando.")
                return False
            
            # Paso 5: Calcular fechas
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("📅 PASO 5: CALCULANDO FECHAS PARA LOS REPORTES")
            self.logger.info("="*80)
            ayer = hoy - timedelta(days=1)
            
            # Calcular fechas para el reporte del día actual
            fecha_inicio_hoy, fecha_fin_hoy = self._calculate_dates_for_day(hoy)
            
            self.logger.info(f"   📊 Reporte HOY ({hoy.strftime('%d/%m/%Y')}):")
            self.logger.info(f"      Desde: {fecha_inicio_hoy.strftime('%d/%m/%Y')}")
            self.logger.info(f"      Hasta: {fecha_fin_hoy.strftime('%d/%m/%Y')}")
            
            reportes_descargados = []
            
            # Paso 6: Descargar reportes según el estado de la carpeta
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("📥 PASO 6: DESCARGANDO REPORTES")
            self.logger.info("="*80)
            
            if carpeta_vacia:
                # Descargar reporte del día anterior
                fecha_inicio_ayer, fecha_fin_ayer = self._calculate_dates_for_day(ayer)
                
                self.logger.info(f"   📊 Reporte AYER ({ayer.strftime('%d/%m/%Y')}):")
                self.logger.info(f"      Desde: {fecha_inicio_ayer.strftime('%d/%m/%Y')}")
                self.logger.info(f"      Hasta: {fecha_fin_ayer.strftime('%d/%m/%Y')}")
                self.logger.info("="*80)
                
                self.logger.info("")
                self.logger.info("   📥 Descargando reporte del día ANTERIOR...")
                reporte_ayer = self._download_single_report(fecha_inicio_ayer, fecha_fin_ayer)
                
                if not reporte_ayer:
                    self.logger.error("   ❌ No se pudo descargar el reporte del día anterior. Abortando.")
                    return False
                
                self.logger.info("   ✅ Reporte del día anterior descargado exitosamente")
                reportes_descargados.append({
                    'tipo': 'día anterior',
                    'path': reporte_ayer,
                    'fecha_inicio': fecha_inicio_ayer,
                    'fecha_fin': fecha_fin_ayer
                })
                self.stats['reporte_anterior_descargado'] = True
                
                # GUARDAR EN BASE DE DATOS
                if self.user:
                    self._process_excel_to_db(reporte_ayer, fecha_fin_ayer)
                
                # Pequeña pausa entre descargas
                self.logger.info("   ⏳ Esperando 5 segundos antes de la siguiente descarga...")
                time.sleep(5)
            
            # Descargar reporte del día actual
            self.logger.info("")
            self.logger.info("   📥 Descargando reporte del día ACTUAL...")
            reporte_hoy = self._download_single_report(fecha_inicio_hoy, fecha_fin_hoy)
            
            if not reporte_hoy:
                self.logger.error("   ❌ No se pudo descargar el reporte del día actual. Abortando.")
                return False
            
            self.logger.info("   ✅ Reporte del día actual descargado exitosamente")
            reportes_descargados.append({
                'tipo': 'día actual',
                'path': reporte_hoy,
                'fecha_inicio': fecha_inicio_hoy,
                'fecha_fin': fecha_fin_hoy
            })
            self.stats['reporte_actual_descargado'] = True
            
            # GUARDAR EN BASE DE DATOS
            if self.user:
                self._process_excel_to_db(reporte_hoy, fecha_fin_hoy)
            
            self.logger.info("="*80)
            
            # Paso 7: Mostrar resumen final
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("✅ PASO 7: RESUMEN FINAL")
            self.logger.info("="*80)
            self.logger.info("   🎉 PROCESO DE DESCARGA COMPLETADO EXITOSAMENTE")
            self.logger.info("")
            self.logger.info(f"   📁 Ubicación: {self.download_dir}")
            self.logger.info("")
            self.logger.info(f"   📊 Total de reportes descargados: {len(reportes_descargados)}")
            self.logger.info("")
            
            for idx, reporte in enumerate(reportes_descargados, 1):
                self.logger.info(f"   {idx}. Reporte {reporte['tipo'].upper()}:")
                self.logger.info(f"      📄 Archivo: {Path(reporte['path']).name}")
                self.logger.info(f"      📅 Período: {reporte['fecha_inicio'].strftime('%d/%m/%Y')} - {reporte['fecha_fin'].strftime('%d/%m/%Y')}")
                self.logger.info(f"      📁 Ruta completa: {reporte['path']}")
                self.logger.info("")
            
            if len(reportes_descargados) == 2:
                self.logger.info("   💡 Próximo paso: Ejecutar el comparador de reportes:")
                self.logger.info(f"      python manage.py reportcomparer --base \"{reportes_descargados[0]['path']}\" --actual \"{reportes_descargados[1]['path']}\"")
            else:
                self.logger.info("   💡 Reporte del día actual descargado. El comparador buscará automáticamente el reporte base.")
            self.logger.info("="*80)
            return True
            
        except Exception as e:
            self.logger.error("="*80)
            self.logger.error("❌ ERROR CRÍTICO EN EL PROCESO")
            self.logger.error("="*80)
            self.logger.error(f"Error: {type(e).__name__}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
            
        finally:
            # Cerrar navegador
            if self.driver:
                self.logger.info("")
                self.logger.info("🔒 Cerrando navegador...")
                self.driver.quit()
                self.logger.info("   ✅ Navegador cerrado")

    def _process_excel_to_db(self, file_path, report_date):
        """
        Lee el archivo Excel descargado y guarda los datos en la base de datos (RawOrderSnapshot)
        Vincula el reporte al usuario actual.
        """
        self.logger.info("="*80)
        self.logger.info(f"💾 GUARDANDO EN BASE DE DATOS: {Path(file_path).name}")
        self.logger.info("="*80)
        
        if not self.user:
            self.logger.warning("   ⚠️ No hay usuario asignado al bot, saltando guardado en DB")
            return

        try:
            # 1. Verificar si ya existe un batch para esta fecha/usuario/cuenta
            # IMPORTANTE: Usamos la fecha del reporte (report_date) para identificar el batch
            
            # Resetear fecha a medianoche para búsqueda precisa y hacerlo timezone aware
            report_date_aware = timezone.make_aware(report_date.replace(hour=12, minute=0, second=0, microsecond=0))
            
            existing_batch = ReportBatch.objects.filter(
                user=self.user,
                created_at__year=report_date.year,
                created_at__month=report_date.month,
                created_at__day=report_date.day,
                account_email=self.DROPI_EMAIL
            ).first()
            
            if existing_batch:
                self.logger.info(f"   ⚠️ Ya existe un lote para esta fecha ({report_date.strftime('%Y-%m-%d')}). Reemplazando...")
                existing_batch.delete()
                self.logger.info("      ✅ Lote anterior eliminado")
            
            # 2. Crear nuevo Batch
            batch = ReportBatch.objects.create(
                user=self.user,
                account_email=self.DROPI_EMAIL,
                status="PROCESSING",
                total_records=0
            ) 
            # Force update created_at to match report date
            ReportBatch.objects.filter(id=batch.id).update(created_at=report_date_aware)
            batch.refresh_from_db()

            self.logger.info(f"   ✅ Lote creado: ID {batch.id}")
            
            # 3. Leer Excel
            df = pd.read_excel(file_path)
            total_rows = len(df)
            self.logger.info(f"   📊 Filas encontradas: {total_rows}")
            
            snapshots = []
            
            for idx, row in df.iterrows():
                try:
                    dropi_id = str(row.get('ID', '')).strip()
                    # Skip empty or weird IDs
                    if not dropi_id or dropi_id.lower() == 'nan': continue
                    
                    # Parse dates safely
                    fecha_val = row.get('FECHA')
                    order_date_obj = None
                    if pd.notna(fecha_val):
                        if isinstance(fecha_val, str):
                            try:
                                order_date_obj = datetime.strptime(fecha_val, '%d-%m-%Y').date()
                            except: pass
                        else:
                            try:
                                order_date_obj = fecha_val.date()
                            except: pass

                    snapshot = RawOrderSnapshot(
                        batch=batch,
                        dropi_order_id=dropi_id,
                        shopify_order_id=str(row.get('NUMERO DE PEDIDO DE TIENDA', '')).replace('.0', '') if pd.notna(row.get('NUMERO DE PEDIDO DE TIENDA')) else None,
                        guide_number=str(row.get('NÚMERO GUIA', '')) if pd.notna(row.get('NÚMERO GUIA')) else None,
                        current_status=str(row.get('ESTATUS', '')).strip(),
                        carrier=str(row.get('TRANSPORTADORA', '')) if pd.notna(row.get('TRANSPORTADORA')) else None,
                        customer_name=str(row.get('NOMBRE CLIENTE', '')) if pd.notna(row.get('NOMBRE CLIENTE')) else None,
                        customer_phone=str(row.get('TELÉFONO', '')) if pd.notna(row.get('TELÉFONO')) else None,
                        address=str(row.get('DIRECCION', '')) if pd.notna(row.get('DIRECCION')) else None,
                        city=str(row.get('CIUDAD DESTINO', '')) if pd.notna(row.get('CIUDAD DESTINO')) else None,
                        department=str(row.get('DEPARTAMENTO DESTINO', '')) if pd.notna(row.get('DEPARTAMENTO DESTINO')) else None,
                        product_name=str(row.get('PRODUCTO', '')) if pd.notna(row.get('PRODUCTO')) else None,
                        quantity=int(row.get('CANTIDAD', 1)) if pd.notna(row.get('CANTIDAD')) else 1,
                        total_amount=float(row.get('TOTAL DE LA ORDEN', 0)) if pd.notna(row.get('TOTAL DE LA ORDEN')) else 0.0,
                        order_date=order_date_obj
                    )
                    snapshots.append(snapshot)
                    
                    if len(snapshots) >= 2000:
                        RawOrderSnapshot.objects.bulk_create(snapshots)
                        snapshots = []
                        self.logger.info(f"      📥 Insertados 2000 registros...")
                        
                except Exception as row_error:
                    continue # Skip problematic rows silently or log debug
            
            if snapshots:
                RawOrderSnapshot.objects.bulk_create(snapshots)
                self.logger.info(f"      📥 Insertados restantes {len(snapshots)} registros")
            
            batch.total_records = total_rows
            batch.status = "SUCCESS"
            batch.save()
            
            self.logger.info(f"   ✅ Guardado en DB completado para {report_date.strftime('%d/%m/%Y')}")
            
            # Eliminar archivo Excel después de guardarlo en DB
            try:
                os.remove(file_path)
                self.logger.info(f"   🗑️ Archivo Excel eliminado: {Path(file_path).name}")
            except Exception as del_err:
                self.logger.warning(f"   ⚠️ No se pudo eliminar el archivo Excel: {del_err}")
            
        except Exception as e:
            self.logger.error(f"   ❌ Error al guardar en DB: {e}")
            # No fallar el bot entero si falla la DB, solo loguear



class Command(BaseCommand):
    """Comando de Django para ejecutar el bot descargador de reportes"""
    
    help = 'Descarga reportes de Dropi (base y actual) con nombres descriptivos que incluyen las fechas'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--headless',
            action='store_true',
            help='Ejecutar el navegador en modo headless (sin interfaz gráfica)'
        )
        
        parser.add_argument(
            '--download-dir',
            type=str,
            help='Directorio donde se guardarán los archivos descargados (default: results/downloads)'
        )
        
        parser.add_argument(
            '--use-chrome-fallback',
            action='store_true',
            help='Usar Chrome en lugar de Edge (útil si Edge no funciona o no está disponible)'
        )
        
        parser.add_argument(
            '--user-id',
            type=int,
            help='ID del usuario para obtener credenciales de la base de datos'
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
            help='Email especifico para Dropi'
        )
        
        parser.add_argument(
            '--password',
            type=str,
            help='Password especifico para Dropi'
        )
    
    def handle(self, *args, **options):
        configure_utf8_stdio()
        headless = options.get('headless', False)
        download_dir = options.get('download_dir', None)
        use_chrome_fallback = options.get('use_chrome_fallback', False)
        user_id = options.get('user_id')
        dropi_label = options.get('dropi_label', 'reporter')
        email = options.get('email')
        password = options.get('password')

        if user_id:
            try:
                # Usar credenciales Dropi directamente del User (ahora están en la tabla users)
                from core.models import User
                user = User.objects.filter(id=user_id).first()
                if user and user.dropi_email and user.dropi_password:
                    email = user.dropi_email
                    password = user.get_dropi_password_plain()
                    self.stdout.write(self.style.SUCCESS(f'[INFO] Usando credenciales Dropi del usuario (user_id={user_id}, email={user.dropi_email})'))
                else:
                    self.stdout.write(self.style.WARNING(f'[WARN] No se encontraron credenciales Dropi para user_id={user_id}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[ERROR] Falló al obtener perfil de usuario: {e}'))

        # Crear y ejecutar el bot
        bot = DropiDownloaderReporterBot(
            headless=headless, 
            download_dir=download_dir,
            use_chrome_fallback=use_chrome_fallback,
            email=email,
            password=password,
            user=user if 'user' in locals() else None
        )
        
        try:
            success = bot.run()
            if success:
                # Usar texto simple para evitar problemas de encoding en Windows
                self.stdout.write(
                    self.style.SUCCESS('[OK] Bot ejecutado exitosamente')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('[ERROR] Bot ejecutado con errores')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error al ejecutar el bot: {str(e)}')
            )
            raise
