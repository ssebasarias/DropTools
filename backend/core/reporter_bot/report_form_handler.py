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
        self.wait = WebDriverWait(driver, 15)
        self.short_wait = WebDriverWait(driver, 5)
    
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
        
        Returns:
            True si fue exitoso, False en caso contrario
        """
        self.logger.info("Seleccionando tipo de consulta: Transportadora/Carrier...")
        
        try:
            dropdown_xpath = "//button[contains(@class, 'select-button') and (descendant::p[contains(text(), 'Select the type')] or descendant::p[contains(text(), 'Selecciona el tipo')])]"
            dropdown_css = ".select-container:first-child .select-button"
            
            try:
                type_dropdown = self.wait.until(EC.element_to_be_clickable((By.XPATH, dropdown_xpath)))
            except Exception:
                type_dropdown = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, dropdown_css)))
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", type_dropdown)
            time.sleep(1)
            
            try:
                type_dropdown.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", type_dropdown)
            time.sleep(1)
            
            # Seleccionar "Transportadora" o "Carrier"
            carrier_xpath = "//button[contains(@class, 'option') and (contains(., 'Transportadora') or contains(., 'Carrier'))]"
            transportadora_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, carrier_xpath)))
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", transportadora_option)
            time.sleep(0.5)
            try:
                transportadora_option.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", transportadora_option)
            time.sleep(1)
            
            self.logger.info("✅ Tipo de consulta seleccionado: Transportadora/Carrier")
            return True
            
        except TimeoutException:
            self.logger.error("❌ Timeout al seleccionar tipo de consulta")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error al seleccionar tipo de consulta: {str(e)}")
            return False
    
    def select_consultation_reason(self):
        """
        Selecciona el motivo de consulta: Ordenes sin movimiento
        
        Returns:
            True si fue exitoso, 'wait_required' si detecta alert de espera, False en caso contrario
        """
        self.logger.info("Seleccionando motivo: Ordenes sin movimiento...")
        
        try:
            dropdown_xpath = "//button[contains(@class, 'select-button') and (descendant::div[contains(text(), 'Select the reason')] or descendant::div[contains(text(), 'Selecciona el motivo')])]"
            dropdown_css = ".ticket-selector:nth-of-type(2) .select-button"
            
            try:
                reason_dropdown = self.wait.until(EC.element_to_be_clickable((By.XPATH, dropdown_xpath)))
            except Exception:
                reason_dropdown = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, dropdown_css)))
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", reason_dropdown)
            time.sleep(0.5)
            
            try:
                reason_dropdown.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", reason_dropdown)
            time.sleep(1)
            
            # Seleccionar "Ordenes sin movimiento"
            option_xpath = "//button[contains(@class, 'option') and (contains(., 'Ordenes sin movimiento') or contains(., 'No movement') or contains(., 'without movement'))]"
            no_movement_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
            
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
    
    def click_next_button(self):
        """
        Click en el botón Siguiente (con fallback a Cancelar si falla)
        
        Returns:
            True si fue exitoso, False en caso contrario
        """
        self.logger.info("Haciendo click en 'Siguiente'...")
        
        try:
            next_xpath = "//button[contains(@class, 'btn') and (descendant::span[contains(text(), 'Siguiente')] or descendant::span[contains(text(), 'Next')])]"
            
            next_button = self.short_wait.until(EC.element_to_be_clickable((By.XPATH, next_xpath)))
            
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
            self.logger.warning("⚠️ Timeout al buscar botón 'Siguiente' - Probablemente bloqueado")
            self._close_modal()
            return False
        except Exception as e:
            self.logger.error(f"❌ Error al hacer click en 'Siguiente': {str(e)}")
            self._close_modal()
            return False
    
    def _close_modal(self):
        """Cierra el modal con Cancelar"""
        try:
            cancel_button = self.driver.find_element(
                By.XPATH,
                "//button[contains(@class, 'btn') and contains(@class, 'secondary') and .//span[contains(text(), 'Cancelar')]]"
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
        Click en el botón 'Iniciar una conversación'
        
        Returns:
            True si fue exitoso, False en caso contrario
        """
        self.logger.info("Iniciando conversación...")
        
        try:
            start_xpath = "//button[contains(@class, 'btn') and (descendant::span[contains(text(), 'Iniciar un')] or descendant::span[contains(text(), 'Start a conversation')])]"
            
            start_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, start_xpath)))
            start_button.click()
            time.sleep(2)
            
            self.logger.info("✓ Conversación iniciada")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Error al iniciar conversación: {str(e)}")
            return False
