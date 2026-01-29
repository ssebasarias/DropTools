"""
Auth Manager - Gestión de autenticación en Dropi

Este módulo centraliza el login y la gestión de sesiones, permitiendo
compartir la sesión entre todos los módulos del bot.
"""

import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
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
    
    DROPI_URL = "https://app.dropi.co/login"
    
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
        self.wait = WebDriverWait(driver, 15)
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
            
            # 1. Abrir página de login
            if self.logger:
                self.logger.info("1) Abriendo página de login...")
            self.driver.get(self.DROPI_URL)
            if self.logger:
                self.logger.info(f"   URL cargada: {self.driver.current_url}")
            time.sleep(3)
            
            # 2. Buscar y llenar campo de email
            if self.logger:
                self.logger.info("2) Buscando campo de email...")
            email_input = self.wait.until(
                EC.visibility_of_element_located((By.NAME, "email"))
            )
            if self.logger:
                self.logger.info("   Campo email encontrado")
                self.logger.info(f"   Escribiendo email: {self.email}")
            email_input.clear()
            email_input.send_keys(self.email)
            time.sleep(1)
            if self.logger:
                self.logger.info("   Email ingresado")
            
            # 3. Buscar y llenar campo de password
            if self.logger:
                self.logger.info("   Buscando campo de password...")
            password_input = self.driver.find_element(By.NAME, "password")
            if self.logger:
                self.logger.info("   Campo password encontrado")
                self.logger.info("   Escribiendo password...")
            password_input.clear()
            password_input.send_keys(self.password)
            time.sleep(1)
            if self.logger:
                self.logger.info("   Password ingresado")
            
            # 4. Enviar formulario (ENTER)
            if self.logger:
                self.logger.info("   Presionando ENTER para enviar...")
            password_input.send_keys(Keys.RETURN)
            if self.logger:
                self.logger.info("   Formulario enviado")
            
            # 5. Esperar validación (token o redirección)
            if self.logger:
                self.logger.info("3) Esperando validación (token o redirección)...")
            self.wait.until(
                lambda d: d.execute_script("return !!localStorage.getItem('DROPI_token')") or "/dashboard" in d.current_url
            )
            if self.logger:
                self.logger.info(f"   Validación exitosa - URL actual: {self.driver.current_url}")
            
            # 6. Espera adicional para carga completa del dashboard
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
            if self.logger:
                self.logger.error("="*60)
                self.logger.error("❌ LOGIN FALLIDO")
                self.logger.error("="*60)
                self.logger.error(f"Error: {type(e).__name__}: {e}")
                try:
                    self.logger.error(f"URL actual: {self.driver.current_url}")
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text[:300].replace('\n', ' ')
                    self.logger.error(f"Contenido de pantalla: {body_text}")
                except:
                    pass
                import traceback
                self.logger.error(traceback.format_exc())
            return False

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
