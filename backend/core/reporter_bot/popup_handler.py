"""
Popup Handler - Manejo de popups y alertas

Este módulo se encarga de detectar y manejar los diferentes tipos de popups
que pueden aparecer durante el proceso de reporte:
1. "Orden ya tiene un caso" → Click en "Cancelar"
2. "¡Oops! Aún no es posible" → Click en "Aceptar"
3. Alert de tiempo de espera
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException


class PopupHandler:
    """
    Módulo encargado de detectar y manejar popups durante el proceso de reporte.
    """
    
    def __init__(self, driver, logger):
        """
        Inicializa el popup handler
        
        Args:
            driver: WebDriver compartido
            logger: Logger configurado
        """
        self.driver = driver
        self.logger = logger
        self.wait = WebDriverWait(driver, 5)
    
    def handle_existing_case_popup(self):
        """
        Maneja los popups que pueden aparecer al intentar crear una consulta.
        
        Returns:
            dict con 'found' (bool) y 'type' (str) del popup encontrado
        """
        try:
            time.sleep(1)  # Esperar un poco para ver si aparece algún popup
            self.logger.info("   Verificando si hay popups...")
            
            # TIPO 1: Popup "Orden ya tiene un caso"
            popup_result = self._handle_existing_case()
            if popup_result['found']:
                return popup_result
            
            # TIPO 2: Popup "¡Oops! Aún no es posible"
            popup_result = self._handle_invalid_state()
            if popup_result['found']:
                return popup_result
            
            # No se encontró ningún popup
            self.logger.info("   ✅ No hay popups - Continuando normalmente")
            return {'found': False, 'type': None}
                
        except Exception as e:
            self.logger.error(f"   ❌ Error al manejar popups: {str(e)}")
            # Intentar cerrar cualquier popup visible como último recurso
            self._close_any_visible_popup()
            return {'found': False, 'type': None}
    
    def _handle_existing_case(self):
        """Maneja popup 'Orden ya tiene un caso'"""
        try:
            popup_caso_existente = self.driver.find_element(
                By.XPATH,
                "//div[contains(@class, 'swal2-popup') and ("
                "  .//h2[contains(text(), 'Orden ya tiene un caso')] or "
                "  .//h2[contains(text(), 'Order already has a case')] or "
                "  .//h2[contains(text(), 'Order has an existing case')] or "
                "  .//h2[contains(text(), 'Existing case')]"
                ")]"
            )
            
            if popup_caso_existente.is_displayed():
                self.logger.warning("⚠️  POPUP: ORDEN YA TIENE UN CASO ABIERTO")
                
                cancel_button = self.driver.find_element(By.CSS_SELECTOR, "button.swal2-cancel")
                try:
                    cancel_button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", cancel_button)
                
                # Esperar a que el popup desaparezca
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.swal2-container"))
                    )
                except Exception:
                    pass
                
                time.sleep(0.5)
                self.logger.info("   ✅ Popup cerrado exitosamente")
                return {'found': True, 'type': 'caso_existente'}
        except NoSuchElementException:
            pass
        
        return {'found': False, 'type': None}
    
    def _handle_invalid_state(self):
        """Maneja popup '¡Oops! Aún no es posible'"""
        try:
            popup_estado_invalido = self.driver.find_element(
                By.XPATH,
                "//div[contains(@class, 'p-dialog') and ("
                "  .//h2[contains(text(), '¡Oops! Aún no es posible')] or "
                "  .//h2[contains(text(), 'Oops! Not possible yet')] or "
                "  .//h2[contains(text(), 'Not possible yet')] or "
                "  contains(., 'not allow us to initiate a conversation')"
                ")]"
            )
            
            if popup_estado_invalido.is_displayed():
                self.logger.warning("⚠️  POPUP: ESTADO NO PERMITE CONVERSACIÓN")
                
                # Buscar botón Aceptar
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
                    except Exception:
                        continue
                
                if accept_button:
                    try:
                        accept_button.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", accept_button)
                    
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.p-dialog-mask"))
                        )
                    except Exception:
                        pass
                    
                    time.sleep(0.5)
                    self.logger.info("   ✅ Popup cerrado exitosamente")
                    return {'found': True, 'type': 'estado_invalido'}
                else:
                    # Intentar cerrar por la X
                    try:
                        close_button = self.driver.find_element(
                            By.CSS_SELECTOR,
                            "button.p-dialog-header-close"
                        )
                        close_button.click()
                        time.sleep(2)
                        self.logger.info("   ✅ Popup cerrado por la X")
                        return {'found': True, 'type': 'estado_invalido'}
                    except Exception:
                        pass
        except NoSuchElementException:
            pass
        
        return {'found': False, 'type': None}
    
    def _close_any_visible_popup(self):
        """Intenta cerrar cualquier popup visible como último recurso"""
        try:
            # Intentar botones de SweetAlert2
            cancel_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.swal2-cancel, button.swal2-confirm")
            for btn in cancel_buttons:
                if btn.is_displayed():
                    try:
                        btn.click()
                        time.sleep(1)
                        self.logger.info("   ✅ Popup cerrado (SweetAlert2)")
                        return
                    except Exception:
                        pass
            
            # Intentar botones de PrimeNG Dialog
            dialog_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'p-dialog-header-close')]")
            for btn in dialog_buttons:
                if btn.is_displayed():
                    try:
                        btn.click()
                        time.sleep(1)
                        self.logger.info("   ✅ Popup cerrado (PrimeNG Dialog)")
                        return
                    except Exception:
                        pass
        except Exception:
            pass
    
    def check_wait_time_alert(self):
        """
        Verifica si aparece el alert que indica que se debe esperar un día sin movimiento
        
        Returns:
            True si el alert está presente, False en caso contrario
        """
        try:
            alert = self.driver.find_element(
                By.XPATH,
                "//app-alert//p[contains(text(), 'Debes esperar al menos un día sin movimiento para iniciar una conversación sobre la orden')]"
            )
            return alert.is_displayed()
        except NoSuchElementException:
            return False
        except Exception:
            return False
