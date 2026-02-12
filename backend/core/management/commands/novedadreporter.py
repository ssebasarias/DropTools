"""
Bot de Novedades Automático para Dropi (archivo independiente).

Este bot automatiza la solución de novedades específicas en Dropi:
- "No hay quien reciba"
- "Déficit de Capacidad"
- "El cliente se niega a recibir"
- "Reprogramar entrega"
- "No contesta Cliente"

Cada tipo de novedad tiene mensajes precargados específicos que se seleccionan
aleatoriamente al procesar la novedad.

Dependencias externas: solo core.models.User para consultar credenciales Dropi.
Todo lo demás (login, driver, navegación, lógica) es autocontenido en este archivo.
"""

import os
import sys
import time
import logging
import tempfile
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)
from django.core.management.base import BaseCommand
from core.models import User
from core.reporter_bot.driver_manager import DriverManager


def _configure_utf8_stdio():
    """Configura stdout/stderr a UTF-8 para evitar fallos con emojis en Windows. Autocontenido."""
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


class NovedadReporterBot:
    """Bot para automatizar solución de novedades en Dropi"""
    
    # Credenciales hardcodeadas para uso local
    DROPI_EMAIL = "dahellonline@gmail.com"
    DROPI_PASSWORD = "Bigotes2001@"
    DROPI_URL = "https://app.dropi.co/login"
    NOVELTIES_URL = "https://app.dropi.co/dashboard/novelties"
    
    # Novedades que requieren la respuesta "Volver a pasar"
    TARGET_NOVEDADES = [
        "No hay quien reciba",
        "Déficit de Capacidad",
        "El cliente se niega a recibir",
        "Reprogramar entrega",
        "No contesta Cliente"
    ]
    
    # Mensajes precargados para cada tipo de novedad
    SOLUTION_MESSAGES = {
        "No hay quien reciba": [
            "volver a pasar"
        ],
        "Déficit de Capacidad": [
            "volver a pasar"
        ],
        "El cliente se niega a recibir": [
            "el cliente informa que aun no pasar y sigue esperando entrega",
            "cliente indica que aun no pasar a domicilio volver a pasar"
        ],
        "Reprogramar entrega": [
            "pasar nuevamente cliente puede recibir",
            "pasar para el dia de mañana"
        ],
        "No contesta Cliente": [
            "necesita que se comuniquen por llamada en la entrega, volver a pasar",
            "no se han comunicado con el cliente, sigue esperando entrega"
        ]
    }
    
    def __init__(self, headless=False, user_id=None, dropi_label="reporter", email=None, password=None, browser="edge"):
        """
        Inicializa el bot
        
        Args:
            headless: Si True, ejecuta el navegador sin interfaz gráfica
            user_id: ID del usuario (tabla users.id) para cargar credenciales de Dropi desde BD
            dropi_label: (deprecated) Ya no se usa, las credenciales están en la tabla users directamente
            email: Email de Dropi a usar directamente (sobrescribe user_id)
            password: Password de Dropi a usar directamente (sobrescribe user_id)
            browser: Navegador a usar: edge, chrome, brave, firefox (default edge)
        """
        self.headless = headless
        self.user_id = user_id or 2
        self.browser = (browser or "edge").lower()
        self.dropi_label = dropi_label
        self.dropi_email_direct = email
        self.dropi_password_direct = password
        self.driver = None
        self.wait = None
        self.logger = self._setup_logger()
        self.stats = {
            'total_encontradas': 0,
            'procesadas': 0,
            'errores': 0,
            'saltadas': 0
        }
        
        # Las credenciales ya están hardcodeadas en la clase
        # No es necesario cargarlas desde BD
        self.logger.info(f"✅ Usando credenciales hardcodeadas: {self.DROPI_EMAIL}")
    
    def _get_solution_message(self, novedad_type):
        """Obtiene un mensaje de solución aleatorio para el tipo de novedad dado"""
        import random
        messages = self.SOLUTION_MESSAGES.get(novedad_type, ["volver a pasar"])
        return random.choice(messages)
        
    def _setup_logger(self):
        """Configura el logger para el bot"""
        logger = logging.getLogger('NovedadReporterBot')
        logger.setLevel(logging.INFO)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Handler para archivo
        log_dir = Path(__file__).parent.parent.parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_handler = logging.FileHandler(
            log_dir / f'novedad_reporter_{timestamp}.log',
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
        MODO LOCAL: Las credenciales están hardcodeadas en la clase.
        Este método se mantiene por compatibilidad pero no hace nada.
        """
        pass
    
    def _init_driver(self):
        """Inicializa el driver de Selenium usando DriverManager."""
        self.logger.info("="*60)
        self.logger.info(f"🚀 INICIALIZANDO NAVEGADOR {self.browser.upper()}")
        self.logger.info("="*60)
        
        try:
            # Resetear singleton para asegurar nueva instancia
            DriverManager.reset_singleton()
            
            dm = DriverManager(
                headless=self.headless,
                logger=self.logger,
                download_dir=None,
                browser=self.browser,
                proxy_config=None,
            )
            
            # Intentar inicializar con el navegador especificado
            browser_priority = [self.browser]
            if self.browser != 'chrome':
                browser_priority.append('chrome')
            if self.browser != 'firefox':
                browser_priority.append('firefox')
            
            self.driver = dm.init_driver(browser_priority=browser_priority)
            
            if not self.driver:
                raise Exception("No se pudo inicializar el driver")
            
            self.wait = WebDriverWait(self.driver, 15)
            self.logger.info("   ✅ Navegador inicializado correctamente")
            self.logger.info("="*60)
            
        except Exception as e:
            self.logger.error(f"   ❌ Error al inicializar navegador: {e}")
            raise

    def _create_driver(self, browser_name):
        """Crea el driver para un navegador concreto (edge, chrome, brave, firefox)."""
        use_firefox = browser_name == "firefox"
        if use_firefox:
            options = webdriver.FirefoxOptions()
            if self.headless:
                self.logger.info("🔇 Modo HEADLESS activado")
                options.add_argument("--headless")
            else:
                self.logger.info("👀 Modo VISIBLE activado")
            
            # Modo incógnito/privado
            self.logger.info("🕵️ Modo INCÓGNITO activado")
            options.add_argument("-private")
            
            # Preferencias adicionales
            options.set_preference("dom.webnotifications.enabled", False)
            options.set_preference("geo.enabled", False)
            options.set_preference("browser.privatebrowsing.autostart", True)
            
            self.logger.info("   📦 Creando instancia de Firefox...")
            self.driver = webdriver.Firefox(options=options)
            return
        # Chromium-based: Edge, Chrome, Brave
        temp_dir = tempfile.mkdtemp(prefix=f"{browser_name}_selenium_")
        self.logger.info(f"   📍 Perfil temporal: {temp_dir}")
        if browser_name == "edge":
            options = webdriver.EdgeOptions()
        else:
            options = webdriver.ChromeOptions()
            if browser_name == "brave":
                brave_path = os.getenv(
                    "BRAVE_PATH",
                    "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
                )
                if os.path.isfile(brave_path):
                    options.binary_location = brave_path
        if self.headless:
            self.logger.info("🔇 Modo HEADLESS activado")
            options.add_argument("--headless=new")
        else:
            self.logger.info("👀 Modo VISIBLE activado")
        
        # Modo incógnito
        self.logger.info("🕵️ Modo INCÓGNITO activado")
        options.add_argument("--incognito")
        
        options.add_argument(f"--user-data-dir={temp_dir}")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.geolocation": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        }
        options.add_experimental_option("prefs", prefs)
        self.logger.info(f"   📦 Creando instancia de {browser_name.upper()}...")
        try:
            from selenium.webdriver.edge.service import Service as EdgeService
            from selenium.webdriver.chrome.service import Service as ChromeService
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            from webdriver_manager.chrome import ChromeDriverManager
        except ImportError:
            EdgeService = ChromeService = EdgeChromiumDriverManager = ChromeDriverManager = None
        if browser_name == "edge":
            try:
                if EdgeService is not None and EdgeChromiumDriverManager is not None:
                    service = EdgeService(EdgeChromiumDriverManager().install())
                    self.driver = webdriver.Edge(service=service, options=options)
                else:
                    self.driver = webdriver.Edge(options=options)
            except Exception:
                self.driver = webdriver.Edge(options=options)
        else:
            try:
                if ChromeService is not None and ChromeDriverManager is not None:
                    service = ChromeService(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=options)
                else:
                    self.driver = webdriver.Chrome(options=options)
            except Exception:
                self.driver = webdriver.Chrome(options=options)
    
    def _login(self):
        """Inicia sesión en Dropi usando AuthManager"""
        try:
            self.logger.info("="*60)
            self.logger.info("🔐 INICIANDO PROCESO DE LOGIN CON AUTHMANAGER")
            self.logger.info("="*60)
            
            # Importar AuthManager
            from core.reporter_bot.auth_manager import AuthManager
            
            # Crear instancia de AuthManager
            auth_manager = AuthManager(
                driver=self.driver,
                user_id=self.user_id,
                logger=self.logger
            )
            
            # Cargar credenciales (usará las hardcodeadas del usuario)
            auth_manager.load_credentials(
                direct_email=self.DROPI_EMAIL,
                direct_password=self.DROPI_PASSWORD
            )
            
            # Intentar login
            if auth_manager.login():
                self.logger.info("✅ Login exitoso con AuthManager")
                return True
            else:
                self.logger.error("❌ Login fallido con AuthManager")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ Error en login: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _navigate_to_novelties(self):
        """Navega a la página de Novedades. Primero intenta URL directa, luego menú."""
        try:
            self.logger.info("="*60)
            self.logger.info("📍 NAVEGANDO A NOVEDADES")
            self.logger.info("="*60)
            try:
                current_url = self.driver.current_url or ""
            except Exception:
                current_url = ""
            if "/dashboard/novelties" in current_url:
                self.logger.info("   ✅ Ya estamos en Novedades")
                return True
            # 1) Navegación directa
            self.logger.info("   1) Navegación directa a Novedades...")
            self.driver.get(self.NOVELTIES_URL)
            time.sleep(2)
            # Esperar hasta 20s en pasos de 2s (por si la SPA tarda o la URL no cambia de inmediato)
            for _ in range(10):
                try:
                    url_now = self.driver.current_url or ""
                    if "/dashboard/novelties" in url_now:
                        self.logger.info(f"   ✅ URL correcta: {url_now}")
                        time.sleep(2)
                        self.logger.info("✅ Navegación exitosa a Novedades (directa)")
                        return True
                except Exception:
                    break
                try:
                    self.driver.find_element(By.TAG_NAME, "tbody")
                    self.logger.info("   ✅ Página con tabla cargada (Novedades)")
                    time.sleep(2)
                    self.logger.info("✅ Navegación exitosa a Novedades (tabla visible)")
                    return True
                except Exception:
                    pass
                time.sleep(2)
            self.logger.info("   🔄 Intentando por menú...")
            # 2) Fallback: menú
            wait_long = WebDriverWait(self.driver, 15)
            try:
                for xpath_menu in [
                    "//a[contains(@class, 'is-parent') and contains(., 'Mis Pedidos')]",
                    "//a[contains(., 'Mis Pedidos')]",
                ]:
                    try:
                        el = wait_long.until(EC.element_to_be_clickable((By.XPATH, xpath_menu)))
                        el.click()
                        time.sleep(2)
                        break
                    except TimeoutException:
                        continue
                for xpath_nov in [
                    "//a[@href='/dashboard/novelties' and contains(., 'Novedades')]",
                    "//a[contains(@href, 'novelties')]",
                ]:
                    try:
                        el = wait_long.until(EC.element_to_be_clickable((By.XPATH, xpath_nov)))
                        el.click()
                        time.sleep(3)
                        if "/dashboard/novelties" in (self.driver.current_url or ""):
                            self.logger.info("✅ Navegación exitosa a Novedades (menú)")
                            return True
                    except (TimeoutException, Exception):
                        continue
            except Exception as menu_error:
                self.logger.warning(f"   Menú falló: {menu_error}")
            try:
                if "/dashboard/novelties" in (self.driver.current_url or ""):
                    return True
            except Exception:
                pass
            self.logger.error("   No se detectó URL /dashboard/novelties ni tabla de novedades")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error al navegar a Novedades: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _set_pagination_to_1000(self):
        """Selecciona el dropdown de paginación a 1000 para ver todas las novedades"""
        try:
            self.logger.info("="*60)
            self.logger.info("📊 CONFIGURANDO PAGINACIÓN A 1000")
            self.logger.info("="*60)
            
            # Buscar el select de paginación
            self.logger.info("   Buscando dropdown de paginación...")
            pagination_select = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "select[name='select'], select#select, select.custom-select"
                ))
            )
            self.logger.info("   ✅ Dropdown encontrado")
            
            # Hacer scroll al dropdown si es necesario
            self.driver.execute_script("arguments[0].scrollIntoView(true);", pagination_select)
            time.sleep(1)
            
            # Seleccionar la opción de 1000
            self.logger.info("   Seleccionando opción 1000...")
            select = Select(pagination_select)
            
            # Buscar la opción con valor que contiene "1000"
            try:
                # Intentar seleccionar por texto visible
                select.select_by_visible_text("1000")
                self.logger.info("   ✅ Opción 1000 seleccionada por texto")
            except:
                # Si no funciona, intentar por valor
                try:
                    select.select_by_value("5: 1000")
                    self.logger.info("   ✅ Opción 1000 seleccionada por valor")
                except:
                    # Último intento: buscar la opción directamente
                    options = pagination_select.find_elements(By.TAG_NAME, "option")
                    for option in options:
                        if "1000" in option.text:
                            option.click()
                            self.logger.info("   ✅ Opción 1000 seleccionada por click directo")
                            break
            
            # Esperar a que carguen los cambios
            self.logger.info("   ⏳ Esperando a que carguen los cambios...")
            time.sleep(5)  # Espera inicial
            
            # Esperar a que la tabla se actualice (verificar que hay más filas o que la tabla cambió)
            try:
                # Esperar a que la tabla esté presente y tenga contenido
                self.wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, "tbody"))
                )
                time.sleep(3)  # Espera adicional para asegurar que todo cargó
                self.logger.info("   ✅ Cambios cargados correctamente")
            except:
                self.logger.warning("   ⚠️ No se pudo verificar la carga, continuando...")
            
            self.logger.info("✅ Paginación configurada a 1000")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error al configurar paginación: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            # Continuar de todas formas, puede que ya esté en 1000 o que no sea crítico
            return False
    
    def _find_novelties_table_rows(self):
        """Encuentra todas las filas de la tabla de novedades"""
        try:
            self.logger.info("   Buscando tabla de novedades...")
            # Esperar a que la tabla esté presente
            table = self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "tbody"))
            )
            
            # Encontrar todas las filas (tr) dentro del tbody
            rows = table.find_elements(By.TAG_NAME, "tr")
            self.logger.info(f"   ✅ Encontradas {len(rows)} filas en la tabla")
            return rows
            
        except Exception as e:
            self.logger.error(f"   ❌ Error al buscar tabla: {str(e)}")
            return []
    
    def _extract_novedad_text(self, row):
        """Extrae el texto de la novedad de una fila"""
        try:
            # Buscar el td que contiene los datos (según el HTML proporcionado)
            data_cells = row.find_elements(By.TAG_NAME, "td")
            if len(data_cells) < 3:
                return None
            
            # El tercer td (índice 2) contiene los datos con la novedad
            data_cell = data_cells[2]
            cell_text = data_cell.text
            
            # Buscar el texto "Novedad: " seguido del nombre
            for target in self.TARGET_NOVEDADES:
                if target in cell_text:
                    return target
            
            return None
            
        except Exception as e:
            self.logger.warning(f"   ⚠️ Error al extraer texto de novedad: {str(e)}")
            return None
    
    def _close_modal_if_open(self):
        """Cierra el modal si está abierto - Específico para ngb-modal-window de Bootstrap"""
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                if not self._check_modal_open():
                    if attempt == 0:
                        self.logger.info("   ✅ No hay modal abierto")
                    return True
                
                self.logger.info(f"   🔄 Intento {attempt + 1}/{max_attempts} de cerrar modal...")
                
                # Método 1: Buscar botones con data-dismiss="modal" (específico de Bootstrap)
                try:
                    # Buscar botón btn-close en el header
                    close_buttons = self.driver.find_elements(
                        By.XPATH,
                        "//button[@data-dismiss='modal'] | //button[contains(@class, 'btn-close')] | //button[@aria-label='Close'] | //button[contains(@class, 'btn-link') and contains(., 'Cerrar')]"
                    )
                    if close_buttons:
                        for btn in close_buttons:
                            try:
                                if btn.is_displayed():
                                    self.logger.info("   🖱️ Haciendo click en botón de cerrar...")
                                    # Intentar click normal primero
                                    try:
                                        btn.click()
                                    except:
                                        # Si falla, usar JavaScript
                                        self.driver.execute_script("arguments[0].click();", btn)
                                    time.sleep(2)
                                    if not self._check_modal_open():
                                        self.logger.info("   ✅ Modal cerrado (botón data-dismiss)")
                                        return True
                            except Exception as e:
                                self.logger.warning(f"   ⚠️ Error con botón: {str(e)}")
                                continue
                except Exception as e:
                    self.logger.warning(f"   ⚠️ Error buscando botones: {str(e)}")
                
                # Método 2: Presionar ESC
                try:
                    from selenium.webdriver.common.keys import Keys
                    body = self.driver.find_element(By.TAG_NAME, 'body')
                    body.send_keys(Keys.ESCAPE)
                    time.sleep(2)
                    if not self._check_modal_open():
                        self.logger.info("   ✅ Modal cerrado (tecla ESC)")
                        return True
                except Exception as e:
                    self.logger.warning(f"   ⚠️ Error con ESC: {str(e)}")
                
                # Método 3: Click en backdrop/overlay
                try:
                    # Buscar backdrop específico de Bootstrap
                    backdrop = self.driver.find_elements(
                        By.XPATH,
                        "//div[contains(@class, 'modal-backdrop')] | //div[contains(@class, 'modal-backdrop-show')] | //div[contains(@class, 'fade') and contains(@class, 'show')]"
                    )
                    if backdrop:
                        self.logger.info("   🖱️ Haciendo click en backdrop...")
                        # Click directo en el backdrop usando JavaScript
                        self.driver.execute_script("arguments[0].click();", backdrop[0])
                        time.sleep(2)
                        if not self._check_modal_open():
                            self.logger.info("   ✅ Modal cerrado (click en backdrop)")
                            return True
                except Exception as e:
                    self.logger.warning(f"   ⚠️ Error con backdrop: {str(e)}")
                
                # Método 4: Forzar cierre con JavaScript (específico para ngb-modal-window)
                try:
                    self.logger.info("   🔧 Forzando cierre con JavaScript...")
                    self.driver.execute_script("""
                        // Cerrar todos los modales ngb-modal-window
                        var modals = document.querySelectorAll('ngb-modal-window.modal.show, .modal.show, ngb-modal-window.d-block');
                        modals.forEach(function(modal) {
                            modal.classList.remove('show', 'd-block', 'fade');
                            modal.style.display = 'none';
                            modal.setAttribute('aria-hidden', 'true');
                            modal.setAttribute('aria-modal', 'false');
                        });
                        
                        // Remover todos los backdrops
                        var backdrops = document.querySelectorAll('.modal-backdrop, .modal-backdrop-show, .modal-backdrop.fade.show');
                        backdrops.forEach(function(backdrop) {
                            backdrop.remove();
                        });
                        
                        // Remover clase modal-open del body
                        document.body.classList.remove('modal-open');
                        document.body.style.overflow = '';
                        document.body.style.paddingRight = '';
                    """)
                    time.sleep(2)
                    if not self._check_modal_open():
                        self.logger.info("   ✅ Modal cerrado (JavaScript forzado)")
                        return True
                except Exception as e:
                    self.logger.warning(f"   ⚠️ Error con JavaScript: {str(e)}")
                
                # Método 5: Click fuera usando coordenadas (último recurso)
                try:
                    # Obtener tamaño de la ventana
                    window_size = self.driver.get_window_size()
                    # Click en la esquina superior izquierda
                    self.driver.execute_script(f"document.elementFromPoint(50, 50).click();")
                    time.sleep(2)
                    if not self._check_modal_open():
                        self.logger.info("   ✅ Modal cerrado (click en coordenadas)")
                        return True
                except Exception as e:
                    self.logger.warning(f"   ⚠️ Error con coordenadas: {str(e)}")
                
            except Exception as e:
                self.logger.warning(f"   ⚠️ Error en intento {attempt + 1}: {str(e)}")
        
        # Verificación final
        if self._check_modal_open():
            self.logger.error("   ❌ No se pudo cerrar el modal después de todos los intentos")
            # Último intento desesperado: remover todo con JavaScript
            try:
                self.driver.execute_script("""
                    document.querySelectorAll('ngb-modal-window, .modal').forEach(m => {
                        m.remove();
                    });
                    document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                    document.body.classList.remove('modal-open');
                """)
                time.sleep(1)
            except:
                pass
            return False
        else:
            self.logger.info("   ✅ Modal cerrado exitosamente")
            return True
    
    def _check_modal_open(self):
        """Verifica si el modal sigue abierto y visible - Específico para ngb-modal-window"""
        try:
            # Buscar específicamente ngb-modal-window con clase show
            modals = self.driver.find_elements(
                By.XPATH,
                "//ngb-modal-window[contains(@class, 'show')] | //ngb-modal-window[contains(@class, 'd-block')] | //div[contains(@class, 'modal') and contains(@class, 'show')] | //div[contains(@class, 'p-dialog') and not(contains(@style, 'display: none'))]"
            )
            
            # Verificar que al menos uno esté visible
            for modal in modals:
                try:
                    if modal.is_displayed():
                        # Verificar también que tenga las clases correctas
                        classes = modal.get_attribute('class') or ''
                        if 'show' in classes or 'd-block' in classes:
                            return True
                except:
                    continue
            
            # También verificar si hay backdrop (indica que hay modal abierto)
            try:
                backdrops = self.driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class, 'modal-backdrop')] | //div[contains(@class, 'modal-backdrop-show')]"
                )
                for backdrop in backdrops:
                    try:
                        if backdrop.is_displayed():
                            return True
                    except:
                        continue
            except:
                pass
            
            return False
        except:
            return False
    
    def _check_and_close_success_popup(self):
        """Verifica si hay popup de éxito (swal2) y lo cierra"""
        try:
            # Buscar popup de éxito de SweetAlert2
            success_popup = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'swal2-popup') and contains(@class, 'swal2-icon-success')]"
            )
            
            if success_popup:
                self.logger.info("   ✅ Popup de éxito detectado")
                
                # Buscar el botón OK o confirmar
                ok_button = None
                try:
                    ok_button = self.driver.find_element(
                        By.XPATH,
                        "//button[contains(@class, 'swal2-confirm')] | //button[contains(., 'OK')]"
                    )
                    ok_button.click()
                    time.sleep(1)
                    self.logger.info("   ✅ Popup de éxito cerrado")
                    return True
                except:
                    # Si no hay botón, intentar click fuera del popup
                    try:
                        self.driver.execute_script("document.querySelector('.swal2-container').click();")
                        time.sleep(1)
                        self.logger.info("   ✅ Popup de éxito cerrado (click fuera)")
                        return True
                    except:
                        pass
            
            return False
        except Exception as e:
            self.logger.warning(f"   ⚠️ Error al verificar popup de éxito: {str(e)}")
            return False
    
    def _check_and_close_error_popup(self):
        """Verifica si hay popup de error (p-dialog) y lo cierra"""
        try:
            # Buscar popup de error (p-dialog con "Ups, tenemos el siguiente inconveniente")
            error_popup = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'p-dialog')] | //div[contains(@class, 'p-component') and contains(., 'Ups, tenemos el siguiente inconveniente')]"
            )
            
            if error_popup:
                self.logger.warning("   ⚠️ Popup de error detectado")
                
                # Intentar cerrar con el botón "Aceptar"
                try:
                    accept_button = self.driver.find_element(
                        By.XPATH,
                        "//button[contains(., 'Aceptar')] | //button[contains(@class, 'btn') and contains(@class, 'primary')]"
                    )
                    accept_button.click()
                    time.sleep(1)
                    self.logger.info("   ✅ Popup de error cerrado (botón Aceptar)")
                    return True
                except:
                    pass
                
                # Intentar cerrar con el botón X
                try:
                    close_button = self.driver.find_element(
                        By.XPATH,
                        "//button[contains(@class, 'p-dialog-header-close')] | //button[contains(@class, 'p-button') and contains(@class, 'p-dialog-header-close')]"
                    )
                    close_button.click()
                    time.sleep(1)
                    self.logger.info("   ✅ Popup de error cerrado (botón X)")
                    return True
                except:
                    pass
                
                # Intentar click fuera del popup
                try:
                    # Click en el overlay del dialog
                    overlay = self.driver.find_element(
                        By.XPATH,
                        "//div[contains(@class, 'p-dialog-mask')] | //div[contains(@class, 'p-component-overlay')]"
                    )
                    overlay.click()
                    time.sleep(1)
                    self.logger.info("   ✅ Popup de error cerrado (click fuera)")
                    return True
                except:
                    pass
            
            return False
        except Exception as e:
            self.logger.warning(f"   ⚠️ Error al verificar popup de error: {str(e)}")
            return False
    
    def _check_if_already_solved(self, row):
        """Verifica si la novedad ya está solucionada"""
        try:
            # Buscar si hay algún indicador de que ya está solucionada
            # Por ejemplo, si no hay botón "Solucionar" o si hay un mensaje diferente
            solve_buttons = row.find_elements(
                By.XPATH,
                ".//button[contains(@class, 'btn-success') and contains(., 'Solucionar')]"
            )
            
            if not solve_buttons:
                # Intentar buscar por title
                solve_buttons = row.find_elements(
                    By.XPATH,
                    ".//button[@title='Solucionar']"
                )
            
            if not solve_buttons:
                return True, "No se encontró botón Solucionar (probablemente ya está solucionada)"
            
            # Verificar si el botón está deshabilitado
            solve_button = solve_buttons[0]
            if not solve_button.is_enabled():
                return True, "Botón Solucionar está deshabilitado"
            
            # Verificar si el botón no es visible
            if not solve_button.is_displayed():
                return True, "Botón Solucionar no es visible"
            
            return False, None
            
        except Exception as e:
            self.logger.warning(f"   ⚠️ Error al verificar si está solucionada: {str(e)}")
            return False, None
    
    def _process_novedad(self, row, novedad_text, row_index):
        """Procesa una novedad específica"""
        try:
            self.logger.info(f"   📋 Procesando novedad: {novedad_text}")
            
            # IMPORTANTE: Cerrar cualquier modal abierto antes de empezar
            if self._check_modal_open():
                self.logger.warning("   ⚠️ Hay un modal abierto - Cerrando antes de continuar...")
                closed = self._close_modal_if_open()
                time.sleep(3)  # Esperar más tiempo
                
                # Verificar que realmente se cerró
                if self._check_modal_open():
                    self.logger.error("   ❌ No se pudo cerrar el modal anterior - Reintentando...")
                    # Reintentar cierre más agresivo
                    for i in range(3):
                        self._close_modal_if_open()
                        time.sleep(2)
                        if not self._check_modal_open():
                            break
                    
                    # Si aún está abierto, es un problema serio
                    if self._check_modal_open():
                        self.logger.error("   ❌ CRÍTICO: Modal no se puede cerrar - Saltando esta novedad")
                        return "error"
                else:
                    self.logger.info("   ✅ Modal anterior cerrado exitosamente")
            
            # Verificar si ya está solucionada
            is_solved, reason = self._check_if_already_solved(row)
            if is_solved:
                self.logger.info(f"   ⏭️  Novedad ya está solucionada: {reason}")
                return "already_solved"
            
            # Buscar el botón "Solucionar" en esta fila
            solve_button = None
            try:
                # Buscar el botón con el texto "Solucionar" o el ícono de guardar
                solve_button = row.find_element(
                    By.XPATH,
                    ".//button[contains(@class, 'btn-success') and contains(., 'Solucionar')]"
                )
            except NoSuchElementException:
                # Intentar buscar por el ícono
                try:
                    solve_button = row.find_element(
                        By.XPATH,
                        ".//button[@title='Solucionar']"
                    )
                except NoSuchElementException:
                    self.logger.warning(f"   ⚠️ No se encontró botón Solucionar en fila {row_index} - Saltando")
                    return "no_button"
            
            # Verificar que el botón esté habilitado
            if not solve_button.is_enabled():
                self.logger.info(f"   ⏭️  Botón Solucionar está deshabilitado - Novedad ya procesada")
                return "already_solved"
            
            self.logger.info("   ✅ Botón Solucionar encontrado y habilitado")
            
            # Hacer scroll al botón si es necesario
            self.driver.execute_script("arguments[0].scrollIntoView(true);", solve_button)
            time.sleep(1)
            
            # Hacer click en Solucionar
            self.logger.info("   🖱️ Haciendo click en 'Solucionar'...")
            try:
                solve_button.click()
                time.sleep(3)  # Esperar a que aparezca el modal
            except ElementClickInterceptedException:
                # Intentar con JavaScript click
                self.logger.warning("   ⚠️ Click normal falló, intentando con JavaScript...")
                self.driver.execute_script("arguments[0].click();", solve_button)
                time.sleep(3)
            
            # Buscar el botón "Si" en el modal
            self.logger.info("   Buscando botón 'Si' en el modal...")
            try:
                si_button = self.wait.until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//button[contains(@class, 'btn-success') and contains(., 'Si')]"
                    ))
                )
                self.logger.info("   ✅ Botón 'Si' encontrado")
                
                # Hacer scroll al botón
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", si_button)
                time.sleep(1)
                
                self.logger.info("   🖱️ Haciendo click en 'Si'...")
                try:
                    si_button.click()
                except (ElementClickInterceptedException, Exception) as e:
                    # Si el click falla, intentar con JavaScript
                    self.logger.warning(f"   ⚠️ Click normal falló ({str(e)}), intentando con JavaScript...")
                    self.driver.execute_script("arguments[0].click();", si_button)
                
                time.sleep(2)  # Esperar a que se desplieguen las opciones
                
            except TimeoutException:
                self.logger.error("   ❌ No se encontró el botón 'Si' en el modal - Cerrando modal")
                self._close_modal_if_open()
                return "error"
            
            # PASO 1: Escribir el mensaje de solución correspondiente en el campo "Solución"
            # Obtener el mensaje de solución para este tipo de novedad
            solution_text = self._get_solution_message(novedad_text)
            
            self.logger.info("   📝 PASO 1: Buscando campo 'Solución'...")
            try:
                # Esperar a que aparezcan los inputs
                time.sleep(2)
                
                # Buscar el input con maxlength="100" que está en el form-group con texto "Solución"
                solucion_input = None
                try:
                    # Buscar el div que contiene "Solución" y luego el input dentro
                    solucion_div = self.wait.until(
                        EC.presence_of_element_located((
                            By.XPATH,
                            "//div[contains(@class, 'form-group') and contains(., 'Solución')]"
                        ))
                    )
                    solucion_input = solucion_div.find_element(
                        By.XPATH,
                        ".//input[@type='text' and @maxlength='100']"
                    )
                except (TimeoutException, NoSuchElementException):
                    # Fallback: buscar directamente el input con maxlength="100"
                    try:
                        solucion_input = self.wait.until(
                            EC.presence_of_element_located((
                                By.XPATH,
                                "//input[@type='text' and @maxlength='100' and contains(@class, 'form-control')]"
                            ))
                        )
                    except TimeoutException:
                        self.logger.error("   ❌ No se encontró el campo 'Solución'")
                        self._close_modal_if_open()
                        return "error"
                
                self.logger.info("   ✅ Campo 'Solución' encontrado")
                
                # Escribir el mensaje de solución en el campo Solución
                self.logger.info(f"   ✍️ Escribiendo '{solution_text}' en el campo 'Solución'...")
                solucion_input.clear()
                solucion_input.send_keys(solution_text)
                time.sleep(1)
                
                # Verificar que se escribió correctamente
                written_text = solucion_input.get_attribute('value')
                if written_text != solution_text:
                    self.logger.warning(f"   ⚠️ Texto escrito no coincide. Esperado: '{solution_text}', Obtenido: '{written_text}'")
                    # Intentar de nuevo
                    solucion_input.clear()
                    solucion_input.send_keys(solution_text)
                    time.sleep(1)
                    written_text = solucion_input.get_attribute('value')
                
                self.logger.info(f"   ✅ Texto escrito correctamente en 'Solución': '{written_text}'")
                
            except Exception as e:
                self.logger.error(f"   ❌ Error en PASO 1: {str(e)}")
                self._close_modal_if_open()
                return "error"
            
            # PASO 2: Copiar el texto del campo "Direccion"
            self.logger.info("   📋 PASO 2: Buscando campo 'Direccion' para copiar su contenido...")
            try:
                # Buscar el label "Direccion"
                direccion_label = self.wait.until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//label[contains(@class, 'text-info') and contains(., 'Direccion')]"
                    ))
                )
                
                # Encontrar el input asociado (múltiples estrategias)
                direccion_input = None
                try:
                    direccion_input = direccion_label.find_element(
                        By.XPATH,
                        "./following-sibling::input"
                    )
                except NoSuchElementException:
                    try:
                        direccion_input = direccion_label.find_element(
                            By.XPATH,
                            "./parent::div//input"
                        )
                    except NoSuchElementException:
                        try:
                            direccion_input = direccion_label.find_element(
                                By.XPATH,
                                "../input"
                            )
                        except NoSuchElementException:
                            label_for = direccion_label.get_attribute('for')
                            if label_for:
                                direccion_input = self.driver.find_element(By.ID, label_for)
                            else:
                                raise NoSuchElementException("No se pudo encontrar el input de Direccion")
                
                self.logger.info("   ✅ Campo 'Direccion' encontrado")
                
                # Obtener el texto actual del campo Direccion
                direccion_text = direccion_input.get_attribute('value')
                self.logger.info(f"   📄 Texto en 'Direccion': '{direccion_text}'")
                
                if not direccion_text or direccion_text.strip() == "":
                    self.logger.warning("   ⚠️ El campo 'Direccion' está vacío")
                
                # Copiar el texto del campo Direccion (Ctrl+A, Ctrl+C)
                self.logger.info("   📋 Copiando texto del campo 'Direccion' (Ctrl+A, Ctrl+C)...")
                direccion_input.click()  # Asegurar que el campo tiene foco
                time.sleep(0.3)
                direccion_input.send_keys(Keys.CONTROL + "a")
                time.sleep(0.3)
                direccion_input.send_keys(Keys.CONTROL + "c")
                time.sleep(0.5)
                
                self.logger.info("   ✅ Texto copiado del campo 'Direccion'")
                
            except Exception as e:
                self.logger.error(f"   ❌ Error en PASO 2: {str(e)}")
                self._close_modal_if_open()
                return "error"
            
            # PASO 3: Pegar el texto copiado en el campo "Specify Address"
            self.logger.info("   📋 PASO 3: Buscando campo 'Specify Address' para pegar el texto copiado...")
            try:
                # Buscar el label "Specify Address"
                specify_address_label = self.wait.until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//label[contains(@class, 'text-info') and contains(., 'Specify Address')]"
                    ))
                )
                
                # Encontrar el input asociado (múltiples estrategias)
                specify_address_input = None
                try:
                    specify_address_input = specify_address_label.find_element(
                        By.XPATH,
                        "./following-sibling::input"
                    )
                except NoSuchElementException:
                    try:
                        specify_address_input = specify_address_label.find_element(
                            By.XPATH,
                            "./parent::div//input"
                        )
                    except NoSuchElementException:
                        try:
                            specify_address_input = specify_address_label.find_element(
                                By.XPATH,
                                "../input"
                            )
                        except NoSuchElementException:
                            label_for = specify_address_label.get_attribute('for')
                            if label_for:
                                specify_address_input = self.driver.find_element(By.ID, label_for)
                            else:
                                raise NoSuchElementException("No se pudo encontrar el input de Specify Address")
                
                self.logger.info("   ✅ Campo 'Specify Address' encontrado")
                
                # Pegar el texto copiado (Ctrl+V)
                self.logger.info("   📋 Pegando texto en el campo 'Specify Address' (Ctrl+V)...")
                specify_address_input.clear()
                specify_address_input.click()  # Asegurar que el campo tiene foco
                time.sleep(0.3)
                specify_address_input.send_keys(Keys.CONTROL + "v")
                time.sleep(1)
                
                # Verificar que se pegó correctamente
                pasted_text = specify_address_input.get_attribute('value')
                self.logger.info(f"   📄 Texto pegado en 'Specify Address': '{pasted_text}'")
                
                if pasted_text and pasted_text.strip() != "":
                    self.logger.info(f"   ✅ Texto pegado correctamente en 'Specify Address'")
                else:
                    self.logger.warning("   ⚠️ El texto pegado está vacío, pero continuando...")
                
            except Exception as e:
                self.logger.error(f"   ❌ Error en PASO 3: {str(e)}")
                self._close_modal_if_open()
                return "error"
            
            # PASO 4: Buscar y hacer click en el botón "GUARDAR SOLUCION"
            self.logger.info("   🔍 PASO 4: Buscando botón 'GUARDAR SOLUCION'...")
            try:
                # Hacer scroll hasta el final del modal para asegurar que el botón sea visible
                self.logger.info("   📜 Haciendo scroll hasta el final del modal...")
                try:
                    # Buscar el modal o el contenedor del modal
                    modal = self.driver.find_element(
                        By.XPATH,
                        "//div[contains(@class, 'modal')] | //div[contains(@class, 'modal-content')] | //div[contains(@class, 'modal-body')]"
                    )
                    # Hacer scroll hasta el final del modal
                    self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", modal)
                    time.sleep(1)
                    self.logger.info("   ✅ Scroll realizado en el modal")
                except Exception as e:
                    self.logger.warning(f"   ⚠️ No se pudo hacer scroll en el modal: {str(e)}")
                    # Intentar scroll general de la página
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                
                # Buscar el botón "GUARDAR SOLUCION"
                save_button = self.wait.until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//button[contains(@class, 'btn-success') and (contains(., 'GUARDAR SOLUCION') or contains(., 'GUARDAR') or @title='GUARDAR SOLUCION')]"
                    ))
                )
                self.logger.info("   ✅ Botón 'GUARDAR SOLUCION' encontrado")
                
                # Hacer scroll al botón para asegurar que sea visible
                self.logger.info("   📜 Haciendo scroll al botón 'GUARDAR SOLUCION'...")
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", save_button)
                time.sleep(1)
                
                # Verificar que el botón sea clickeable
                save_button = self.wait.until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[contains(@class, 'btn-success') and (contains(., 'GUARDAR SOLUCION') or contains(., 'GUARDAR') or @title='GUARDAR SOLUCION')]"
                    ))
                )
                
                # Hacer click en guardar
                self.logger.info("   🖱️ Haciendo click en 'GUARDAR SOLUCION'...")
                try:
                    save_button.click()
                except ElementClickInterceptedException:
                    # Si el click falla, intentar con JavaScript
                    self.logger.warning("   ⚠️ Click normal falló, intentando con JavaScript...")
                    self.driver.execute_script("arguments[0].click();", save_button)
                
                time.sleep(4)  # Esperar a que se procese (aumentado a 4 segundos)
                
                # PASO 5: Verificar resultado y cerrar popups
                self.logger.info("   🔍 Verificando resultado de la operación...")
                
                # Primero verificar si apareció el popup de éxito (swal2)
                # Si hay popup de éxito, el modal debería haberse cerrado automáticamente
                success_popup = self._check_and_close_success_popup()
                if success_popup:
                    time.sleep(2)  # Esperar a que se cierre el popup
                    # Verificar que el modal también se cerró
                    if self._check_modal_open():
                        self.logger.warning("   ⚠️ Popup de éxito cerrado pero modal sigue abierto - Cerrando modal...")
                        self._close_modal_if_open()
                    self.logger.info(f"   ✅ Novedad '{novedad_text}' procesada exitosamente - Popup de éxito detectado y cerrado")
                    return True
                
                # Si no hay popup de éxito, verificar si el modal sigue abierto
                modal_still_open = self._check_modal_open()
                if modal_still_open:
                    self.logger.warning("   ⚠️ El modal no se cerró automáticamente - Cerrando manualmente...")
                    # Intentar cerrar el modal de forma agresiva
                    closed = self._close_modal_if_open()
                    time.sleep(3)  # Esperar más tiempo después de cerrar
                    
                    # Verificar nuevamente si se cerró (múltiples verificaciones)
                    for i in range(3):
                        if not self._check_modal_open():
                            self.logger.info("   ✅ Modal cerrado exitosamente")
                            break
                        else:
                            if i < 2:
                                self.logger.warning(f"   ⚠️ Modal aún abierto, reintentando cierre (intento {i+2})...")
                                self._close_modal_if_open()
                                time.sleep(2)
                    
                    # Verificación final
                    if self._check_modal_open():
                        self.logger.error("   ❌ El modal no se pudo cerrar después de múltiples intentos")
                        # Intentar cerrar popup de error por si acaso
                        self._check_and_close_error_popup()
                    else:
                        self.logger.info("   ✅ Modal cerrado exitosamente después de reintentos")
                
                # Verificar si hay popup de error (después de cerrar el modal)
                error_popup = self._check_and_close_error_popup()
                if error_popup:
                    self.logger.warning("   ⚠️ Popup de error detectado y cerrado - Continuando con la siguiente novedad")
                    return "error"
                
                # Si no hay popup de éxito ni de error, asumir éxito
                self.logger.info(f"   ✅ Novedad '{novedad_text}' procesada (sin popup de confirmación)")
                return True
                
            except TimeoutException:
                self.logger.error("   ❌ No se encontró el botón 'GUARDAR SOLUCION'")
                self._close_modal_if_open()
                return "error"
            except Exception as e:
                self.logger.error(f"   ❌ Error al hacer click en 'GUARDAR SOLUCION': {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
                self._close_modal_if_open()
                return "error"
            
        except Exception as e:
            self.logger.error(f"   ❌ Error al procesar novedad: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            self._close_modal_if_open()
            return "error"
    
    def run(self):
        """Ejecuta el bot principal"""
        try:
            _configure_utf8_stdio()
            
            self.logger.info("="*80)
            self.logger.info("🤖 INICIANDO BOT DE NOVEDADES")
            self.logger.info("="*80)
            self.logger.info(f"   Novedades objetivo: {', '.join(self.TARGET_NOVEDADES)}")
            self.logger.info("   Mensajes de solución configurados:")
            for novedad_type, messages in self.SOLUTION_MESSAGES.items():
                self.logger.info(f"     - {novedad_type}: {len(messages)} mensaje(s)")
            self.logger.info("="*80)
            
            # Inicializar navegador
            self._init_driver()
            
            # Login
            if not self._login():
                raise Exception("No se pudo iniciar sesión")
            
            # Navegar a Novedades
            if not self._navigate_to_novelties():
                raise Exception("No se pudo navegar a Novedades")
            
            # Configurar paginación a 1000 para ver todas las novedades
            self._set_pagination_to_1000()
            
            # Procesar novedades
            self.logger.info("")
            self.logger.info("="*60)
            self.logger.info("🔍 BUSCANDO NOVEDADES")
            self.logger.info("="*60)
            
            # Buscar todas las filas de la tabla
            rows = self._find_novelties_table_rows()
            
            if not rows:
                self.logger.warning("⚠️ No se encontraron filas en la tabla")
                return
            
            # Iterar sobre cada fila
            for idx, row in enumerate(rows):
                try:
                    # Extraer el texto de la novedad
                    novedad_text = self._extract_novedad_text(row)
                    
                    if novedad_text:
                        self.stats['total_encontradas'] += 1
                        self.logger.info("")
                        self.logger.info(f"{'='*60}")
                        self.logger.info(f"📌 Novedad encontrada ({self.stats['total_encontradas']}): {novedad_text}")
                        self.logger.info(f"{'='*60}")
                        
                        # Procesar la novedad
                        result = self._process_novedad(row, novedad_text, idx)
                        
                        if result is True:
                            self.stats['procesadas'] += 1
                            self.logger.info(f"✅ Novedad procesada exitosamente ({self.stats['procesadas']}/{self.stats['total_encontradas']})")
                        elif result == "already_solved":
                            self.logger.info(f"⏭️  Novedad ya estaba solucionada - Continuando con la siguiente")
                            # No incrementar errores, solo contar como saltada
                        elif result == "no_button":
                            self.logger.warning(f"⚠️  No se encontró botón Solucionar - Continuando con la siguiente")
                            self.stats['errores'] += 1
                        elif result == "error":
                            self.stats['errores'] += 1
                            self.logger.error(f"❌ Error al procesar novedad ({self.stats['errores']} errores) - Continuando con la siguiente")
                        else:
                            self.stats['errores'] += 1
                            self.logger.error(f"❌ Error desconocido al procesar novedad ({self.stats['errores']} errores) - Continuando con la siguiente")
                        
                        # Pausa entre novedades
                        time.sleep(2)
                    else:
                        self.stats['saltadas'] += 1
                        
                except Exception as e:
                    self.stats['errores'] += 1
                    self.logger.error(f"❌ Error al procesar fila {idx}: {str(e)}")
                    self.logger.error(f"   Continuando con la siguiente novedad...")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    # Asegurar que el modal esté cerrado si existe
                    try:
                        close_buttons = self.driver.find_elements(
                            By.XPATH,
                            "//button[contains(@class, 'close')] | //button[@aria-label='Close'] | //button[contains(., 'Cerrar')]"
                        )
                        if close_buttons:
                            close_buttons[0].click()
                            time.sleep(1)
                    except:
                        pass
                    continue
            
            # Mostrar estadísticas finales
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("📊 ESTADÍSTICAS FINALES")
            self.logger.info("="*80)
            self.logger.info(f"   Total encontradas: {self.stats['total_encontradas']}")
            self.logger.info(f"   Procesadas exitosamente: {self.stats['procesadas']}")
            self.logger.info(f"   Errores: {self.stats['errores']}")
            self.logger.info(f"   Saltadas: {self.stats['saltadas']}")
            self.logger.info("="*80)
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error fatal: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise
            
        finally:
            # Cerrar navegador
            if self.driver:
                self.logger.info("Cerrando navegador...")
                self.driver.quit()


class Command(BaseCommand):
    help = 'Bot para automatizar solución de novedades en Dropi'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--headless',
            action='store_true',
            help='Ejecutar navegador en modo headless (sin interfaz gráfica)',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='ID del usuario para cargar credenciales desde BD',
        )
        parser.add_argument(
            '--dropi-label',
            type=str,
            default='reporter',
            help='(Deprecated) Ya no se usa. Las credenciales están en la tabla users directamente.',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email de Dropi (sobrescribe user_id)',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password de Dropi (sobrescribe user_id)',
        )
        parser.add_argument(
            '--browser',
            type=str,
            default='edge',
            choices=['edge', 'chrome', 'brave', 'firefox'],
            help='Navegador a usar (default: edge)',
        )
    
    def handle(self, *args, **options):
        _configure_utf8_stdio()
        
        headless = options.get('headless', False)
        user_id = options.get('user_id')
        dropi_label = options.get('dropi_label', 'reporter')
        email = options.get('email')
        password = options.get('password')
        browser = options.get('browser', 'edge')
        
        # En modo local, las credenciales están hardcodeadas
        # No es necesario validar argumentos
        
        # Crear y ejecutar bot
        bot = NovedadReporterBot(
            headless=headless,
            user_id=user_id,
            dropi_label=dropi_label,
            email=email,
            password=password,
            browser=browser
        )
        
        try:
            bot.run()
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Bot completado. Procesadas: {bot.stats["procesadas"]}, Errores: {bot.stats["errores"]}'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error al ejecutar el bot: {str(e)}')
            )
            raise
