"""
Report Form Handler - Manejo completo del formulario de reporte

Este módulo se encarga de:
1. Click en "Nueva Consulta"
2. Seleccionar tipo de consulta (Transportadora/Carrier)
3. Seleccionar motivo (Ordenes sin movimiento)
4. Click en "Siguiente"
5. Ingresar texto de observación
6. Iniciar conversación
"""

import random
import time
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException
)


class ReportFormHandler:
    """
    Módulo encargado de manejar el formulario completo de reporte.
    """
    
    # Textos de observación variados para evitar detección como spam
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
    
    def __init__(self, driver, logger):
        """
        Inicializa el form handler
        
        Args:
            driver: WebDriver compartido
            logger: Logger configurado
        """
        self.driver = driver
        self.logger = logger
        self.wait = WebDriverWait(driver, 10)
        # Timeouts del formulario: fallar antes para no bloquear (refresh y siguiente orden)
        # 12s es suficiente para saber si el elemento aparece; evita esperas de 25–120s
        self.form_wait_sec = 12
        self.short_wait = WebDriverWait(driver, 5)
        self.long_wait = WebDriverWait(driver, self.form_wait_sec)
        self.modal_wait = WebDriverWait(driver, self.form_wait_sec)
    
    def click_new_consultation(self, order_row=None):
        """
        Click en el botón de Nueva Consulta de la fila correcta.
        
        Args:
            order_row: Fila de la orden (opcional, si no se proporciona usa la primera)
            
        Returns:
            True si fue exitoso, False en caso contrario
        """
        self.logger.info("Haciendo click en 'Nueva consulta / New request'...")
        
        try:
            # Usar fila proporcionada o buscar la primera
            if order_row:
                row = order_row
                self.logger.info("   Usando la fila correcta identificada anteriormente")
            else:
                row = self.driver.find_element(By.CSS_SELECTOR, "tbody.list tr:first-child")
                self.logger.warning("   No hay fila específica, usando la primera")
            
            # Buscar botón de Nueva consulta
            new_consultation_button = None
            
            selectors_to_try = [
                "a[title='New request'] i.fa-headset",
                "a[title='Nueva consulta'] i.fa-headset",
                "a[title='New request']",
                "a[title='Nueva consulta']",
                "a i.fa-headset",
            ]
            
            for selector in selectors_to_try:
                try:
                    new_consultation_button = row.find_element(By.CSS_SELECTOR, selector)
                    self.logger.info(f"   ✅ Botón encontrado con selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not new_consultation_button:
                # Búsqueda genérica
                actions = row.find_elements(By.CSS_SELECTOR, "td a")
                for action in actions:
                    if action.find_elements(By.CSS_SELECTOR, "i.fa-headset") or action.find_elements(By.CSS_SELECTOR, "i.fas.fa-headset"):
                        new_consultation_button = action
                        self.logger.info("   ✅ Botón encontrado por búsqueda genérica")
                        break
                    title = action.get_attribute("title")
                    if title and ("request" in title.lower() or "consulta" in title.lower()):
                        new_consultation_button = action
                        self.logger.info("   ✅ Botón encontrado por atributo title")
                        break
            
            if not new_consultation_button:
                raise NoSuchElementException("No se pudo encontrar el botón de Nueva Consulta")
            
            # Scroll y click
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", new_consultation_button)
            time.sleep(1)
            
            element_to_click = new_consultation_button
            if new_consultation_button.tag_name == 'i':
                try:
                    element_to_click = new_consultation_button.find_element(By.XPATH, "..")
                except Exception:
                    pass

            try:
                element_to_click.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", element_to_click)
            
            time.sleep(3)
            self.logger.info("✅ Click en 'Nueva consulta' exitoso")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error al hacer click en 'Nueva consulta': {str(e)}")
            return False
    
    def select_consultation_type(self):
        """
        Selecciona el tipo de consulta: Transportadora / Carrier
        
        Estructura Dropi: app-dropi-select > div.custom-select > label "Type of inquiry"
        > div.dropdown-container > button.select-button > div.elipsis "Select the type of inquiry"
        
        Returns:
            True si fue exitoso, False en caso contrario
        """
        self.logger.info("Seleccionando tipo de consulta: Transportadora/Carrier...")
        
        try:
            # En headless/proxy Angular puede tardar más en renderizar el modal
            self.logger.info("   Esperando 4s a que el modal renderice (Angular)...")
            time.sleep(4)
            # Espera más larga solo para este paso (dropdown crítico)
            type_wait = WebDriverWait(self.driver, 25)
            # Selectores que coinciden con el DOM real: app-dropi-select, .dropdown-container, .elipsis
            type_dropdown_selectors = [
                # Exacto: componente app-dropi-select con el botón del dropdown
                (By.CSS_SELECTOR, "app-dropi-select .dropdown-container button.select-button"),
                (By.CSS_SELECTOR, "app-dropi-select .custom-select button.select-button"),
                (By.CSS_SELECTOR, "div.custom-select .select-button"),
                (By.XPATH, "//div[contains(@class, 'custom-select')][.//label[contains(., 'Type of inquiry') or contains(., 'Tipo de consulta')]]//button[contains(@class, 'select-button')]"),
                (By.XPATH, "//button[contains(@class, 'select-button') and .//div[contains(@class, 'elipsis') and (contains(., 'Select the type') or contains(., 'Selecciona el tipo'))]]"),
                (By.XPATH, "//button[contains(@class, 'select-button') and (descendant::div[contains(., 'Select the type')] or descendant::div[contains(., 'Selecciona el tipo')])]"),
            ]
            self.logger.info("   Buscando dropdown 'Tipo de consulta' (espera hasta 25s)...")
            type_dropdown = None
            for by, selector in type_dropdown_selectors:
                try:
                    # Primero presencia, luego visibilidad (menos estricto que clickable; evita fallos por overlay)
                    type_dropdown = type_wait.until(EC.presence_of_element_located((by, selector)))
                    type_dropdown = type_wait.until(EC.visibility_of(type_dropdown))
                    break
                except Exception:
                    continue
            if not type_dropdown:
                try:
                    type_dropdown = type_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".custom-select .select-button")))
                except Exception:
                    raise TimeoutException("Dropdown tipo de consulta no encontrado")
            self.logger.info("   Dropdown encontrado; abriendo...")
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", type_dropdown)
            time.sleep(0.8)
            try:
                type_dropdown.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", type_dropdown)
            time.sleep(1.2)
            
            self.logger.info("   Buscando opción 'Transportadora/Carrier'...")
            # Las opciones pueden abrirse en overlay (cdk-overlay); buscar en todo el documento
            option_wait = WebDriverWait(self.driver, 15)
            carrier_selectors = [
                "//button[contains(@class, 'option') and (.//span[contains(., 'Carrier')] or .//span[contains(., 'Transportadora')])]",
                "//button[contains(@class, 'option') and (contains(., 'Carrier') or contains(., 'Transportadora'))]",
                "//*[contains(@class, 'option') and (contains(., 'Carrier') or contains(., 'Transportadora'))]",
            ]
            transportadora_option = None
            for xpath in carrier_selectors:
                try:
                    transportadora_option = option_wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    break
                except Exception:
                    continue
            if not transportadora_option:
                raise TimeoutException("Opción Carrier/Transportadora no encontrada")
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", transportadora_option)
            time.sleep(0.5)
            try:
                transportadora_option.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", transportadora_option)
            time.sleep(1)
            self.logger.info("   Opción Transportadora/Carrier seleccionada.")
            
            # Nuevo en Dropi: al elegir Transportadora puede aparecer un popup
            # "¡Oops! Aún no es posible" / "El estado actual de la orden no permite iniciar una conversación con la transportadora"
            # Si aparece: Aceptar -> Cancel (cerrar formulario) y marcar orden como no reportable aún
            self.logger.info("   Comprobando si aparece popup 'Aún no es posible'...")
            if self._check_and_handle_carrier_not_allowed_alert():
                return 'carrier_not_allowed'
            
            self.logger.info("✅ Tipo de consulta seleccionado: Transportadora/Carrier")
            return True
            
        except TimeoutException:
            self.logger.error("❌ Timeout al seleccionar tipo de consulta")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error al seleccionar tipo de consulta: {str(e)}")
            return False
    
    def _check_and_handle_carrier_not_allowed_alert(self):
        """
        Detecta el popup de Dropi "Aún no es posible" / "Not possible yet" que dice que
        el estado de la orden no permite iniciar conversación con la transportadora.
        Si está visible: clic en Aceptar, luego en Cancel (cerrar formulario).
        
        Returns:
            True si se detectó y se manejó el popup, False si no aparece
        """
        try:
            time.sleep(1)
            self.logger.info("   Revisando DOM en busca del modal de alerta...")
            # Modal: dropi-alert-modal con contenido "Aún no es posible" / "Not possible yet" o "no permite iniciar una conversación"
            alert_indicators = [
                "//div[contains(@class, 'dropi-alert-modal')]//h2[contains(., 'Aún no es posible') or contains(., 'Not possible yet') or contains(., 'Oops')]",
                "//div[contains(@class, 'content-alert')]//p[contains(., 'no permite iniciar una conversación') or contains(., 'does not allow') or contains(., 'carrier')]",
                "//div[contains(@class, 'body-alert')]//h2[contains(., 'Oops') or contains(., 'Aún no')]",
            ]
            for xpath in alert_indicators:
                try:
                    el = self.driver.find_element(By.XPATH, xpath)
                    if el.is_displayed():
                        break
                except NoSuchElementException:
                    continue
            else:
                self.logger.info("   No se detectó popup 'Aún no es posible'; continuando con el flujo.")
                return False
            
            self.logger.warning("⚠️ Popup detectado: 'Aún no es posible' (estado de orden no permite conversación con transportadora)")
            
            # 1) Clic en Aceptar (botón primary con span "Aceptar")
            accept_selectors = [
                "//div[contains(@class, 'dropi-alert-modal')]//button[contains(@class, 'btn') and contains(@class, 'primary')]//span[contains(text(), 'Aceptar')]",
                "//div[contains(@class, 'dropi-alert-modal')]//button[.//span[contains(text(), 'Aceptar')]]",
                "//button[contains(@class, 'btn') and contains(@class, 'primary') and .//span[normalize-space(text())='Aceptar']]",
            ]
            for xpath in accept_selectors:
                try:
                    btn = self.driver.find_element(By.XPATH, xpath)
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(0.3)
                        try:
                            btn.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(1)
                        self.logger.info("   Clic en 'Aceptar' (cerrar popup)")
                        break
                except NoSuchElementException:
                    continue
            else:
                self.logger.warning("   No se encontró botón Aceptar, intentando cerrar con X")
                try:
                    close_btn = self.driver.find_element(By.XPATH, "//div[contains(@class, 'dropi-alert-modal')]//button[@aria-label='Cerrar']")
                    close_btn.click()
                    time.sleep(0.5)
                except Exception:
                    pass
            
            # 2) Clic en Cancel del formulario de nueva consulta (secondary, texto Cancel o Cancelar)
            time.sleep(0.5)
            cancel_selectors = [
                "//button[contains(@class, 'btn') and contains(@class, 'secondary') and (.//span[contains(text(), 'Cancel')] or .//span[contains(text(), 'Cancelar')])]",
                "//button[.//span[contains(text(), 'Cancel') or contains(text(), 'Cancelar')]]",
            ]
            for xpath in cancel_selectors:
                try:
                    cancel_btn = self.driver.find_element(By.XPATH, xpath)
                    if cancel_btn.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cancel_btn)
                        time.sleep(0.3)
                        try:
                            cancel_btn.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", cancel_btn)
                        time.sleep(1)
                        self.logger.info("   Clic en 'Cancel' (cerrar formulario de nueva consulta)")
                        return True
                except NoSuchElementException:
                    continue
            self._close_modal()
            return True
        except Exception as e:
            self.logger.debug("_check_and_handle_carrier_not_allowed_alert: %s", e)
            return False
    
    def select_consultation_reason(self):
        """
        Selecciona el motivo de consulta: Ordenes sin movimiento
        
        Returns:
            True si fue exitoso, 'wait_required' si detecta alert de espera, False en caso contrario
        """
        self.logger.info("Seleccionando motivo: Ordenes sin movimiento...")
        
        try:
            # Dropi actual: div.ticket-selector con span.label "Reason for query", botón con div.elipsis "Select the reason for consultation"
            reason_dropdown_selectors = [
                "//div[contains(@class, 'ticket-selector')][.//span[contains(@class, 'label') and (contains(., 'Reason for query') or contains(., 'Motivo') or contains(., 'Reason'))]]//button[contains(@class, 'select-button')]",
                "//button[contains(@class, 'select-button') and .//div[contains(@class, 'elipsis') and (contains(., 'Select the reason') or contains(., 'Selecciona el motivo') or contains(., 'reason for consultation'))]]",
                "//button[contains(@class, 'select-button') and (descendant::div[contains(., 'Select the reason')] or descendant::div[contains(., 'Selecciona el motivo')])]",
            ]
            reason_dropdown = None
            for xpath in reason_dropdown_selectors:
                try:
                    reason_dropdown = self.modal_wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    break
                except Exception:
                    continue
            if not reason_dropdown:
                try:
                    reason_dropdown = self.modal_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ticket-selector .select-button")))
                except Exception:
                    raise TimeoutException("Dropdown motivo no encontrado")
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", reason_dropdown)
            time.sleep(0.5)
            
            try:
                reason_dropdown.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", reason_dropdown)
            time.sleep(1)
            
            # Seleccionar "Ordenes sin movimiento" (opción: button.option con span "Ordenes sin movimiento")
            no_movement_selectors = [
                "//button[contains(@class, 'option') and .//span[contains(., 'Ordenes sin movimiento')]]",
                "//button[contains(@class, 'option') and (contains(., 'Ordenes sin movimiento') or contains(., 'No movement') or contains(., 'without movement'))]",
            ]
            no_movement_option = None
            for xpath in no_movement_selectors:
                try:
                    no_movement_option = self.modal_wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    break
                except Exception:
                    continue
            if not no_movement_option:
                raise TimeoutException("Opción Ordenes sin movimiento no encontrada")
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", no_movement_option)
            time.sleep(0.5)
            try:
                no_movement_option.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", no_movement_option)
            time.sleep(1)
            
            self.logger.info("✅ Motivo seleccionado: Ordenes sin movimiento")
            
            # Verificar alert de espera (debe ser verificado por popup_handler)
            time.sleep(1)
            return True
            
        except TimeoutException:
            self.logger.error("❌ Timeout al seleccionar motivo")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error al seleccionar motivo: {str(e)}")
            return False
    
    def _save_screenshot_on_failure(self, prefix="fail_siguiente"):
        """Guarda captura en results/screenshots para diagnóstico."""
        try:
            from django.conf import settings
            screenshots_dir = Path(settings.BASE_DIR) / "results" / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = screenshots_dir / f"{prefix}_{ts}.png"
            self.driver.save_screenshot(str(path))
            if self.logger:
                self.logger.warning(f"   📷 Screenshot guardado: {path}")
        except Exception:
            pass

    def _is_wait_time_alert_visible(self):
        """
        Comprueba si está visible el alert de espera (un día sin movimiento).
        Si está visible, no debe intentarse buscar ni hacer click en Next.
        Soporta texto en español e inglés.
        """
        for xpath in (
            "//app-alert//p[contains(@class, 'alert-message') and contains(., 'un día sin movimiento')]",
            "//app-alert//p[contains(@class, 'alert-message') and contains(., 'one day without any movement')]",
        ):
            try:
                el = self.driver.find_element(By.XPATH, xpath)
                if el.is_displayed():
                    return True
            except NoSuchElementException:
                continue
            except Exception:
                continue
        return False

    def click_next_button(self):
        """
        Click en el botón Siguiente/Next (selectores por clase + texto ES/EN).
        Si está visible el alert de "esperar un día sin movimiento", no intenta buscar el botón.

        Returns:
            True si fue exitoso, False en caso contrario
        """
        if self._is_wait_time_alert_visible():
            self.logger.warning("⚠️ Alert de espera visible: no se busca botón Siguiente/Next")
            return False

        self.logger.info("Haciendo click en 'Siguiente'...")
        # Selectores: botón "btn primary default normal" con texto Next/Siguiente (Dropi); luego genéricos
        next_selectors = [
            (By.XPATH, "//button[contains(@class, 'btn') and contains(@class, 'primary') and contains(@class, 'normal') and (.//span[contains(text(), 'Next')] or .//span[contains(text(), 'Siguiente')])]"),
            (By.XPATH, "//button[.//span[@class='text' and (contains(text(), 'Next') or contains(text(), 'Siguiente'))]]"),
            (By.XPATH, "//button[contains(@class, 'btn') and (contains(., 'Siguiente') or contains(., 'Next'))]"),
            (By.XPATH, "//button[contains(@class, 'p-button') and (contains(., 'Siguiente') or contains(., 'Next'))]"),
            (By.XPATH, "//button[.//span[contains(text(), 'Siguiente') or contains(text(), 'Next')]]"),
            (By.XPATH, "//button[.//*[contains(text(), 'Siguiente') or contains(text(), 'Next')]]"),
        ]
        next_button = None
        try:
            for by, selector in next_selectors:
                try:
                    next_button = self.long_wait.until(EC.presence_of_element_located((by, selector)))
                    if not next_button.is_displayed():
                        next_button = None
                        continue
                    if next_button.get_attribute("disabled") is not None or "disabled" in (next_button.get_attribute("class") or "").split():
                        self.logger.warning("⚠️ Botón Siguiente/Next está bloqueado (p. ej. alert de espera)")
                        return False
                    break
                except TimeoutException:
                    next_button = None
                    continue
            if next_button is None:
                self._save_screenshot_on_failure("fail_siguiente")
                self.logger.warning("⚠️ Timeout al buscar botón 'Siguiente' - Probablemente bloqueado")
                self._close_modal()
                return False
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            time.sleep(0.5)
            try:
                next_button.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", next_button)
            time.sleep(1)
            self.logger.info("✅ Click en 'Siguiente' exitoso")
            return True
        except TimeoutException:
            self._save_screenshot_on_failure("fail_siguiente")
            self.logger.warning("⚠️ Timeout al buscar botón 'Siguiente' - Probablemente bloqueado")
            self._close_modal()
            return False
        except Exception as e:
            self._save_screenshot_on_failure("fail_siguiente")
            self.logger.error(f"❌ Error al hacer click en 'Siguiente': {str(e)}")
            self._close_modal()
            return False
    
    def _close_modal(self):
        """Cierra el modal con Cancel / Cancelar"""
        try:
            cancel_button = self.driver.find_element(
                By.XPATH,
                "//button[contains(@class, 'btn') and contains(@class, 'secondary') and (.//span[contains(text(), 'Cancelar')] or .//span[contains(text(), 'Cancel')])]"
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cancel_button)
            time.sleep(0.5)
            try:
                cancel_button.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", cancel_button)
            time.sleep(1)
        except Exception:
            pass
    
    def get_random_observation_text(self):
        """Selecciona un texto de observación aleatorio"""
        return random.choice(self.OBSERVATION_TEXTS)
    
    def enter_observation_text(self):
        """
        Ingresa el texto de observación (seleccionado aleatoriamente)
        
        Returns:
            True si fue exitoso, False en caso contrario
        """
        self.logger.info("Ingresando texto de observación...")
        
        try:
            observation_text = self.get_random_observation_text()
            self.logger.info(f"   Texto seleccionado (aleatorio): '{observation_text}'")
            
            textarea = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "textarea[id='description'], textarea[placeholder*='Tell the conveyor'], textarea[placeholder*='transportadora']"
                ))
            )
            
            textarea.clear()
            time.sleep(0.5)
            textarea.send_keys(observation_text)
            time.sleep(1)
            
            self.logger.info(f"✓ Texto ingresado: '{observation_text}'")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Error al ingresar texto: {str(e)}")
            return False
    
    def start_conversation(self):
        """
        Click en el botón 'Iniciar conversación' / 'Start conversation'.
        Dropi: button.btn.primary.default.normal con span.text "Start conversation".
        
        Returns:
            True si fue exitoso, False en caso contrario
        """
        self.logger.info("Iniciando conversación...")
        
        start_wait = WebDriverWait(self.driver, 20)
        selectors = [
            # Texto exacto que usa Dropi actual
            (By.XPATH, "//button[contains(@class, 'btn') and contains(@class, 'primary')]//span[contains(., 'Start conversation')]/ancestor::button"),
            (By.XPATH, "//span[contains(., 'Start conversation')]/ancestor::button[contains(@class, 'btn')]"),
            (By.XPATH, "//button[.//span[contains(@class, 'text') and contains(., 'Start conversation')]]"),
            (By.CSS_SELECTOR, "button.btn.primary.default.normal"),
            (By.XPATH, "//button[contains(@class, 'btn') and (descendant::span[contains(., 'Iniciar un')] or descendant::span[contains(., 'Start a conversation')] or descendant::span[contains(., 'Start conversation')])]"),
        ]
        start_button = None
        for by, selector in selectors:
            try:
                start_button = start_wait.until(EC.presence_of_element_located((by, selector)))
                start_button = start_wait.until(EC.visibility_of(start_button))
                break
            except Exception:
                continue
        if not start_button:
            try:
                start_button = start_wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn')]//span[contains(., 'Start')]")))
            except Exception:
                self.logger.error("✗ Botón 'Start conversation' no encontrado")
                return False
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", start_button)
            time.sleep(0.5)
            start_button.click()
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", start_button)
            except Exception as e:
                self.logger.error(f"✗ Error al iniciar conversación: {str(e)}")
                return False
        time.sleep(2)
        self.logger.info("✓ Conversación iniciada")
        return True
