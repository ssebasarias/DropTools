"""
Auth Manager - Gestión de autenticación en Dropi

Este módulo centraliza el login y la gestión de sesiones, permitiendo
compartir la sesión entre todos los módulos del bot.
"""

import os
import time
from datetime import datetime
from pathlib import Path
from django.conf import settings
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException as SeleniumTimeoutException
from selenium.common.exceptions import NoSuchElementException
from core.models import User


class AuthManager:
    """
    Clase responsable de la autenticación en Dropi.
    Maneja login, recuperación de credenciales y verificación de sesión.
    
    Prioridad de carga de credenciales:
    1. Argumentos directos (email/password)
    2. Tabla Users (campos dropi_email/dropi_password)
    3. Variables de entorno (solo si no hay user_id)
    """
    
    # Landing para elegir país (Colombia); luego el botón lleva a login
    LANDING_URL = "https://dropi.co/inicio-de-sesion/"
    # Misma URL que novedadreporter (funciona con proxy y send_keys)
    LOGIN_URL = "https://app.dropi.co/login"
    LOGIN_URL_AUTH = "https://app.dropi.co/auth/login"
    DROPI_URL = LOGIN_URL

    def __init__(self, driver, user_id, logger):
        """
        Inicializa el AuthManager
        
        Args:
            driver: Instancia del WebDriver (compartida)
            user_id: ID del usuario Django
            logger: Logger configurado
        """
        self.driver = driver
        self.user_id = user_id
        self.logger = logger
        # 30s: con proxy la página de Dropi puede tardar más en cargar o mostrar el formulario
        self.wait = WebDriverWait(driver, 30)
        self.email = None
        self.password = None
        self.session_active = False
        
    def load_credentials(self, direct_email=None, direct_password=None):
        """
        Carga credenciales desde múltiples fuentes según prioridad.
        
        Args:
            direct_email: Email directo (máxima prioridad)
            direct_password: Password directo (máxima prioridad)
        """
        # 1. Credenciales directas (CLI/Argumentos)
        if direct_email and direct_password:
            self.email = direct_email
            self.password = direct_password
            if self.logger:
                self.logger.info("🔑 Credenciales cargadas: Directas (Argumentos)")
            return

        # 2. Base de Datos (Tabla Users)
        if not self.user_id:
            # Fallback a variables de entorno solo si no hay user_id
            env_email = os.getenv("DROPI_EMAIL")
            env_pass = os.getenv("DROPI_PASSWORD")
            if env_email and env_pass:
                self.email = env_email
                self.password = env_pass
                if self.logger:
                    self.logger.warning("⚠️ Credenciales cargadas de Environment Variables (Sin User ID)")
                return
            raise ValueError("Se requiere user_id para cargar credenciales de BD")
            
        try:
            user = User.objects.get(id=self.user_id)
            if self.logger:
                self.logger.info(f"[DEBUG] Usuario cargado: {user.email} (ID: {user.id})")
            
            # Prioridad: User fields (Tabla 'users')
            if user.dropi_email and user.dropi_password:
                self.email = user.dropi_email
                self.password = user.get_dropi_password_plain()
                if self.logger:
                    self.logger.info(f"🔑 Credenciales cargadas de User Table: {self.email}")
                return
            else:
                error_msg = (
                    f"❌ NO SE ENCONTRARON CREDENCIALES para el usuario ID {self.user_id} ({user.email}).\n"
                    f"   El sistema buscó en:\n"
                    f"   1. Argumentos directos (--email)\n"
                    f"   2. Tabla Users (campos dropi_email/dropi_password)\n"
                    f"   \n"
                    f"   SOLUCIÓN: Configure las credenciales Dropi en el perfil del usuario."
                )
                if self.logger:
                    self.logger.error(error_msg)
                raise ValueError(error_msg)
                
        except User.DoesNotExist:
            raise ValueError(f"Usuario ID {self.user_id} no existe")

    def _wait_login_page_visible(self, timeout=60):
        """
        Espera hasta que aparezca algún elemento del formulario de login (email o password).
        Para conexiones lentas o proxy: no sigue hasta que la página haya renderizado algo.
        """
        if self.logger:
            self.logger.info(f"   Esperando hasta {timeout}s a que cargue la página de login...")
        selectors = [
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']"),
        ]
        start = time.time()
        while time.time() - start < timeout:
            for by, value in selectors:
                try:
                    el = self.driver.find_element(by, value)
                    if el.is_displayed():
                        elapsed = int(time.time() - start)
                        if self.logger:
                            self.logger.info(f"   Página de login visible tras {elapsed}s (elemento: {by}={value!r})")
                        return
                except NoSuchElementException:
                    continue
            time.sleep(2)
        raise SeleniumTimeoutException(
            f"La página de login no mostró ningún campo en {timeout}s (¿conexión lenta o bloqueo?)"
        )

    def _fill_input_instant(self, element, value):
        """
        Rellena un input de forma instantánea vía JavaScript para evitar que la página
        cambie o recargue mientras se escribe (send_keys es lento y puede quedar a medias).
        Dispara input/change para que frameworks tipo React detecten el valor.
        """
        if not value:
            return
        self.driver.execute_script(
            """
            var el = arguments[0];
            var val = arguments[1];
            el.focus();
            el.value = val;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            """
           ,
            element,
            value,
        )

    def _wait_email_input(self):
        """
        Espera hasta que aparezca el campo de email probando varios selectores
        (Dropi puede ser SPA o cambiar atributos; con proxy la página puede tardar más).
        """
        selectors = [
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[name='email']"),
            (By.XPATH, "//input[@type='email']"),
            (By.XPATH, "//input[contains(@placeholder,'mail') or contains(@placeholder,'Mail')]"),
        ]
        last_error = None
        for by, value in selectors:
            try:
                el = WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_element_located((by, value))
                )
                if self.logger:
                    self.logger.info(f"   Campo email encontrado con selector: {by}={value!r}")
                return el
            except SeleniumTimeoutException as e:
                last_error = e
                continue
        raise last_error or SeleniumTimeoutException("Campo email no encontrado con ningún selector")

    def _navigate_to_login_colombia(self, timeout=60):
        """
        Paso previo al login: ir a la landing de Dropi, hacer clic en el botón Colombia
        y verificar que estamos en https://app.dropi.co/auth/login (login vinculado a Colombia).
        Si ya estamos en auth/login, no hace nada.
        """
        if "app.dropi.co/auth/login" in (self.driver.current_url or ""):
            if self.logger:
                self.logger.info("0) Ya en página de login Colombia, continuando...")
            return
        if self.logger:
            self.logger.info("0) Abriendo landing Dropi (inicio de sesión)...")
        self.driver.get(self.LANDING_URL)
        if self.logger:
            self.logger.info(f"   URL cargada: {self.driver.current_url}")
        # Esperar a que aparezca el enlace/botón de Colombia (href a app.dropi.co/auth/login)
        wait_landing = WebDriverWait(self.driver, timeout)
        colombia_link = wait_landing.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'a[href="https://app.dropi.co/auth/login"]'
            ))
        )
        if self.logger:
            self.logger.info("   Clic en botón Colombia...")
        current_handles = set(self.driver.window_handles)
        colombia_link.click()
        time.sleep(2)
        # Si abrió nueva pestaña (target="_blank"), cambiar a ella
        new_handles = set(self.driver.window_handles) - current_handles
        if new_handles:
            self.driver.switch_to.window(new_handles.pop())
        # Esperar a estar realmente en la página de login
        wait_landing.until(lambda d: "app.dropi.co/auth/login" in (d.current_url or ""))
        if self.logger:
            self.logger.info(f"   En página de login Colombia: {self.driver.current_url}")

    def login(self):
        """
        Ejecuta el flujo de login completo en Dropi.
        
        Returns:
            bool: True si el login fue exitoso, False en caso contrario
        """
        if not self.email or not self.password:
            if self.logger:
                self.logger.error("❌ Credenciales no cargadas. Llama a load_credentials() primero.")
            return False
        
        try:
            if self.logger:
                self.logger.info("="*60)
                self.logger.info("🔐 INICIANDO PROCESO DE LOGIN")
                self.logger.info("="*60)
            # Modo directo (DROPI_LOGIN_DIRECT=1): misma URL que novedadreporter (app.dropi.co/login).
            # Si no, va a landing y clic Colombia (termina en app.dropi.co/auth/login).
            use_direct = os.environ.get("DROPI_LOGIN_DIRECT", "").strip().lower() in ("1", "true", "yes")
            if use_direct:
                if self.logger:
                    self.logger.info("0) Modo directo: yendo a app.dropi.co/login (igual que novedadreporter)...")
                self.driver.get(self.LOGIN_URL)
                if self.logger:
                    self.logger.info(f"   URL cargada: {self.driver.current_url}")
                # Misma espera que novedadreporter para que la página cargue por completo
                if self.logger:
                    self.logger.info("   ⏳ Esperando 8s a que la página cargue (como novedadreporter)...")
                time.sleep(8)
            else:
                self._navigate_to_login_colombia(timeout=60)
            # Esperar hasta que aparezca el formulario (email o password).
            if self.logger:
                self.logger.info("1) Esperando formulario de login...")
            self._wait_login_page_visible(timeout=60)
            time.sleep(2)
            
            # 2. Rellenar con send_keys (igual que novedadreporter); el relleno por JS no actualiza el state en Dropi.
            if self.logger:
                self.logger.info("2) Buscando campo de email...")
            email_input = self._wait_email_input()
            if self.logger:
                self.logger.info("   Campo email encontrado, escribiendo email...")
            email_input.clear()
            email_input.send_keys(self.email)
            time.sleep(1)
            if self.logger:
                self.logger.info("   Email ingresado")
            
            if self.logger:
                self.logger.info("   Buscando campo de password...")
            password_input = self.driver.find_element(By.NAME, "password")
            if self.logger:
                self.logger.info("   Campo password encontrado, escribiendo password...")
            password_input.clear()
            password_input.send_keys(self.password)
            time.sleep(1)
            if self.logger:
                self.logger.info("   Password ingresado")
            
            # 3. Enviar formulario (ENTER)
            if self.logger:
                self.logger.info("   Presionando ENTER para enviar...")
            password_input.send_keys(Keys.RETURN)
            if self.logger:
                self.logger.info("   Formulario enviado")
            
            # 4. Esperar validación (token o redirección)
            if self.logger:
                self.logger.info("3) Esperando validación (token o redirección)...")
            self.wait.until(
                lambda d: d.execute_script("return !!localStorage.getItem('DROPI_token')") or "/dashboard" in d.current_url
            )
            if self.logger:
                self.logger.info(f"   Validación exitosa - URL actual: {self.driver.current_url}")
            
            # 5. Espera adicional para carga completa del dashboard
            if self.logger:
                self.logger.info("   Esperando 15s para carga completa del dashboard...")
            time.sleep(15)
            if self.logger:
                self.logger.info("   Espera completada")
            
            self.session_active = True
            if self.logger:
                self.logger.info("="*60)
                self.logger.info("✅ LOGIN EXITOSO")
                self.logger.info("="*60)
            return True
            
        except Exception as e:
            self.session_active = False
            _screenshot_path = self._save_login_failure_screenshot()
            
            # Detectar si es un error de bloqueo de automatización
            if self._is_automation_blocked_error(e):
                self._handle_blocked_proxy_during_login(e)
            
            if self.logger:
                self.logger.error("="*60)
                self.logger.error("❌ LOGIN FALLIDO")
                self.logger.error("="*60)
                self.logger.error(f"Error: {type(e).__name__}: {e}")
                if _screenshot_path:
                    self.logger.error(f"📸 Captura guardada: {_screenshot_path}")
                try:
                    self.logger.error(f"URL actual: {self.driver.current_url}")
                    title = self.driver.title or "(vacío)"
                    ready = self.driver.execute_script("return document.readyState") or "?"
                    self.logger.error(f"Título página: {title} | readyState: {ready}")
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text[:400].replace("\n", " ").strip()
                    self.logger.error(f"Contenido de pantalla: {body_text or '(vacío)'}")
                except Exception as _e:
                    if self.logger:
                        self.logger.error(f"No se pudo leer estado de página: {_e}")
                import traceback
                self.logger.error(traceback.format_exc())
            return False
    
    def _is_automation_blocked_error(self, e):
        """Indica si el error sugiere que el proxy fue bloqueado por detección de automatización."""
        msg = (getattr(e, 'msg', None) or getattr(e, 'args', [None])[0] or str(e)).lower()
        # Palabras clave que indican bloqueo de automatización
        blocked_keywords = [
            'automation', 'automated', 'bot', 'blocked', 'forbidden', '403',
            'access denied', 'suspicious', 'detected', 'captcha', 'verification',
            'unusual traffic', 'automated queries', 'robot', 'crawler'
        ]
        # También verificar contenido de la página si es posible
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            if any(kw in body_text for kw in blocked_keywords):
                return True
        except Exception:
            pass
        return any(kw in msg for kw in blocked_keywords)
    
    def _get_current_proxy_id(self):
        """Obtiene el ID del proxy asignado al usuario actual."""
        from core.models import UserProxyAssignment
        try:
            assignment = UserProxyAssignment.objects.select_related('proxy').get(user_id=self.user_id)
            return assignment.proxy_id
        except UserProxyAssignment.DoesNotExist:
            return None
    
    def _handle_blocked_proxy_during_login(self, error):
        """Marca un proxy como bloqueado cuando se detecta error de automatización durante el login."""
        proxy_id = self._get_current_proxy_id()
        if not proxy_id:
            return
        
        from core.services.proxy_allocator_service import mark_proxy_blocked
        
        error_msg = str(error)
        reason = f"Bloqueo detectado durante login: {error_msg[:200]}"
        
        if self.logger:
            self.logger.error(f"🚫 Detectado bloqueo de automatización durante login en proxy id={proxy_id}. Marcando como bloqueado...")
        
        try:
            migrated_count = mark_proxy_blocked(proxy_id, reason=reason)
            if self.logger:
                if migrated_count is not None:
                    self.logger.info(f"✅ Proxy id={proxy_id} marcado como bloqueado. {migrated_count} usuarios migrados automáticamente.")
                else:
                    self.logger.warning(f"⚠️ No se pudo marcar proxy id={proxy_id} como bloqueado o ya estaba bloqueado.")
        except Exception as e:
            if self.logger:
                self.logger.exception(f"❌ Error al marcar proxy id={proxy_id} como bloqueado: {e}")

    def _save_login_failure_screenshot(self):
        """
        Guarda una captura de pantalla cuando falla el login (para ver captcha, bloqueo, etc.).
        Ruta: backend/results/screenshots/login_fail_YYYYMMDD_HHMMSS_user{N}.png
        Con Docker (volume ./results:/app/backend/results): ver en results/screenshots/ en el host.
        """
        try:
            screenshots_dir = Path(settings.BASE_DIR) / "results" / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"login_fail_{ts}_user{self.user_id}.png"
            path = screenshots_dir / filename
            self.driver.save_screenshot(str(path))
            return str(path)
        except Exception as e:
            if self.logger:
                self.logger.warning(f"No se pudo guardar captura de login: {e}")
            return None

    def check_session(self):
        """
        Verifica si la sesión sigue activa.
        
        Returns:
            bool: True si la sesión está activa, False si expiró
        """
        try:
            # Verificar token en localStorage o URL de login
            token_exists = self.driver.execute_script("return !!localStorage.getItem('DROPI_token')")
            is_login_page = "/login" in self.driver.current_url
            
            if not token_exists or is_login_page:
                self.session_active = False
                if self.logger:
                    self.logger.warning("⚠️ Sesión expirada detectada")
                return False
            
            self.session_active = True
            return True
        except Exception:
            # Si hay error al verificar, asumir que está expirada
            self.session_active = False
            return False
    
    def is_session_active(self):
        """Retorna el estado de la sesión"""
        return self.session_active
    
    def relogin(self):
        """
        Reloguea si la sesión expiró.
        
        Returns:
            bool: True si el relogin fue exitoso
        """
        if self.logger:
            self.logger.info("="*60)
            self.logger.info("🔄 RELOGUEANDO DESPUÉS DE EXPIRACIÓN")
            self.logger.info("="*60)
        
        return self.login()
