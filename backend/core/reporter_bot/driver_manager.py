"""
Driver Manager - Gestión centralizada del WebDriver de Selenium

Este módulo implementa el patrón Singleton para compartir una única instancia
del navegador entre todos los módulos del bot, reduciendo el consumo de recursos.

Soporta múltiples navegadores:
- Chrome (default)
- Edge (recomendado para descargas - más ligero)
- Brave (basado en Chromium)
- Firefox (alternativa completa)
"""

import os
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait


class DriverManager:
    """
    Clase encargada ÚNICAMENTE de la gestión del Webdriver de Selenium.
    Implementa patrón Singleton para compartir driver entre módulos.
    
    Características:
    - Soporte múltiples navegadores (Chrome, Edge, Brave, Firefox)
    - Optimizaciones agresivas de CPU/RAM (sin GPU, sin imágenes)
    - Configuración de descargas automáticas
    - Anti-detección básico
    - Soporte para Docker y local
    - Validación de usuario y manejo robusto de errores
    """
    
    _instance = None
    _driver = None
    
    # Navegadores soportados
    SUPPORTED_BROWSERS = ['chrome', 'edge', 'brave', 'firefox']
    
    def __new__(cls, headless=False, logger=None, download_dir=None, browser='edge'):
        """Patrón Singleton - Retorna la misma instancia si ya existe"""
        if cls._instance is None:
            cls._instance = super(DriverManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, headless=False, logger=None, download_dir=None, browser='edge'):
        """
        Inicializa el manager (solo una vez por instancia Singleton)
        
        Args:
            headless: Si True, ejecuta sin interfaz gráfica
            logger: Logger configurado
            download_dir: Directorio para descargas
            browser: Navegador a usar ('chrome', 'edge', 'brave', 'firefox')
        """
        if hasattr(self, '_initialized'):
            return  # Ya inicializado
            
        self.headless = headless
        self.logger = logger
        self.download_dir = download_dir
        self.browser = browser.lower() if browser else 'edge'
        self.TIMEOUT_SECONDS = 15
        self._initialized = True
        
        # Validar navegador
        if self.browser not in self.SUPPORTED_BROWSERS:
            if self.logger:
                self.logger.warning(f"⚠️ Navegador '{browser}' no soportado. Usando Edge por defecto.")
            self.browser = 'edge'
    
    def _log_step(self, message, level='info'):
        """Helper para logging consistente"""
        if self.logger:
            if level == 'info':
                self.logger.info(f"   📍 {message}")
            elif level == 'warning':
                self.logger.warning(f"   ⚠️ {message}")
            elif level == 'error':
                self.logger.error(f"   ❌ {message}")
            elif level == 'success':
                self.logger.info(f"   ✅ {message}")
    
    def _init_one_browser(self):
        """Inicializa un solo navegador (self.browser). Usado por init_driver."""
        if self.browser == 'edge':
            self._driver = self._init_edge()
        elif self.browser == 'chrome':
            self._driver = self._init_chrome()
        elif self.browser == 'brave':
            self._driver = self._init_brave()
        elif self.browser == 'firefox':
            self._driver = self._init_firefox()
        else:
            self._log_step(f"Navegador '{self.browser}' no reconocido, usando Edge", 'warning')
            self._driver = self._init_edge()

    def init_driver(self, browser_priority=None):
        """
        Inicializa el driver de Selenium. Si se pasa browser_priority (lista),
        intenta cada navegador en orden hasta que uno funcione (fallback).
        
        Args:
            browser_priority: Lista opcional, ej. ['chrome', 'firefox', 'edge'].
                             Si es None, se usa solo self.browser.
        
        Returns:
            webdriver: Instancia del driver configurado
        """
        # Si ya existe un driver, retornarlo
        if self._driver is not None:
            if self.logger:
                self.logger.info("♻️ Reutilizando driver existente (Singleton)")
            return self._driver

        # Normalizar lista de fallback (chromium -> chrome)
        if browser_priority:
            browser_priority = [
                (b.strip().lower() if b.strip().lower() != 'chromium' else 'chrome')
                for b in browser_priority if b and str(b).strip()
            ]
            browser_priority = [b for b in browser_priority if b in self.SUPPORTED_BROWSERS]

        last_error = None
        tried = []

        for one_browser in (browser_priority or [self.browser]):
            self.browser = one_browser
            DriverManager._driver = None
            self._driver = None
            if self.logger:
                self.logger.info("="*60)
                self.logger.info(f"🚀 Intentando navegador: {self.browser.upper()}")
                self.logger.info("="*60)
            try:
                self._init_one_browser()
                if self._driver:
                    tried.append(self.browser)
                    self._configure_downloads()
                    self._apply_anti_detection()
                    if self.logger:
                        self.logger.info(f"   🌐 Navegador listo: {self.browser}")
                        self.logger.info("="*60)
                    return self._driver
            except Exception as e:
                last_error = e
                tried.append(self.browser)
                if self.logger:
                    self.logger.warning(f"   ⚠️ Falló {self.browser}: {e}")
                continue

        if self.logger and tried:
            self.logger.error(f"   ❌ Ningún navegador funcionó (probados: {', '.join(tried)})")
        raise RuntimeError(
            f"No se pudo inicializar ningún navegador (probados: {tried or [self.browser]}). Último error: {last_error}"
        )
    
    def _init_edge(self):
        """Inicializa Microsoft Edge (recomendado para descargas)"""
        self._log_step("Inicializando Microsoft Edge...", 'info')
        
        options = EdgeOptions()
        self._apply_common_options(options)
        
        # Configurar binario de Edge si está en variables de entorno (Docker)
        edge_bin = os.environ.get('EDGE_BIN')
        if edge_bin and os.path.exists(edge_bin):
            options.binary_location = edge_bin
            self._log_step(f"Usando binario Edge: {edge_bin}", 'info')
        elif not os.environ.get('EDGE_BIN') and os.path.exists('/usr/bin/microsoft-edge'):
             # Fallback directo en Linux si no está la variable
             options.binary_location = '/usr/bin/microsoft-edge'
             self._log_step("Usando binario Edge detectado: /usr/bin/microsoft-edge", 'info')
        
        try:
            # Edge generalmente viene con Windows, intentar directo
            self._driver = webdriver.Edge(options=options)
            self._log_step("Edge iniciado exitosamente", 'success')
            return self._driver
        except Exception as e:
            self._log_step(f"Error iniciando Edge: {e}", 'error')
            # Intentar con webdriver-manager
            try:
                from webdriver_manager.microsoft import EdgeChromiumDriverManager
                service = EdgeService(EdgeChromiumDriverManager().install())
                self._driver = webdriver.Edge(service=service, options=options)
                self._log_step("Edge iniciado con webdriver-manager", 'success')
                return self._driver
            except ImportError:
                self._log_step("webdriver-manager no disponible", 'warning')
                raise
    
    def _init_chrome(self):
        """Inicializa Google Chrome / Chromium"""
        self._log_step("Inicializando Chrome/Chromium...", 'info')
        
        options = ChromeOptions()
        self._apply_common_options(options)
        
        # En Docker: usar binario Chromium instalado por apt (evita Edge/msedgedriver)
        chrome_bin = os.environ.get('CHROME_BIN')
        if chrome_bin and os.path.exists(chrome_bin):
            options.binary_location = chrome_bin
            self._log_step(f"Binario: {chrome_bin}", 'info')
        
        try:
            # Intentar driver del sistema (Docker/Linux)
            chromedriver_path = os.environ.get('CHROMEDRIVER')
            if not chromedriver_path or not os.path.exists(chromedriver_path):
                chromedriver_path = None
                possible_paths = [
                    '/usr/bin/chromedriver',
                    '/usr/local/bin/chromedriver',
                    '/usr/lib/chromium/chromedriver'
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        chromedriver_path = path
                        break
            
            if chromedriver_path:
                service = ChromeService(chromedriver_path)
                self._driver = webdriver.Chrome(service=service, options=options)
                self._log_step(f"Chrome/Chromium iniciado con driver: {chromedriver_path}", 'success')
                return self._driver
            else:
                # Fallback webdriver-manager
                try:
                    from webdriver_manager.chrome import ChromeDriverManager
                    service = ChromeService(ChromeDriverManager().install())
                    self._driver = webdriver.Chrome(service=service, options=options)
                    self._log_step("Chrome iniciado con webdriver-manager", 'success')
                    return self._driver
                except ImportError:
                    self._driver = webdriver.Chrome(options=options)
                    self._log_step("Chrome iniciado con Selenium default", 'success')
                    return self._driver
        except Exception as e:
            self._log_step(f"Error iniciando Chrome: {e}", 'error')
            raise
    
    def _init_brave(self):
        """Inicializa Brave Browser (usa ChromeDriver)"""
        self._log_step("Inicializando Brave Browser...", 'info')
        
        options = ChromeOptions()
        self._apply_common_options(options)
        
        # Brave usa ChromeDriver pero necesita ruta específica
        brave_paths = [
            r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe',
            r'C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe',
            '/usr/bin/brave-browser',
            '/usr/bin/brave',
        ]
        
        brave_path = None
        for path in brave_paths:
            if os.path.exists(path):
                brave_path = path
                break
        
        if brave_path:
            options.binary_location = brave_path
            self._log_step(f"Brave encontrado en: {brave_path}", 'info')
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = ChromeService(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=options)
            self._log_step("Brave iniciado exitosamente", 'success')
            return self._driver
        except Exception as e:
            self._log_step(f"Error iniciando Brave: {e}", 'error')
            raise
    
    def _init_firefox(self):
        """Inicializa Mozilla Firefox (incl. Firefox ESR en Linux/Docker)"""
        self._log_step("Inicializando Mozilla Firefox...", 'info')
        
        options = FirefoxOptions()
        # En Docker/Linux: binario firefox-esr si existe
        firefox_bin = os.environ.get('FIREFOX_BIN')
        if not firefox_bin and os.path.exists('/usr/bin/firefox-esr'):
            firefox_bin = '/usr/bin/firefox-esr'
        if firefox_bin:
            options.binary_location = firefox_bin
            self._log_step(f"Binario: {firefox_bin}", 'info')
        self._apply_common_options_firefox(options)
        
        try:
            # Intentar GeckoDriver del sistema (Selenium 4 también lo descarga si falta)
            geckodriver_path = os.environ.get('GECKODRIVER')
            if not geckodriver_path or not os.path.exists(geckodriver_path):
                geckodriver_path = None
            possible_paths = ['/usr/bin/geckodriver', '/usr/local/bin/geckodriver']
            if not geckodriver_path:
                for path in possible_paths:
                    if os.path.exists(path):
                        geckodriver_path = path
                        break
            
            if geckodriver_path:
                service = FirefoxService(geckodriver_path)
                self._driver = webdriver.Firefox(service=service, options=options)
                self._log_step(f"Firefox iniciado con driver sistema: {geckodriver_path}", 'success')
                return self._driver
            else:
                # Fallback webdriver-manager
                try:
                    from webdriver_manager.firefox import GeckoDriverManager
                    service = FirefoxService(GeckoDriverManager().install())
                    self._driver = webdriver.Firefox(service=service, options=options)
                    self._log_step("Firefox iniciado con webdriver-manager", 'success')
                    return self._driver
                except ImportError:
                    self._driver = webdriver.Firefox(options=options)
                    self._log_step("Firefox iniciado con Selenium default", 'success')
                    return self._driver
        except Exception as e:
            self._log_step(f"Error iniciando Firefox: {e}", 'error')
            raise
    
    def _apply_common_options(self, options):
        """Aplica opciones comunes a navegadores basados en Chromium (Chrome, Edge, Brave)"""
        # --- CONFIGURACIÓN BASE ---
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--disable-infobars')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-notifications')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--disable-popup-blocking')
        # Estabilidad en Docker/headless (evita crashes al hacer click)
        if os.path.exists('/.dockerenv'):
            options.add_argument('--no-first-run')
            options.add_argument('--no-zygote')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--window-size=1920,1080')
        
        # --- OPTIMIZACIONES DE RENDIMIENTO (CPU/RAM) ---
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--mute-audio')
        options.add_argument('--disable-application-cache')
        options.add_argument('--blink-settings=imagesEnabled=false')
        options.add_argument('--disable-software-rasterizer')
        
        # Configuraciones para descargas automáticas (mejoradas para Edge)
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-features=DownloadBubble,DownloadBubbleV2')
        options.add_argument('--disable-prompt-on-repost')
        
        # --- ANTI-DETECCIÓN ---
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # --- MODO VISUAL vs HEADLESS ---
        if self.headless:
            self._log_step("Modo HEADLESS activado", 'info')
            options.add_argument('--headless=new')
        else:
            self._log_step("Modo VISIBLE activado - Podrás ver el navegador", 'info')

        # --- PERFIL TEMPORAL ---
        temp_dir = tempfile.mkdtemp(prefix=f'{self.browser}_selenium_')
        options.add_argument(f'--user-data-dir={temp_dir}')
        self._log_step(f"Perfil temporal: {temp_dir}", 'info')
        
        # --- PREFERENCIAS ---
        download_directory = str(self.download_dir) if self.download_dir else str(temp_dir)
        
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            # Bloquear imágenes para optimización
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            # Configuración de descargas (mejorada para Edge)
            "download.default_directory": download_directory,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "safebrowsing.disable_download_protection": True,
            "profile.default_content_settings.popups": 0,
            "profile.content_settings.exceptions.automatic_downloads": {
                "*": {"setting": 1}
            },
            "profile.default_content_setting_values.automatic_downloads": 1,
            # Bloquear la apertura automática de archivos Office
            "download.open_pdf_in_system_reader": False,
            "plugins.always_open_pdf_externally": True,
            "download.extensions_to_open": "",
            # Específico para Edge: 'Open Office files in the browser' -> Disabled
            "browser.helperApps.alwaysAsk.force": False,
            "browser.download.manager.showWhenStarting": False,
            # MIME types para Excel
            "browser.helperApps.neverAsk.saveToDisk": "application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream",
            "profile.default_content_settings.popups": 0,
        }
        options.add_experimental_option("prefs", prefs)
        
        self._log_step(f"Directorio de descarga: {download_directory}", 'info')
    
    def _apply_common_options_firefox(self, options):
        """Aplica opciones comunes a Firefox"""
        # --- CONFIGURACIÓN BASE ---
        if self.headless:
            self._log_step("Modo HEADLESS activado", 'info')
            options.add_argument('--headless')
        else:
            self._log_step("Modo VISIBLE activado - Podrás ver el navegador", 'info')
        
        # --- PREFERENCIAS FIREFOX ---
        download_directory = str(self.download_dir) if self.download_dir else tempfile.mkdtemp(prefix='firefox_selenium_')
        
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.dir", download_directory)
        options.set_preference("browser.download.useDownloadDir", True)
        options.set_preference("browser.helperApps.neverAsk.saveToDisk", 
                               "application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        options.set_preference("browser.download.manager.showWhenStarting", False)
        options.set_preference("browser.download.manager.showAlertOnComplete", False)
        options.set_preference("browser.download.manager.closeWhenDone", True)
        options.set_preference("permissions.default.image", 2)  # Bloquear imágenes
        
        self._log_step(f"Directorio de descarga: {download_directory}", 'info')
    
    def _configure_downloads(self):
        """Configura permisos de descarga vía CDP (solo Chromium)"""
        if self.browser in ['chrome', 'edge', 'brave']:
            try:
                self._log_step("Configurando permisos de descarga (CDP)...", 'info')
                download_directory = str(self.download_dir) if self.download_dir else tempfile.gettempdir()
                self._driver.execute_cdp_cmd('Browser.setDownloadBehavior', {
                    'behavior': 'allow',
                    'downloadPath': download_directory
                })
                self._log_step("Permisos de descarga configurados", 'success')
            except Exception as e:
                self._log_step(f"No se pudo configurar permisos CDP: {str(e)}", 'warning')
    
    def _apply_anti_detection(self):
        """Aplica scripts anti-detección"""
        try:
            self._driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            self._log_step("Anti-detección aplicado", 'info')
        except Exception:
            pass
    
    def get_driver(self):
        """Retorna el driver actual o None si no está inicializado"""
        return self._driver
    
    def get_wait(self, timeout=None):
        """Retorna un WebDriverWait configurado"""
        if self._driver is None:
            raise RuntimeError("Driver no inicializado. Llama a init_driver() primero.")
        timeout = timeout or self.TIMEOUT_SECONDS
        return WebDriverWait(self._driver, timeout)
    
    def close(self):
        """Cierra el navegador y limpia la instancia"""
        if self._driver:
            if self.logger:
                self.logger.info("🔌 Cerrando navegador...")
            try:
                self._driver.quit()
                self._log_step("Navegador cerrado exitosamente", 'success')
            except Exception as e:
                self._log_step(f"Error al cerrar navegador: {e}", 'warning')
            finally:
                self._driver = None
                DriverManager._driver = None  # Limpiar instancia Singleton
    
    @classmethod
    def reset_singleton(cls):
        """Resetea la instancia Singleton (útil para tests)"""
        cls._instance = None
        cls._driver = None
