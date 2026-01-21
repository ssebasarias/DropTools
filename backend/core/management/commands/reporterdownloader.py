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

from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
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
    
    def __init__(self, headless=False, download_dir=None, use_chrome_fallback=False, email=None, password=None):
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
        
        # El directorio específico del mes se creará dinámicamente
        self.download_dir = None
        
        # Las preferencias de descarga se configurarán después de crear la carpeta del mes
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
        if self.use_chrome_fallback:
            return self._init_chrome_driver()
        else:
            return self._init_edge_driver()
    
    def _init_edge_driver(self):
        """Inicializa Edge WebDriver"""
        self.logger.info("="*80)
        self.logger.info("🚀 PASO 1: INICIALIZANDO NAVEGADOR EDGE")
        self.logger.info("="*80)
        self.logger.info("   ℹ️ Usando Edge (más permisivo con descargas automáticas)")
        
        options = EdgeOptions()
        
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
        self.logger.info("🚀 PASO 1: INICIALIZANDO NAVEGADOR CHROME (FALLBACK)")
        self.logger.info("="*80)
        self.logger.info("   ℹ️ Usando Chrome con perfil temporal para evitar bloqueos de permisos")
        
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        
        options = ChromeOptions()
        
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
        
        # Usar un perfil temporal para evitar bloqueos de permisos
        import tempfile
        temp_profile = tempfile.mkdtemp()
        options.add_argument(f'--user-data-dir={temp_profile}')
        self.logger.info(f"   📁 Usando perfil temporal: {temp_profile}")
        
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
        
        try:
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
    
    def _get_month_folder_name(self, fecha=None):
        """
        Obtiene el nombre de la carpeta del mes en español + año
        
        Args:
            fecha: datetime opcional (default: fecha actual)
        
        Returns:
            str: Nombre de la carpeta (ej: "enero_2026")
        """
        if fecha is None:
            fecha = datetime.now()
        
        meses_espanol = {
            1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
            5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
            9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
        }
        
        mes_nombre = meses_espanol[fecha.month]
        año = fecha.year
        
        return f"{mes_nombre}_{año}"
    
    def _get_month_folder_path(self, fecha=None):
        """
        Obtiene la ruta completa de la carpeta del mes
        
        Args:
            fecha: datetime opcional (default: fecha actual)
        
        Returns:
            Path: Ruta completa de la carpeta del mes
        """
        nombre_carpeta = self._get_month_folder_name(fecha)
        return self.download_dir_base / nombre_carpeta
    
    def _ensure_month_folder_exists(self, fecha=None):
        """
        Crea la carpeta del mes si no existe y configura el directorio de descarga
        
        Args:
            fecha: datetime opcional (default: fecha actual)
        
        Returns:
            Path: Ruta de la carpeta del mes creada/verificada
        """
        if fecha is None:
            fecha = datetime.now()
        
        carpeta_mes = self._get_month_folder_path(fecha)
        nombre_carpeta = self._get_month_folder_name(fecha)
        
        self.logger.info(f"   📂 Verificando carpeta del mes: {nombre_carpeta}")
        
        if not carpeta_mes.exists():
            self.logger.info(f"      ⚠️ Carpeta no existe, creando: {carpeta_mes}")
            carpeta_mes.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"      ✅ Carpeta creada exitosamente")
        else:
            self.logger.info(f"      ✅ Carpeta ya existe")
        
        # Actualizar directorio de descarga y preferencias de Edge
        self.download_dir = carpeta_mes
        self.download_prefs["download.default_directory"] = str(self.download_dir)
        
        self.logger.info(f"      📁 Directorio de descarga configurado: {self.download_dir}")
        
        return carpeta_mes
    
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
            time.sleep(1)
            
            # Buscar input de fecha "Hasta"
            self.logger.info("      4) Buscando campo 'Hasta'...")
            hasta_input = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//input[contains(@placeholder, 'Hasta') or contains(@class, 'p-datepicker-trigger')]"
                ))
            )
            self.logger.info("         ✅ Campo 'Hasta' encontrado")
            
            hasta_input.click()
            time.sleep(1)
            
            # Navegar al mes correcto en el calendario
            self.logger.info("      5) Navegando al mes correcto en calendario...")
            self._navigate_calendar_to_date(fecha_fin)
            
            # Seleccionar día de fin
            self.logger.info(f"      6) Seleccionando día de fin: {fecha_fin.day}")
            self._select_day_in_calendar(fecha_fin.day)
            time.sleep(1)
            
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
            # Buscar dropdown de acciones
            self.logger.info("      1) Buscando dropdown de acciones...")
            acciones_dropdown = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//a[contains(@class, 'dropdown-toggle') and contains(text(), 'Acciones')]"
                ))
            )
            self.logger.info("         ✅ Dropdown de acciones encontrado")
            
            acciones_dropdown.click()
            time.sleep(1)
            
            # Buscar opción "Órdenes con Productos (Un producto por fila)"
            self.logger.info("      2) Buscando opción 'Órdenes con Productos'...")
            report_option = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'dropdown-item') and contains(text(), 'Órdenes con Productos (Un producto por fila)')]"
                ))
            )
            self.logger.info("         ✅ Opción encontrada")
            
            report_option.click()
            time.sleep(3)
            
            # Esperar modal de éxito
            self.logger.info("      3) Esperando modal de confirmación...")
            modal_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'swal2-confirm') and contains(text(), 'Ver reportes')]"
                ))
            )
            self.logger.info("         ✅ Modal de confirmación apareció")
            
            # Esperar 7 segundos antes de hacer click
            self.logger.info("      4) Esperando 7 segundos antes de continuar...")
            time.sleep(7)
            
            # Click en "Ver reportes"
            self.logger.info("      5) Haciendo click en 'Ver reportes'...")
            modal_button.click()
            time.sleep(3)
            
            # Verificar que redirigió a la página de reportes
            self.wait.until(EC.url_contains("/dashboard/reports/downloads"))
            self.logger.info(f"         ✅ Redirigido a: {self.driver.current_url}")
            
            return True
            
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
        
        while time.time() - start_time < max_wait_time:
            try:
                # Buscar la primera fila de la tabla (reporte más reciente)
                self.logger.info(f"      Verificando estado del reporte... ({int(time.time() - start_time)}s)")
                
                # Buscar filas de la tabla
                rows = self.driver.find_elements(
                    By.XPATH,
                    "//tbody//tr[contains(@class, 'table-row')]"
                )
                
                if rows:
                    # Obtener la primera fila (más reciente)
                    first_row = rows[0]
                    
                    # Verificar estado - buscar elemento con texto "Listo"
                    try:
                        estado_element = first_row.find_element(
                            By.XPATH,
                            ".//app-dropi-tag//span[contains(text(), 'Listo')]"
                        )
                        
                        if estado_element:
                            self.logger.info("         ✅ Reporte está listo!")
                            
                            # Obtener nombre del archivo antes de descargar
                            try:
                                filename_element = first_row.find_element(
                                    By.XPATH,
                                    ".//span[contains(@class, 'table-labels') and contains(text(), '.xlsx')]"
                                )
                                expected_filename = filename_element.text.strip()
                                self.logger.info(f"         📄 Archivo esperado: {expected_filename}")
                            except:
                                # Si no encuentra el nombre exacto, buscar cualquier .xlsx en la fila
                                self.logger.info("         📄 Buscando archivo .xlsx en la fila...")
                                expected_filename = None
                            
                            # Buscar botón de descarga - intentar múltiples selectores
                            download_button = None
                            
                            # Método 1: Buscar por SVG con File-download
                            try:
                                download_button = first_row.find_element(
                                    By.XPATH,
                                    ".//app-icon[contains(@class, 'action-icon')]//svg[contains(@use, 'File-download')]"
                                )
                                self.logger.info("         ✅ Botón de descarga encontrado (método 1)")
                            except:
                                pass
                            
                            # Método 2: Buscar por el icono de descarga directamente
                            if not download_button:
                                try:
                                    download_button = first_row.find_element(
                                        By.XPATH,
                                        ".//div[contains(@class, 'ng-star-inserted')]//app-icon[contains(@class, 'action-icon')]"
                                    )
                                    self.logger.info("         ✅ Botón de descarga encontrado (método 2)")
                                except:
                                    pass
                            
                            # Método 3: Buscar cualquier icono clickeable en la columna de acciones
                            if not download_button:
                                try:
                                    action_icons = first_row.find_elements(
                                        By.XPATH,
                                        ".//td[contains(@class, 'action-button')]//app-icon"
                                    )
                                    if action_icons:
                                        download_button = action_icons[0]  # Primer icono es el de descarga
                                        self.logger.info("         ✅ Botón de descarga encontrado (método 3)")
                                except:
                                    pass
                            
                            if download_button:
                                # Hacer click en descargar
                                self.logger.info("         📥 Haciendo click en descargar...")
                                try:
                                    # Scroll al botón para asegurar que sea visible
                                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
                                    time.sleep(0.5)
                                    download_button.click()
                                except Exception as click_error:
                                    # Si falla el click normal, usar JavaScript
                                    self.logger.warning(f"         ⚠️ Click normal falló, usando JavaScript: {str(click_error)}")
                                    self.driver.execute_script("arguments[0].click();", download_button)
                                
                                # Esperar y verificar si aparece algún diálogo de permisos
                                time.sleep(2)
                                
                                # Verificar si hay algún diálogo de permisos
                                try:
                                    # Buscar diálogos comunes que bloquean descargas
                                    # Estos pueden aparecer como alertas o elementos específicos
                                    alerts = self.driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'permiso') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'permission') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'descargar')]")
                                    if alerts:
                                        self.logger.warning("         ⚠️ Posible diálogo de permisos detectado")
                                        # Intentar cerrar cualquier diálogo presionando ESC o Enter
                                        from selenium.webdriver.common.keys import Keys
                                        try:
                                            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                                            time.sleep(1)
                                        except:
                                            pass
                                except:
                                    pass  # No hay diálogo, continuar normalmente
                                
                                time.sleep(5)  # Esperar 5 segundos adicionales para la descarga
                                
                                # Buscar el archivo descargado
                                if expected_filename:
                                    downloaded_file = self._find_downloaded_file(expected_filename)
                                else:
                                    # Buscar el archivo más reciente
                                    downloaded_file = self._find_downloaded_file(None)
                                
                                if downloaded_file:
                                    self.logger.info(f"         ✅ Archivo descargado: {downloaded_file}")
                                    return downloaded_file
                                else:
                                    # Esperar un poco más y buscar de nuevo
                                    self.logger.info("         ⏳ Archivo no encontrado aún, esperando más tiempo...")
                                    time.sleep(5)
                                    if expected_filename:
                                        downloaded_file = self._find_downloaded_file(expected_filename)
                                    else:
                                        downloaded_file = self._find_downloaded_file(None)
                                    if downloaded_file:
                                        return downloaded_file
                            else:
                                self.logger.warning("         ⚠️ No se encontró el botón de descarga, esperando...")
                    except NoSuchElementException:
                        # El estado "Listo" aún no aparece
                        pass
                
                # Si no está listo, esperar
                self.logger.info("         ⏳ Reporte aún no está listo, esperando...")
                time.sleep(check_interval)
                
            except NoSuchElementException:
                # El reporte aún no está listo
                self.logger.info("         ⏳ Reporte aún no está disponible, esperando...")
                time.sleep(check_interval)
                
            except Exception as e:
                self.logger.warning(f"         ⚠️ Error al verificar estado: {str(e)}")
                time.sleep(check_interval)
        
        self.logger.error(f"      ❌ Timeout: El reporte no estuvo listo en {max_wait_time} segundos")
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
            
            # Paso 2: Obtener fecha actual y crear/verificar carpeta del mes
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("📅 PASO 2: CONFIGURANDO CARPETA DEL MES ACTUAL")
            self.logger.info("="*80)
            hoy = datetime.now()
            nombre_carpeta_mes = self._get_month_folder_name(hoy)
            self.logger.info(f"   📆 Fecha actual: {hoy.strftime('%d/%m/%Y')}")
            self.logger.info(f"   📂 Carpeta del mes: {nombre_carpeta_mes}")
            
            carpeta_mes = self._ensure_month_folder_exists(hoy)
            self.logger.info(f"   ✅ Carpeta del mes configurada: {carpeta_mes}")
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
            self.logger.info("="*80)
            
            # Paso 7: Mostrar resumen final
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("✅ PASO 7: RESUMEN FINAL")
            self.logger.info("="*80)
            self.logger.info("   🎉 PROCESO DE DESCARGA COMPLETADO EXITOSAMENTE")
            self.logger.info("")
            self.logger.info(f"   📂 Carpeta del mes: {nombre_carpeta_mes}")
            self.logger.info(f"   📁 Ubicación: {carpeta_mes}")
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
        headless = options.get('headless', False)
        download_dir = options.get('download_dir', None)
        user_id = options.get('user_id')
        email = options.get('email')
        password = options.get('password')

        if user_id:
            try:
                from core.models import UserProfile
                # Assuming User profile is linked via user_id directly or user__id
                # user_id typically refers to User.id
                profile = UserProfile.objects.filter(user__id=user_id).first()
                if profile and profile.dropi_email and profile.dropi_password:
                    email = profile.dropi_email
                    password = profile.dropi_password
                    self.stdout.write(self.style.SUCCESS(f'[INFO] Usando credenciales de base de datos para usuario ID {user_id}'))
                else:
                    self.stdout.write(self.style.WARNING(f'[WARN] No se encontraron credenciales completas para usuario ID {user_id}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[ERROR] Falló al obtener perfil de usuario: {e}'))

        # Crear y ejecutar el bot
        bot = DropiDownloaderReporterBot(
            headless=headless, 
            download_dir=download_dir,
            use_chrome_fallback=use_chrome_fallback,
            email=email,
            password=password
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
