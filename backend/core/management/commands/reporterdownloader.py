"""
Bot Descargador de Reportes para Dropi
Este bot descarga dos reportes de órdenes:
- Reporte BASE: un mes exacto (desde día 16 hasta día 16)
- Reporte ACTUAL: desde día 16 hasta hoy

Los archivos se guardan con nombres descriptivos que incluyen las fechas.
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
    Bot para descargar y comparar reportes de Dropi
    
    Funcionalidad:
    1. Descarga dos reportes: uno actual y uno de 2 días antes
    2. Compara ambos reportes para encontrar órdenes sin movimiento
    3. Genera un Excel con las órdenes sin movimiento (>46 horas)
    4. Pasa el Excel al reporter para generar observaciones
    """
    
    # Credenciales
    DROPI_EMAIL = "dahellonline@gmail.com"
    DROPI_PASSWORD = "Bigotes2001@"
    DROPI_URL = "https://app.dropi.co/login"
    
    # URLs importantes
    ORDERS_URL = "https://app.dropi.co/dashboard/orders"
    REPORTS_URL = "https://app.dropi.co/dashboard/reports/downloads"
    
    def __init__(self, headless=False, download_dir=None):
        """
        Inicializa el bot
        
        Args:
            headless: Si True, ejecuta el navegador sin interfaz gráfica
            download_dir: Directorio donde se guardarán los archivos descargados
        """
        self.headless = headless
        self.driver = None
        self.wait = None
        self.logger = self._setup_logger()
        
        # Configurar directorio de descargas
        if download_dir is None:
            # Directorio por defecto: results/downloads
            base_dir = Path(__file__).parent.parent.parent.parent
            download_dir = base_dir / 'results' / 'downloads'
        
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar preferencias de descarga para Chrome
        self.download_prefs = {
            "download.default_directory": str(self.download_dir),
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
        
        PASO 1: Configurar Chrome con preferencias de descarga
        """
        self.logger.info("="*80)
        self.logger.info("🚀 PASO 1: INICIALIZANDO NAVEGADOR CHROME")
        self.logger.info("="*80)
        
        options = webdriver.ChromeOptions()
        
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
        
        # Evitar detección de automatización
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Preferencias incluyendo descargas
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            **self.download_prefs  # Agregar preferencias de descarga
        }
        options.add_experimental_option("prefs", prefs)
        
        self.logger.info(f"   📁 Directorio de descargas: {self.download_dir}")
        self.logger.info("   📦 Creando instancia de Chrome...")
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.logger.info("   ✅ Chrome iniciado correctamente")
        except Exception as e:
            self.logger.error(f"   ❌ Error al iniciar Chrome: {e}")
            self.logger.info("   💡 Asegúrate de tener Chrome instalado")
            raise
        
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
    
    def _calculate_dates(self):
        """
        Calcula las fechas para los filtros de reportes
        
        Lógica:
        - Reporte actual: desde 16 del mes anterior hasta hoy (un mes y algunos días)
        - Reporte base: desde 16 del mes anterior hasta el día 16 del mes actual (exactamente un mes)
        
        Ejemplo si hoy es 18/01/2026:
        - Reporte actual: desde 16/12/2025 hasta 18/01/2026
        - Reporte base: desde 16/12/2025 hasta 16/01/2026
        
        PASO 4: Calcular fechas para los filtros
        
        Returns:
            tuple: (fecha_inicio_actual, fecha_fin_actual, fecha_inicio_base, fecha_fin_base)
        """
        self.logger.info("="*80)
        self.logger.info("📅 PASO 4: CALCULANDO FECHAS PARA LOS FILTROS")
        self.logger.info("="*80)
        
        hoy = datetime.now()
        
        # Calcular día 16 del mes actual
        dia_base = 16
        fecha_fin_base = datetime(hoy.year, hoy.month, dia_base)
        
        # Si hoy es antes del día 16, usar el día 16 del mes anterior
        if hoy.day < dia_base:
            # Si estamos antes del día 16, el reporte base termina el día 16 del mes anterior
            if hoy.month == 1:
                fecha_fin_base = datetime(hoy.year - 1, 12, dia_base)
            else:
                fecha_fin_base = datetime(hoy.year, hoy.month - 1, dia_base)
        
        # Calcular fecha de inicio (día 16 del mes anterior al del reporte base)
        if fecha_fin_base.month == 1:
            fecha_inicio = datetime(fecha_fin_base.year - 1, 12, dia_base)
        else:
            fecha_inicio = datetime(fecha_fin_base.year, fecha_fin_base.month - 1, dia_base)
        
        # Reporte actual: desde día 16 del mes anterior hasta hoy
        fecha_inicio_actual = fecha_inicio
        fecha_fin_actual = hoy
        
        # Reporte base: desde día 16 del mes anterior hasta día 16 del mes actual (exactamente un mes)
        fecha_inicio_base = fecha_inicio
        fecha_fin_base = fecha_fin_base
        
        self.logger.info(f"   📊 Reporte ACTUAL (desde {fecha_inicio_actual.strftime('%d/%m/%Y')} hasta hoy):")
        self.logger.info(f"      Desde: {fecha_inicio_actual.strftime('%d/%m/%Y')}")
        self.logger.info(f"      Hasta: {fecha_fin_actual.strftime('%d/%m/%Y')}")
        self.logger.info(f"   📊 Reporte BASE (un mes exacto, para comparación):")
        self.logger.info(f"      Desde: {fecha_inicio_base.strftime('%d/%m/%Y')}")
        self.logger.info(f"      Hasta: {fecha_fin_base.strftime('%d/%m/%Y')}")
        self.logger.info("="*80)
        
        return fecha_inicio_actual, fecha_fin_actual, fecha_inicio_base, fecha_fin_base
    
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
                                    download_button.click()
                                except:
                                    # Si falla el click normal, usar JavaScript
                                    self.driver.execute_script("arguments[0].click();", download_button)
                                
                                time.sleep(7)  # Esperar 7 segundos para la descarga
                                
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
                                    self.logger.warning("         ⚠️ Archivo no encontrado, esperando más tiempo...")
                                    time.sleep(10)
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
    
    def _rename_downloaded_file(self, downloaded_file, fecha_inicio, fecha_fin, tipo_reporte):
        """
        Renombra el archivo descargado con un nombre descriptivo que incluye las fechas
        
        Args:
            downloaded_file: Ruta del archivo descargado
            fecha_inicio: Fecha de inicio (datetime)
            fecha_fin: Fecha de fin (datetime)
            tipo_reporte: Tipo de reporte ('base' o 'actual')
        
        Returns:
            str: Ruta del archivo renombrado
        """
        try:
            # Crear nombre descriptivo con timestamp para evitar conflictos
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            fecha_inicio_str = fecha_inicio.strftime('%Y%m%d')
            fecha_fin_str = fecha_fin.strftime('%Y%m%d')
            nuevo_nombre = f"reporte_{tipo_reporte}_{fecha_inicio_str}_{fecha_fin_str}_{timestamp}.xlsx"
            
            # Ruta completa del nuevo archivo
            nuevo_path = self.download_dir / nuevo_nombre
            
            # Renombrar archivo
            if os.path.exists(downloaded_file):
                os.rename(downloaded_file, nuevo_path)
                self.logger.info(f"   📝 Archivo renombrado: {nuevo_nombre}")
                return str(nuevo_path)
            else:
                self.logger.warning(f"   ⚠️ Archivo original no encontrado: {downloaded_file}")
                return downloaded_file
                
        except Exception as e:
            self.logger.warning(f"   ⚠️ Error al renombrar archivo: {str(e)}")
            return downloaded_file
    
    def _download_single_report(self, fecha_inicio, fecha_fin, reporte_nombre, tipo_reporte):
        """
        Descarga un reporte completo con las fechas especificadas y lo renombra
        
        Este método siempre navega desde cero a Mis Pedidos para asegurar un estado limpio.
        
        Args:
            fecha_inicio: Fecha de inicio (datetime)
            fecha_fin: Fecha de fin (datetime)
            reporte_nombre: Nombre descriptivo del reporte (para logs)
            tipo_reporte: Tipo de reporte ('base' o 'actual')
        
        Returns:
            str: Ruta del archivo descargado y renombrado o None si falló
        """
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
            renamed_file = self._rename_downloaded_file(downloaded_file, fecha_inicio, fecha_fin, tipo_reporte)
            
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
        
        Flujo:
        1. Inicializar navegador
        2. Login
        3. Calcular fechas
        4. Descargar reporte BASE (un mes exacto, desde día 16 hasta día 16)
        5. Descargar reporte ACTUAL (desde día 16 hasta hoy)
        6. Renombrar archivos con nombres descriptivos que incluyen las fechas
        """
        self.logger.info("="*80)
        self.logger.info("🤖 INICIANDO BOT DESCARGADOR DE REPORTES")
        self.logger.info("="*80)
        self.logger.info(f"   📁 Directorio de descargas: {self.download_dir}")
        self.logger.info("="*80)
        
        try:
            # Paso 1: Inicializar navegador
            self._init_driver()
            
            # Paso 2: Login
            if not self._login():
                self.logger.error("❌ Login fallido. Abortando.")
                return False
            
            # Paso 3: Calcular fechas
            fecha_inicio_actual, fecha_fin_actual, fecha_inicio_base, fecha_fin_base = self._calculate_dates()
            
            # Paso 4: Descargar reporte BASE (un mes exacto, para comparación)
            self.logger.info("")
            self.reporte_anterior_path = self._download_single_report(
                fecha_inicio_base,
                fecha_fin_base,
                f"REPORTE BASE (desde {fecha_inicio_base.strftime('%d/%m/%Y')} hasta {fecha_fin_base.strftime('%d/%m/%Y')})",
                'base'
            )
            
            if not self.reporte_anterior_path:
                self.logger.error("❌ No se pudo descargar el reporte base. Abortando.")
                return False
            
            self.stats['reporte_anterior_descargado'] = True
            
            # Paso 5: Descargar reporte ACTUAL (hasta hoy)
            # Nota: Este método siempre navega desde cero a Mis Pedidos para estado limpio
            self.logger.info("")
            self.reporte_actual_path = self._download_single_report(
                fecha_inicio_actual,
                fecha_fin_actual,
                f"REPORTE ACTUAL (desde {fecha_inicio_actual.strftime('%d/%m/%Y')} hasta {fecha_fin_actual.strftime('%d/%m/%Y')})",
                'actual'
            )
            
            if not self.reporte_actual_path:
                self.logger.error("❌ No se pudo descargar el reporte actual. Abortando.")
                return False
            
            self.stats['reporte_actual_descargado'] = True
            
            # Paso 6: Mostrar resumen final
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("✅ PROCESO DE DESCARGA COMPLETADO EXITOSAMENTE")
            self.logger.info("="*80)
            self.logger.info(f"   📁 Reporte BASE: {self.reporte_anterior_path}")
            self.logger.info(f"   📁 Reporte ACTUAL: {self.reporte_actual_path}")
            self.logger.info("")
            self.logger.info("   💡 Próximo paso: Ejecutar el comparador de reportes:")
            self.logger.info(f"      python manage.py reportcomparer --base \"{self.reporte_anterior_path}\" --actual \"{self.reporte_actual_path}\"")
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
    
    def handle(self, *args, **options):
        headless = options.get('headless', False)
        download_dir = options.get('download_dir', None)
        
        # Crear y ejecutar el bot
        bot = DropiDownloaderReporterBot(headless=headless, download_dir=download_dir)
        
        try:
            success = bot.run()
            if success:
                self.stdout.write(
                    self.style.SUCCESS('✓ Bot ejecutado exitosamente')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('✗ Bot ejecutado con errores')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error al ejecutar el bot: {str(e)}')
            )
            raise
