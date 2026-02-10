"""
Order Searcher - Búsqueda y validación de órdenes en la web

Este módulo se encarga de:
1. Buscar órdenes por ID o teléfono (búsqueda directa O(1))
2. Validar que el estado coincida con el esperado
3. Guardar referencia a la fila correcta para acciones posteriores
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementNotInteractableException,
    ElementClickInterceptedException
)


class OrderSearcher:
    """
    Módulo encargado de buscar y validar órdenes en la página web.
    """
    
    def __init__(self, driver, logger):
        """
        Inicializa el searcher
        
        Args:
            driver: WebDriver compartido (ya logueado)
            logger: Logger configurado
        """
        self.driver = driver
        self.logger = logger
        self.wait = WebDriverWait(driver, 15)
        self.current_order_row = None
    
    def search_order(self, term):
        """
        Busca una orden por término (Teléfono o ID)
        
        Args:
            term: Término de búsqueda (ID o teléfono)
            
        Returns:
            True si se encontró la orden, False en caso contrario
        """
        self.logger.info(f"🔎 Buscando orden: {term}")
        
        # Intentos con autorecuperación (refresh) si el input está bloqueado
        for attempt in range(2):
            try:
                # Buscar el input de búsqueda
                search_input = self.wait.until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "input[name='textToSearch'], input[placeholder*='Buscar']"
                    ))
                )
                
                # Limpiar búsqueda anterior e ingresar nuevo
                try:
                    search_input.clear()
                except (ElementNotInteractableException, ElementClickInterceptedException):
                    raise ElementNotInteractableException("Input bloqueado al hacer clear()")
                
                time.sleep(0.5)
                search_input.send_keys(str(term))
                time.sleep(0.5)
                
                # Presionar ENTER para ejecutar la búsqueda
                search_input.send_keys(Keys.RETURN)
                time.sleep(2)
                
                # Verificar si hay resultados
                try:
                    self.wait.until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR,
                            "tbody.list tr"
                        ))
                    )
                    self.logger.info(f"   ✅ Resultado encontrado ('{term}')")
                    return True
                except TimeoutException:
                    self.logger.warning(f"   ⚠️ No se encontraron resultados para: {term}")
                    return False
                    
            except (ElementNotInteractableException, ElementClickInterceptedException) as e:
                if attempt == 0:
                    self.logger.warning(f"   ⚠️ Input bloqueado. Refrescando página...")
                    try:
                        self.driver.refresh()
                        time.sleep(5)
                        # Navegar de nuevo a órdenes
                        self.driver.get("https://app.dropi.co/dashboard/orders")
                        self.wait.until(EC.url_contains("/dashboard/orders"))
                        time.sleep(5)
                    except Exception as refresh_error:
                        self.logger.error(f"   ❌ Error al refrescar: {str(refresh_error)}")
                    continue
                else:
                    self.logger.error(f"   ❌ Error al buscar orden (Intento {attempt+1}): {str(e)}")
                    return False
            except Exception as e:
                self.logger.error(f"   ❌ Error al buscar orden: {str(e)}")
                return False
                
        return False
    
    def validate_order_state(self, expected_state, order_id=None):
        """
        Valida que el estado de la orden coincida con el esperado.
        Si order_id viene informado y hay varias filas (mismo teléfono), elige la fila
        cuya columna # coincide con order_id.
        Guarda referencia a la fila correcta para acciones posteriores.
        
        Args:
            expected_state: Estado esperado de la orden
            order_id: ID de la orden (opcional). Si hay varias órdenes del cliente, se hace match por este ID.
            
        Returns:
            True si el estado coincide, False en caso contrario
        """
        try:
            self.logger.info(f"Validando estado esperado: {expected_state}" + (f" (ID orden: {order_id})" if order_id else ""))
            
            rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody.list tr")
            if not rows:
                self.logger.warning("❌ No se encontraron filas en la tabla")
                return False

            expected_normalized = expected_state.upper().strip()
            target_row = None

            if order_id and str(order_id).strip():
                # Buscar la fila cuya columna # (segunda celda, índice 1) coincide con order_id
                order_id_str = str(order_id).strip()
                for row in rows:
                    cells = row.find_elements(By.XPATH, "./td | ./th")
                    if len(cells) < 2:
                        continue
                    cell_id_text = cells[1].text.strip()
                    if cell_id_text == order_id_str:
                        target_row = row
                        self.logger.info(f"   Fila con ID de orden '{order_id_str}' encontrada.")
                        break
                if not target_row:
                    self.logger.warning(f"   No se encontró ninguna fila con ID de orden '{order_id_str}' en los resultados.")
                    return False
            else:
                target_row = rows[0]

            # Validar estado en la fila elegida
            badges = target_row.find_elements(By.CSS_SELECTOR, "td span.badge, td div.badge, td span.status")
            if not badges:
                self.logger.warning("   No se encontraron badges de estado en la fila.")
                return False

            found_match = False
            for badge in badges:
                current_state = badge.text.strip()
                if not current_state:
                    continue
                current_normalized = current_state.upper().strip()
                if (expected_normalized in current_normalized) or (current_normalized in expected_normalized):
                    self.logger.info(f"   ✅ ¡COINCIDENCIA! Estado correcto: '{current_state}'")
                    found_match = True
                    break

            if found_match:
                self.current_order_row = target_row
                return True
            self.logger.warning(f"❌ La orden no coincide con el estado esperado '{expected_state}'")
            return False

        except Exception as e:
            self.logger.error(f"❌ Error al validar estado: {str(e)}")
            return False
    
    def get_current_order_row(self):
        """Retorna la fila actual de la orden (si está guardada)"""
        return self.current_order_row
    
    def clear_order_row(self):
        """Limpia la referencia a la fila actual"""
        self.current_order_row = None
