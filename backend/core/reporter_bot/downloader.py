"""
Downloader - Módulo de descarga de reportes Excel desde Dropi

Este módulo se encarga de:
1. Navegar a "Mis Pedidos"
2. Verificar historial en BD (si hay batches previos)
3. Descargar reportes Excel (Ayer/Hoy según historial)
4. Procesar inmediatamente a BD (RawOrderSnapshot)
5. Eliminar archivos físicos después de procesar
"""

import os
import time
import glob
import calendar
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from django.conf import settings
from django.utils import timezone as django_tz
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from core.models import ReportBatch, RawOrderSnapshot, User
from core.reporter_bot.docker_config import get_downloader_wait_timeout


class DropiDownloader:
    """
    Componente encargado de la descarga de reportes.
    Usa el driver compartido y maneja la navegación específica para descargar Excels.
    """
    
    ORDERS_URL = "https://app.dropi.co/dashboard/orders"
    REPORTS_URL = "https://app.dropi.co/dashboard/reports/downloads"
    
    def __init__(self, driver, user_id, logger, download_dir=None):
        """
        Inicializa el downloader
        
        Args:
            driver: WebDriver compartido (ya logueado)
            user_id: ID del usuario Django
            logger: Logger configurado
            download_dir: Directorio para descargas (opcional)
        """
        self.driver = driver
        self.user_id = user_id
        self.logger = logger
        # Timeout mayor en Docker/headless (página tarda más en renderizar)
        wait_seconds = get_downloader_wait_timeout()
        self.wait = WebDriverWait(driver, wait_seconds)
        
        # Configurar directorio de descargas
        if download_dir:
            self.download_dir_base = Path(download_dir)
        else:
            self.download_dir_base = Path(settings.BASE_DIR) / 'results' / 'downloads'
        
        self.user_download_dir = self.download_dir_base / str(self.user_id)
        self.today_str = datetime.now().strftime('%Y-%m-%d')
        self.download_dir = self.user_download_dir / self.today_str
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Actualizar ruta de descarga en el navegador
        try:
            self.driver.execute_cdp_cmd('Browser.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': str(self.download_dir)
            })
            if self.logger:
                self.logger.info(f"   🔧 Configuración de descarga actualizada: {self.download_dir}")
        except Exception:
            pass
        
        # Cargar usuario
        try:
            self.user = User.objects.get(id=self.user_id)
        except User.DoesNotExist:
            self.user = None
            if self.logger:
                self.logger.error(f"❌ Usuario ID {self.user_id} no encontrado")
        
        # Estadísticas
        self.stats = {
            'reporte_anterior_descargado': False,
            'reporte_actual_descargado': False
        }

    def run(self):
        """
        Lógica principal de descarga:
        1. Verifica historial (si ya hay batches exitosos, solo descarga HOY).
        2. Si es nuevo, descarga AYER y HOY.
        3. Procesa cada Excel a BD.
        
        Returns:
            list: Lista de rutas de archivos descargados
        """
        if self.logger:
            self.logger.info("="*60)
            self.logger.info("📥 INICIANDO MÓDULO DOWNLOADER (Unificado)")
            self.logger.info("="*60)
        
        # PASO 1: Validar si existe reporte generado AYER y HOY (en timezone de la aplicación)
        # created_at se guarda en UTC; comparar por rango en timezone local evita falsos negativos.
        today_local = django_tz.localdate()
        yesterday_local = today_local - timedelta(days=1)
        tz = django_tz.get_current_timezone()

        def _start_of_day(d):
            return django_tz.make_aware(datetime.combine(d, datetime.min.time()), tz)

        start_yesterday = _start_of_day(yesterday_local)
        end_yesterday = _start_of_day(today_local)
        start_today = _start_of_day(today_local)
        end_today = _start_of_day(today_local + timedelta(days=1))

        exists_batch_yesterday = ReportBatch.objects.filter(
            user_id=self.user_id,
            status='SUCCESS',
            created_at__gte=start_yesterday,
            created_at__lt=end_yesterday
        ).exists()

        exists_batch_today = ReportBatch.objects.filter(
            user_id=self.user_id,
            status='SUCCESS',
            created_at__gte=start_today,
            created_at__lt=end_today
        ).exists()

        dates_to_download = []

        if not exists_batch_yesterday:
            if self.logger:
                self.logger.info("   📋 No se detectó reporte de ayer en BD -> Agendando descarga de AYER.")
            dates_to_download.append(datetime(yesterday_local.year, yesterday_local.month, yesterday_local.day))
        else:
            if self.logger:
                self.logger.info("   📋 Reporte de ayer ya existe en BD.")

        if not exists_batch_today:
            if self.logger:
                self.logger.info("   📋 Agendando descarga de HOY (cada día es único, no se actualizan datos).")
            dates_to_download.append(datetime(today_local.year, today_local.month, today_local.day))
        else:
            if self.logger:
                self.logger.info("   📋 Reporte de hoy ya existe en BD -> No se descarga de nuevo (un batch por día).")

        if not dates_to_download:
            if self.logger:
                self.logger.info("   ✅ Ayer y hoy ya tienen batch en BD. Nada que descargar.")
            return []

        success = True
        descargados = []

        # PASO 2: Navegar a órdenes (una sola vez)
        if not self._navigate_to_orders():
            if self.logger:
                self.logger.error("❌ Falló navegación inicial a órdenes")
            return []

        # PASO 3: Bucle de descargas
        for report_date in dates_to_download:
            fecha_inicio, fecha_fin = self._calculate_dates_for_day(report_date)
            label = "AYER" if report_date.date() < today_local else "HOY"
            
            if self.logger:
                self.logger.info(f"   ⬇️ Proceso descarga {label} ({fecha_inicio.strftime('%d/%m')} - {fecha_fin.strftime('%d/%m')})")
            
            file_path = self._download_single_report(fecha_inicio, fecha_fin)
            
            if file_path:
                if self.logger:
                    self.logger.info(f"   ✅ Archivo descargado: {Path(file_path).name}")
                self._process_excel_to_db(file_path, fecha_fin)
                descargados.append(file_path)
                
                # Pausa entre descargas
                time.sleep(3)
            else:
                if self.logger:
                    self.logger.error(f"   ❌ Falló descarga de {label}")
                success = False
                break  # Detener si falla uno para evitar inconsistencias
        
        return descargados

    def _calculate_dates_for_day(self, target_day):
        """
        Calcula fecha inicio (mes exacto atrás) y fin (día objetivo)
        
        Ejemplo si target_day es 19/01/2026:
        - Fecha inicio: 19/12/2025
        - Fecha fin: 19/01/2026
        
        Args:
            target_day: datetime del día objetivo
            
        Returns:
            tuple: (fecha_inicio, fecha_fin)
        """
        dia_mes = target_day.day
        
        # Calcular mes anterior
        if target_day.month == 1:
            fecha_inicio = datetime(target_day.year - 1, 12, dia_mes)
        else:
            try:
                fecha_inicio = datetime(target_day.year, target_day.month - 1, dia_mes)
            except ValueError:
                # Si el día no existe en el mes anterior, usar el último día de ese mes
                ultimo_dia = calendar.monthrange(target_day.year, target_day.month - 1)[1]
                fecha_inicio = datetime(target_day.year, target_day.month - 1, ultimo_dia)
        
        # Fecha fin es el mismo día
        fecha_fin = datetime(target_day.year, target_day.month, dia_mes)
        return fecha_inicio, fecha_fin

    def _navigate_to_orders(self):
        """Navega a la sección de Mis Pedidos"""
        try:
            if self.logger:
                self.logger.info("   📍 Navegando a Mis Pedidos...")
            self.driver.get(self.ORDERS_URL)
            self.wait.until(EC.url_contains("/dashboard/orders"))
            time.sleep(5)
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"   ❌ Error navegando a órdenes: {e}")
            return False

    def _download_single_report(self, start_date, end_date):
        """
        Orquesta pasos de UI para descargar UN reporte
        
        Args:
            start_date: Fecha de inicio (datetime)
            end_date: Fecha de fin (datetime)
            
        Returns:
            str: Ruta del archivo descargado o None si falló
        """
        # Si no estamos en orders, navegar
        if "/dashboard/orders" not in self.driver.current_url:
            if not self._navigate_to_orders():
                return None

        # 1. Abrir filtros
        if not self._open_filters():
            return None
        
        # 2. Setear fechas (si falla, no seguir: sin rango correcto el reporte trae ~1k filas por defecto)
        if not self._set_date_range(start_date, end_date):
            if self.logger:
                self.logger.error("   ❌ No se pudo configurar rango de fechas. Abortando descarga.")
            return None
        # 2.5 Validar que los filtros quedaron aplicados antes de Acciones
        if not self._verify_filters_applied(start_date, end_date):
            if self.logger:
                self.logger.warning("   ⚠️ Validación de filtros falló; continuando igual (el reporte puede traer menos filas).")
        
        # 2.6 Espera a que la página asiente tras filtros (headless/Docker tarda más en renderizar)
        if self.logger:
            self.logger.info("   ⏳ Esperando a que la tabla/filtros terminen de cargar...")
        time.sleep(5)
        try:
            self.wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "a.dropdown-toggle.btn.btn-light"
            )))
        except Exception:
            pass  # Si no aparece en 120s, _click_download_action intentará con reintentos y selectores alternativos
        
        # 3. Click Descargar (Acciones → Orders with Products)
        if self.logger:
            self.logger.warning("   📥 Intentando click en Acciones → Órdenes con Productos...")
        if not self._click_download_action():
            if self.logger:
                self.logger.warning("   🛑 Falló click en Acciones/descarga. No se descargó archivo.")
            return None
        
        # 4. Esperar y Descargar (Manejo de Modal + Espera de archivo)
        return self._wait_for_report_and_download()

    def _open_filters(self):
        """
        Abre el panel de filtros en Mis Pedidos. Usa solo el selector que funciona en Dropi
        (botón por clase btn-success btn-sm) para no perder tiempo en intentos que fallan.
        """
        by, selector = By.CSS_SELECTOR, "button.btn.btn-success.btn-sm"
        try:
            filter_button = self.wait.until(EC.presence_of_element_located((by, selector)))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", filter_button)
            time.sleep(0.5)
            filter_button = self.wait.until(EC.element_to_be_clickable((by, selector)))
            if self.logger:
                self.logger.info("   🔍 Botón filtros encontrado, haciendo clic...")
            self._safe_click(filter_button)
            time.sleep(2)
            if self._date_inputs_visible():
                if self.logger:
                    self.logger.info("   ✅ Panel de filtros abierto (inputs de fecha visibles).")
                return True
            if self.logger:
                self.logger.warning("   ⚠️ Clic en filtros pero no se detectaron inputs de fecha.")
        except Exception as e:
            if self.logger:
                self.logger.warning(f"   ⚠️ Botón filtros: {e}")
        self._save_screenshot_on_failure("fail_open_filters")
        if self.logger:
            self.logger.error("   ❌ No se pudo abrir el panel de filtros. Sin filtros, el reporte trae datos por defecto (~1k filas).")
        return False

    def _get_modal_body(self):
        """
        Devuelve el contenedor del modal de filtros (app-filter-modal → modal-body).
        Así todos los selectores de fechas y Ok se limitan al modal y no a otros elementos de la página.
        """
        # Estructura real: app-filter-modal > app-modal-template > div.modal-body
        for xpath in [
            "//app-filter-modal//div[contains(@class, 'modal-body')]",
            "//div[contains(@class, 'modal-body') and .//h4[contains(@class, 'modal-title') and (contains(., 'Filtros') or contains(., 'Filters'))]]",
            "//div[contains(@class, 'modal-body')]//input[@placeholder='From']/ancestor::div[contains(@class, 'modal-body')]",
        ]:
            try:
                el = self.driver.find_element(By.XPATH, xpath)
                if el.is_displayed():
                    return el
            except Exception:
                continue
        return None

    def _date_inputs_visible(self):
        """Comprueba si el modal de filtros está abierto y los dos inputs de fecha (p-calendar) son visibles.
        Solo usa atributos del DOM (placeholder From/Until o estructura: inputs con botón p-datepicker-trigger).
        No se usan nombres como 'Desde'/'Hasta'; son analogías del usuario.
        """
        # 1) Por placeholder (atributo real en DOM; PrimeNG suele usar From/Until)
        for placeholder in ["From", "Until"]:
            try:
                el = self.driver.find_element(
                    By.XPATH,
                    f"//div[contains(@class, 'modal-body')]//input[@placeholder='{placeholder}']"
                )
                if el.is_displayed():
                    return True
            except Exception:
                try:
                    el = self.driver.find_element(By.XPATH, f"//input[@placeholder='{placeholder}']")
                    if el.is_displayed():
                        return True
                except Exception:
                    continue
        # 2) Por estructura: dos inputs de fecha (p-calendar) dentro del modal
        try:
            inputs = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'modal-body')]//input[following-sibling::button[contains(@class, 'p-datepicker-trigger')]]"
            )
            if len(inputs) >= 2 and all(el.is_displayed() for el in inputs[:2]):
                return True
        except Exception:
            pass
        return False

    def _find_date_input_by_position(self, index):
        """Devuelve el input de fecha por posición en el modal (1=primero, 2=segundo). Index 1 es el PILAR (fecha desde)."""
        xpath = (
            f"(//div[contains(@class, 'modal-body')]//input[following-sibling::button[contains(@class, 'p-datepicker-trigger')]])[{index}]"
        )
        try:
            el = self.driver.find_element(By.XPATH, xpath)
            return el if el.is_displayed() else None
        except Exception:
            return None

    def _set_date_via_calendar_button(self, strategies, date_obj, label, is_filter_1=False):
        """
        Setea una fecha haciendo clic en el botón del calendario (icono), panel PrimeNG, navegar mes/año, clic día.
        strategies: lista de formas de encontrar el input, en orden de prioridad. Ej: [1, "From"] = primero por
                    posición (1º input), luego por placeholder "From". El FILTRO #1 (fecha desde) debe usar [1, "From"]
                    para que siempre se setee el primer campo del modal (el pilar del rango de un mes).
        is_filter_1: si True, es el filtro #1 (fecha desde); se loguea y verifica explícitamente.
        """
        try:
            input_el = None
            method_used = None
            for s in strategies:
                if s in (1, 2):
                    input_el = self._find_date_input_by_position(s)
                    if input_el:
                        method_used = f"posición #{s}"
                        break
                elif s in ("From", "Until"):
                    xpath_input = f"//div[contains(@class, 'modal-body')]//input[@placeholder='{s}']"
                    try:
                        input_el = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath_input)))
                    except Exception:
                        try:
                            input_el = self.driver.find_element(By.XPATH, f"//input[@placeholder='{s}']")
                        except Exception:
                            pass
                    if input_el and input_el.is_displayed():
                        method_used = f"placeholder '{s}'"
                        break
                    input_el = None
            if not input_el or not input_el.is_displayed():
                if self.logger and is_filter_1:
                    self.logger.warning("      ⚠️ FILTRO #1 (fecha desde): no se encontró el input.")
                return False
            if self.logger and is_filter_1:
                self.logger.info(f"      🎯 FILTRO #1 (fecha desde) — input encontrado por {method_used}.")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_el)
            time.sleep(0.3)
            # 2. Botón que abre el calendario: hermano del input (p-datepicker-trigger)
            trigger_btn = None
            try:
                trigger_btn = input_el.find_element(
                    By.XPATH, "./following-sibling::button[contains(@class, 'p-datepicker-trigger')]"
                )
            except Exception:
                pass
            if not trigger_btn or not trigger_btn.is_displayed():
                if self.logger:
                    self.logger.warning(f"      No se encontró botón calendario para {label}.")
                if is_filter_1 and self.logger:
                    self.logger.warning("      ⚠️ FILTRO #1: sin botón calendario no se puede setear la fecha desde.")
                return False
            if self.logger:
                self.logger.info(f"      📅 Abriendo calendario {label} (clic en botón)...")
            self._safe_click(trigger_btn)
            time.sleep(1)
            # 3. Esperar y obtener el panel visible (role="dialog", p-datepicker p-component)
            panel = self.wait.until(EC.visibility_of_element_located((
                By.XPATH,
                "//div[contains(@class, 'p-datepicker') and contains(@class, 'p-component') and @role='dialog']"
            )))
            # Si hay varios en DOM, quedarnos con el que esté visible
            try:
                panels = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'p-datepicker') and contains(@class, 'p-component')]")
                for p in panels:
                    if p.is_displayed():
                        panel = p
                        break
            except Exception:
                pass
            time.sleep(0.5)
            # 4. Navegar al mes/año correcto dentro de ESTE panel (p-datepicker-prev / p-datepicker-next)
            self._navigate_calendar_to_date(date_obj, panel=panel)
            time.sleep(0.5)
            # 5. Clic en el día dentro del panel: data-date="YYYY-M-D" (mes 0-indexed), excluir other-month
            day = date_obj.day
            month_0 = date_obj.month - 1
            year = date_obj.year
            data_date = f"{year}-{month_0}-{day}"
            day_el = None
            for xpath in [
                f".//span[@data-date='{data_date}' and not(ancestor::td[contains(@class, 'p-datepicker-other-month')])]",
                f".//span[@data-date='{data_date}']",
                f".//td[not(contains(@class, 'p-datepicker-other-month'))]//span[@data-date='{data_date}']",
            ]:
                try:
                    day_el = panel.find_element(By.XPATH, xpath)
                    if day_el.is_displayed():
                        break
                except Exception:
                    continue
            if not day_el or not day_el.is_displayed():
                if self.logger:
                    self.logger.warning(f"      No se encontró día {day} en calendario para {label}.")
                try:
                    self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                except Exception:
                    pass
                return False
            self._safe_click(day_el)
            time.sleep(0.8)
            if self.logger:
                self.logger.info(f"      ✅ {label} seleccionada: {date_obj.strftime('%d/%m/%Y')}")
            # Verificación crítica para FILTRO #1 (fecha desde): leer valor del input y confirmar que quedó
            if is_filter_1:
                time.sleep(0.5)
                try:
                    val = (input_el.get_attribute("value") or "").strip()
                    expected = date_obj.strftime("%d/%m/%Y")
                    if expected in val or expected.replace("/", "-") in val:
                        if self.logger:
                            self.logger.info(f"      ✅ FILTRO #1 verificado en input: '{val}' (rango de un mes asegurado)")
                    elif val and self.logger:
                        self.logger.warning(f"      ⚠️ FILTRO #1: input muestra '{val}', esperado '{expected}' — revisar si el reporte trae solo ~1 semana")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"      ⚠️ FILTRO #1: no se pudo verificar valor en input: {e}")
            try:
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except Exception:
                pass
            return True
        except Exception as e:
            if self.logger:
                self.logger.warning(f"      Calendario UI {label}: {e}")
            if is_filter_1 and self.logger:
                self.logger.warning("      ⚠️ FILTRO #1 (fecha desde) falló — el reporte podría traer solo ~1 semana por defecto.")
            try:
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except Exception:
                pass
            return False

    def _set_date_range(self, fecha_inicio, fecha_fin):
        """
        Configura rango de fechas en el modal de filtros (app-filter-modal).
        Flujo correcto: clic en botón del calendario (icono) → se abre el panel →
        navegar mes/año (p-datepicker-prev/next) → clic en el día.
        Si falla, intenta escribir en el input (readonly).
        """
        date_fmt_4 = "%d/%m/%Y"
        date_fmt_2 = "%d/%m/%y"
        if self.logger:
            self.logger.info(f"   📅 Configurando rango de fechas (Desde: {fecha_inicio.strftime(date_fmt_4)}, Hasta: {fecha_fin.strftime(date_fmt_4)})...")

        # Primero: flujo por UI. FILTRO #1 (fecha desde) es el pilar: sin él el reporte trae solo ~1 semana.
        # Buscamos el input por posición 1 primero, luego placeholder "From".
        try:
            ok_from = self._set_date_via_calendar_button(
                [1, "From"], fecha_inicio, "DESDE (filtro #1)", is_filter_1=True
            )
            time.sleep(1)
            ok_until = self._set_date_via_calendar_button([2, "Until"], fecha_fin, "HASTA")
            if ok_from and ok_until:
                time.sleep(0.5)
                for xpath in [
                    "//div[contains(@class, 'modal-body')]//button[contains(@class, 'btn-success') and normalize-space(.)='Ok']",
                    "//app-filter-modal//button[contains(@class, 'btn-success') and normalize-space(.)='Ok']",
                    "//button[contains(@class, 'btn-success') and normalize-space(.)='Ok']",
                ]:
                    try:
                        ok_btn = self.driver.find_element(By.XPATH, xpath)
                        if ok_btn.is_displayed():
                            self._safe_click(ok_btn)
                            if self.logger:
                                self.logger.info("   ✅ Clic en Ok para aplicar filtros.")
                            time.sleep(2)
                            return True
                    except Exception:
                        continue
                self._save_screenshot_on_failure("fail_ok_filters")
                return True
            if self.logger and (not ok_from or not ok_until):
                self.logger.warning("   ⚠️ Calendario UI falló; intentando escribir en input...")
        except Exception as e:
            if self.logger:
                self.logger.warning(f"   ⚠️ Flujo calendario: {e}")

        # Fallback: escribir en input (solo atributos DOM: placeholder From/Until o posición 1º/2º)
        xpath_from = "//div[contains(@class, 'modal-body')]//input[@placeholder='From']"
        xpath_until = "//div[contains(@class, 'modal-body')]//input[@placeholder='Until']"
        xpath_from_fb = "//input[@placeholder='From']"
        xpath_until_fb = "//input[@placeholder='Until']"
        xpath_1st = "(//div[contains(@class, 'modal-body')]//input[following-sibling::button[contains(@class, 'p-datepicker-trigger')]])[1]"
        xpath_2nd = "(//div[contains(@class, 'modal-body')]//input[following-sibling::button[contains(@class, 'p-datepicker-trigger')]])[2]"

        def find_and_set_date(xpath_list, date_obj, label):
            for date_fmt, date_str in [(date_fmt_2, date_obj.strftime(date_fmt_2)), (date_fmt_4, date_obj.strftime(date_fmt_4))]:
                for xpath in xpath_list:
                    try:
                        input_el = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                        if not input_el.is_displayed():
                            continue
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_el)
                        self.driver.execute_script("arguments[0].removeAttribute('readonly');", input_el)
                        self.driver.execute_script("arguments[0].removeAttribute('disabled');", input_el)
                        input_el.click()
                        time.sleep(0.2)
                        input_el.send_keys(Keys.CONTROL + "a")
                        input_el.send_keys(Keys.BACKSPACE)
                        input_el.send_keys(date_str)
                        time.sleep(0.5)
                        input_el.send_keys(Keys.TAB)
                        self.driver.execute_script("var el = arguments[0]; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true }));", input_el)
                        current = (input_el.get_attribute("value") or "").strip()
                        if date_str in current or date_str.replace("/", "-") in current:
                            if self.logger:
                                self.logger.info(f"      ✅ {label} (input): {current or date_str}")
                            return True
                    except Exception:
                        continue
            return False

        try:
            # FILTRO #1 primero: por posición (1º input), luego placeholder From
            if not find_and_set_date([xpath_1st, xpath_from, xpath_from_fb], fecha_inicio, "filtro #1 (fecha desde)"):
                self._save_screenshot_on_failure("fail_set_filtro_1_fecha_desde")
                return False
            time.sleep(1)
            # Segundo filtro: por posición (2º input), luego placeholder Until
            if not find_and_set_date([xpath_2nd, xpath_until, xpath_until_fb], fecha_fin, "fecha fin"):
                self._save_screenshot_on_failure("fail_set_fecha_fin")
                return False
            time.sleep(0.5)
            try:
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except Exception:
                pass
            for xpath in ["//div[contains(@class, 'modal-body')]//button[contains(@class, 'btn-success') and normalize-space(.)='Ok']", "//button[contains(@class, 'btn-success') and normalize-space(.)='Ok']"]:
                try:
                    ok_btn = self.driver.find_element(By.XPATH, xpath)
                    if ok_btn.is_displayed():
                        self._safe_click(ok_btn)
                        if self.logger:
                            self.logger.info("   ✅ Clic en Ok para aplicar filtros.")
                        break
                except Exception:
                    continue
            time.sleep(2)
            return True
        except Exception as e:
            if self.logger:
                self.logger.warning(f"   ⚠️ Falló set date range: {e}")
            self._save_screenshot_on_failure("fail_set_date_range")
            return False

    def _verify_filters_applied(self, fecha_inicio, fecha_fin):
        """
        Comprueba que los inputs de fecha muestren el rango aplicado (después de Ok).
        Solo usa atributos del DOM: placeholder "From"/"Until" o posición (1º y 2º input p-calendar).
        Si no hay forma de leer, devolvemos True para no bloquear.
        """
        date_fmt = "%d/%m/%Y"
        expected_inicio = fecha_inicio.strftime(date_fmt)
        expected_fin = fecha_fin.strftime(date_fmt)
        try:
            # Por placeholder (atributo real en DOM)
            for placeholder, expected, log_name in [
                ("From", expected_inicio, "primer"),
                ("Until", expected_fin, "segundo"),
            ]:
                try:
                    el = self.driver.find_element(
                        By.XPATH,
                        f"//div[contains(@class, 'modal-body')]//input[@placeholder='{placeholder}']"
                    )
                    val = (el.get_attribute("value") or "").strip()
                    if expected in val or expected.replace("/", "-") in val:
                        if self.logger:
                            self.logger.info(f"   ✅ Verificación filtros ({log_name}): {val}")
                    elif val and self.logger:
                        self.logger.warning(f"   ⚠️ Filtro {log_name} muestra '{val}', esperado ~'{expected}'")
                except Exception:
                    try:
                        el = self.driver.find_element(By.XPATH, f"//input[@placeholder='{placeholder}']")
                        val = (el.get_attribute("value") or "").strip()
                        if expected in val or expected.replace("/", "-") in val:
                            if self.logger:
                                self.logger.info(f"   ✅ Verificación filtros ({log_name}): {val}")
                    except Exception:
                        pass
            # Por posición: 1º y 2º input con p-datepicker-trigger en modal
            try:
                inputs = self.driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class, 'modal-body')]//input[following-sibling::button[contains(@class, 'p-datepicker-trigger')]]"
                )
                for i, (inp, exp) in enumerate([(inputs[0], expected_inicio), (inputs[1], expected_fin)], 1):
                    if inp and inp.is_displayed():
                        val = (inp.get_attribute("value") or "").strip()
                        if exp in val or exp.replace("/", "-") in val:
                            if self.logger:
                                self.logger.info(f"   ✅ Verificación filtros (input {i}): {val}")
            except Exception:
                pass
            return True
        except Exception as e:
            if self.logger:
                self.logger.warning(f"   ⚠️ Verificación filtros: {e}")
            return True

    def _navigate_calendar_to_date(self, target_date, panel=None):
        """
        Navega el widget de calendario al mes/año correcto usando el header del panel:
        p-datepicker-prev (Previous Month), p-datepicker-month, p-datepicker-year, p-datepicker-next.
        Si panel está definido, todas las búsquedas son dentro de ese elemento (evita otro datepicker).
        """
        root = panel if panel else self.driver
        xpath_prefix = ".//" if panel else "//"
        try:
            if not panel:
                self.wait.until(EC.presence_of_element_located((
                    By.XPATH, "//button[contains(@class, 'p-datepicker-month')]"
                )))
            time.sleep(0.5)
            target_month = target_date.month - 1
            target_year = target_date.year

            current_month_element = root.find_element(By.XPATH, xpath_prefix + "button[contains(@class, 'p-datepicker-month')]")
            current_month_text = current_month_element.text.strip()

            current_year_element = root.find_element(By.XPATH, xpath_prefix + "button[contains(@class, 'p-datepicker-year')]")
            current_year_text = current_year_element.text.strip()
            current_year = int(current_year_text)

            meses = {
                'january': 0, 'february': 1, 'march': 2, 'april': 3,
                'may': 4, 'june': 5, 'july': 6, 'august': 7,
                'september': 8, 'october': 9, 'november': 10, 'december': 11,
                'enero': 0, 'febrero': 1, 'marzo': 2, 'abril': 3,
                'mayo': 4, 'junio': 5, 'julio': 6, 'agosto': 7,
                'septiembre': 8, 'octubre': 9, 'noviembre': 10, 'diciembre': 11
            }
            current_month = meses.get(current_month_text.lower().strip(), 0)
            months_diff = (target_year - current_year) * 12 + (target_month - current_month)

            if self.logger:
                self.logger.info(f"         📍 Calendario actual: {current_month_text} {current_year}")
                self.logger.info(f"         🎯 Objetivo: {target_date.strftime('%B %Y')} (diferencia: {months_diff} meses)")

            if months_diff < 0:
                if self.logger:
                    self.logger.info(f"         ⬅️ Navegando {abs(months_diff)} meses hacia atrás...")
                for _ in range(abs(months_diff)):
                    prev_btn = root.find_element(By.XPATH, xpath_prefix + "button[contains(@class, 'p-datepicker-prev')]")
                    self._safe_click(prev_btn)
                    time.sleep(0.7)
            elif months_diff > 0:
                if self.logger:
                    self.logger.info(f"         ➡️ Navegando {months_diff} meses hacia adelante...")
                for _ in range(months_diff):
                    next_btn = root.find_element(By.XPATH, xpath_prefix + "button[contains(@class, 'p-datepicker-next')]")
                    self._safe_click(next_btn)
                    time.sleep(0.7)
            else:
                if self.logger:
                    self.logger.info("         ✅ Ya estamos en el mes correcto")

            if self.logger:
                self.logger.info(f"         ✅ Calendario navegado a {target_date.strftime('%B %Y')}")
        except Exception as e:
            if self.logger:
                self.logger.warning(f"         ⚠️ Error al navegar calendario: {str(e)}")

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
        except Exception:
            # Intentar método alternativo
            try:
                day_element = self.driver.find_element(
                    By.XPATH,
                    f"//td[contains(@aria-label, '{day}')]//span"
                )
                day_element.click()
                time.sleep(0.5)
            except Exception:
                pass

    def _safe_click(self, element):
        """Click por JavaScript para evitar crash del driver en headless (Chromium/Edge)."""
        try:
            self.driver.execute_script("arguments[0].click();", element)
        except Exception:
            element.click()

    def _save_screenshot_on_failure(self, prefix="fail_click"):
        """Guarda captura de pantalla en results/screenshots para diagnóstico. Retorna ruta o None."""
        try:
            screenshots_dir = Path(settings.BASE_DIR) / "results" / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = screenshots_dir / f"{prefix}_{ts}.png"
            self.driver.save_screenshot(str(path))
            if self.logger:
                self.logger.warning(f"   📷 Screenshot guardado: {path}")
            return str(path)
        except Exception as e:
            if self.logger:
                self.logger.warning(f"   ⚠️ No se pudo guardar screenshot: {e}")
            return None

    def _click_download_action(self):
        """
        Clic en Acciones/Actions -> Órdenes con Productos / Orders with Products -> Confirmar.
        Selectores por clase/atributos para funcionar en español e inglés.
        """
        from selenium.common.exceptions import TimeoutException
        # Dropdown Acciones: <a class="dropdown-toggle btn btn-light"> con texto "Actions" o "Acciones"
        dropdown_selectors = [
            (By.CSS_SELECTOR, "a.dropdown-toggle.btn.btn-light"),
            (By.CSS_SELECTOR, "a[ngbdropdowntoggle].btn.btn-light"),
            (By.XPATH, "//a[contains(@class, 'dropdown-toggle') and contains(@class, 'btn-light') and (contains(., 'Actions') or contains(., 'Acciones'))]"),
        ]
        wait_primary = get_downloader_wait_timeout()
        wait_retry = 25
        dropdown = None
        try:
            for i, (by, selector) in enumerate(dropdown_selectors):
                wait_sec = wait_primary if i == 0 else wait_retry
                w = WebDriverWait(self.driver, wait_sec)
                try:
                    dropdown = w.until(EC.presence_of_element_located((by, selector)))
                    if self.logger and i > 0:
                        self.logger.info(f"   ✅ Dropdown Acciones encontrado con selector alternativo #{i + 1}")
                    break
                except TimeoutException:
                    if self.logger:
                        self.logger.warning(f"   ⏳ Selector #{i + 1} sin resultado (timeout {wait_sec}s), probando siguiente...")
                    continue
            if dropdown is None:
                self._save_screenshot_on_failure("fail_acciones_dropdown")
                if self.logger:
                    self.logger.error("   ❌ No se encontró el dropdown Acciones con ningún selector.")
                return False
            self._safe_click(dropdown)
            time.sleep(1)
            # Opción: button.dropdown-item con texto "Orders with Products" o "Órdenes con Productos"
            option = self.wait.until(EC.presence_of_element_located((
                By.XPATH,
                "//button[contains(@class, 'dropdown-item') and (contains(., 'Orders with Products') or contains(., 'Órdenes con Productos'))]"
            )))
            self._safe_click(option)
            time.sleep(0.5)
            confirm = self.wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, "button.swal2-confirm"
            )))
            self._safe_click(confirm)
            self.wait.until(EC.url_contains("/dashboard/reports/downloads"))
            return True
        except Exception as e:
            self._save_screenshot_on_failure("fail_click_download")
            if self.logger:
                import traceback
                exc_type = type(e).__name__
                msg = str(e).strip() if str(e).strip() else "(mensaje vacío)"
                self.logger.error(f"   ❌ Error click descarga: {exc_type}: {msg}")
                self.logger.error("Traceback: %s", traceback.format_exc())
            return False

    def _wait_for_report_and_download(self, max_wait_time=300):
        """
        Espera en la tabla de descargas a que aparezca 'Listo' y hace click
        
        Args:
            max_wait_time: Tiempo máximo de espera en segundos (default: 5 minutos)
        
        Returns:
            str: Ruta del archivo descargado o None si falló
        """
        if self.logger:
            self.logger.info("   ⏳ Esperando a que el reporte esté listo...")
        
        start_time = time.time()
        check_interval = 5  # Verificar cada 5 segundos
        refresh_interval = 20  # Refrescar página cada 20 segundos
        
        while time.time() - start_time < max_wait_time:
            # Refrescar página si ha pasado el tiempo
            if int(time.time() - start_time) % refresh_interval == 0:
                if self.logger:
                    self.logger.info("      🔄 Refrescando página para actualizar lista...")
                self.driver.refresh()
                time.sleep(5)
            
            try:
                # Buscar la primera fila de la tabla
                rows = self.driver.find_elements(
                    By.XPATH,
                    "//tbody//tr[contains(@class, 'table-row')]"
                )
                
                if rows:
                    first_row = rows[0]
                    
                    # 1. Verificar Fecha (Debe ser HOY)
                    try:
                        date_label = first_row.find_element(By.CSS_SELECTOR, ".date-label span").text.strip()
                        # Formato esperado: "26-01-2026"
                        today_formatted = datetime.now().strftime("%d-%m-%Y")
                        
                        if today_formatted not in date_label:
                            if self.logger:
                                self.logger.info(f"         ⚠️ El primer reporte es de {date_label}, se esperaba {today_formatted}. Esperando nuevo...")
                            # Si la fecha no coincide, es que el nuevo reporte aún no aparece en la lista
                            time.sleep(2)  # Pequeña espera por si es renderizado
                            continue 
                    except Exception:
                        pass # Si falla lectura de fecha, continuamos a verificar estado por seguridad

                    # 2. Verificar estado "Ready"
                    estado_xpath = ".//app-dropi-tag//span"
                    estado_tags = first_row.find_elements(By.XPATH, estado_xpath)
                    
                    is_ready = False
                    estado_texto = "Desconocido"
                    
                    for tag in estado_tags:
                        txt = tag.text.strip()
                        estado_texto = txt
                        if txt.lower() in ['listo', 'ready', 'completed', 'success', 'hecho']:
                            is_ready = True
                            break
                    
                    if is_ready:
                        if self.logger:
                            self.logger.info(f"         ✅ Reporte verificado: Fecha HOY y Estado '{estado_texto}'")
                        
                        # Buscar botón de descarga
                        found_btn = False
                        try:
                            # Intento 1: Buscando por el SVG específico (más preciso en estructuras PrimeNG)
                            btn = first_row.find_element(By.XPATH, ".//*[local-name()='use' and contains(@xlink:href, 'File-download')]/ancestor::app-icon")
                            if btn.is_displayed():
                                btn.click()
                                found_btn = True
                        except Exception:
                            pass
                        
                        if not found_btn:
                            try:
                                # Intento 2: Por clase simple (fallback)
                                download_btns = first_row.find_elements(By.CSS_SELECTOR, "app-icon.action-icon")
                                if download_btns:
                                    download_btns[0].click()
                                    found_btn = True
                            except Exception:
                                pass
                        
                        if found_btn:
                            if self.logger:
                                self.logger.info("         ⬇️ Click en descargar realizado")
                            
                            # Esperar archivo en disco
                            return self._find_downloaded_file()
                        else:
                             # Si está listo pero no hay botón, es un glitch visual -> Refrescar
                            if self.logger:
                                self.logger.warning("         ⚠️ Reporte 'Ready' pero sin botón de descarga. Refrescando...")
                            self.driver.refresh()
                            time.sleep(5)
                            continue
                    else:
                        # Si está generando, refrescar inmediatamente (Solicitud Usuario)
                        if any(x in estado_texto.lower() for x in ['generando', 'generating', 'processing', 'proceso']):
                            if self.logger:
                                self.logger.info(f"         🔄 Reporte en generación ({estado_texto}). Refrescando inmediatamente...")
                            self.driver.refresh()
                            time.sleep(2) # Pequeña pausa para carga
                            continue
                        
                        if self.logger:
                            self.logger.info(f"         ⏳ Reporte en proceso (Estado: {estado_texto}), esperando...")
                else:
                    if self.logger:
                        self.logger.info("         ℹ️ No se encontraron reportes en la lista")
                
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"      ⚠️ Error en verificación: {str(e)}")
            
            # Solo esperar si NO se refrescó arriba
            time.sleep(check_interval)
        
        if self.logger:
            self.logger.error("   ❌ Tiempo de espera agotado. El reporte no se generó a tiempo.")
        return None

    def _find_downloaded_file(self, expected_filename=None, timeout=30):
        """
        Busca el archivo descargado en el directorio de descargas con reintentos.
        
        Args:
            expected_filename: Nombre esperado del archivo (opcional)
            timeout: Tiempo máximo de espera en segundos para que aparezca el archivo
        
        Returns:
            str: Ruta completa del archivo o None si no se encuentra
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
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
                
                # Verificar que el archivo no esté en uso/descarga (tamaño > 0)
                try:
                    if os.path.getsize(latest_file) > 0:
                        # Verificar que sea reciente (descargado en los últimos 2 minutos)
                        file_time = os.path.getmtime(latest_file)
                        if time.time() - file_time < 120:
                            # Esperar un momento extra para asegurar escritura completa
                            time.sleep(1)
                            return latest_file
                except Exception:
                    pass
            
            # Si no se encontró, esperar y reintentar
            time.sleep(1)
            
        return None

    def _read_excel_full(self, file_path):
        """Lee el Excel completo: usa la hoja con más filas. Devuelve (DataFrame, dict col_std -> nombre_real)."""
        xl = pd.ExcelFile(file_path)
        sheet_names = xl.sheet_names
        best_df = None
        best_rows = 0
        for sn in sheet_names:
            df = pd.read_excel(xl, sheet_name=sn, header=0)
            df.columns = [str(c).strip() for c in df.columns]
            if len(df) > best_rows:
                best_rows = len(df)
                best_df = df.copy()
        if best_df is None:
            best_df = pd.DataFrame()

        def norm(s):
            return str(s).strip().upper().replace('Ú', 'U').replace('É', 'E').replace('Á', 'A').replace('Í', 'I').replace('Ó', 'O')

        col_map = {}
        # Solo columnas con datos útiles para análisis (omitimos mayormente vacías o no relevantes)
        standards = [
            'ID', 'FECHA', 'FECHA DE REPORTE', 'HORA', 'PRODUCTO', 'PRODUCTO ID', 'SKU', 'VARIACION',
            'NUMERO DE PEDIDO DE TIENDA', 'CANTIDAD', 'TOTAL DE LA ORDEN', 'PRECIO FLETE', 'PRECIO PROVEEDOR',
            'ESTATUS', 'NUMERO GUIA', 'NÚMERO GUIA', 'TRANSPORTADORA', 'NOMBRE CLIENTE', 'TELÉFONO', 'TELEFONO',
            'EMAIL', 'CIUDAD DESTINO', 'DEPARTAMENTO DESTINO', 'DIRECCION', 'TIPO DE TIENDA', 'TIENDA'
        ]
        for std in standards:
            for c in best_df.columns:
                if norm(c) == norm(std):
                    col_map[std] = c
                    break
            if std not in col_map:
                col_map[std] = std
        return best_df, col_map

    def _row_val(self, row, col_map, *keys):
        """Obtiene valor de la fila por clave estándar."""
        for k in keys:
            if k in col_map:
                c = col_map[k]
                if c in row.index:
                    val = row.get(c)
                    if pd.notna(val):
                        return val
        return None

    def _process_excel_to_db(self, file_path, report_date):
        """
        Lee el archivo Excel descargado y guarda los datos en la base de datos.
        Elimina el archivo después de procesarlo.
        
        Args:
            file_path: Ruta del archivo Excel
            report_date: Fecha del reporte (datetime)
        """
        try:
            if not self.user:
                return
            
            if self.logger:
                self.logger.info(f"   💾 Guardando en BD: {Path(file_path).name}")
            
            # Obtener email de Dropi del usuario
            account_email = self.user.dropi_email or "unknown@dropi.co"
            
            # Crear nuevo Batch
            batch = ReportBatch.objects.create(
                user=self.user,
                account_email=account_email,
                status="PROCESSING",
                total_records=0
            )
            
            if self.logger:
                self.logger.info(f"   ✅ Lote creado: ID {batch.id}")
            
            # Leer Excel completo (hoja con más filas, todas las filas)
            df, col_map = self._read_excel_full(file_path)

            if df.empty:
                if self.logger:
                    self.logger.warning("   ⚠️ El archivo Excel está vacío")
                batch.status = "FAILED"
                batch.save()
                return

            total_rows = len(df)
            if self.logger:
                self.logger.info(f"   📊 Filas en Excel: {total_rows} (guardando todas)")

            batch_size = 500
            snapshots = []
            rows_processed = 0
            rows_synthetic_id = 0

            for idx, row in df.iterrows():
                try:
                    # ID: usar real o sintético para no omitir ninguna fila
                    dropi_id_raw = self._row_val(row, col_map, 'ID') or ''
                    dropi_id = str(dropi_id_raw).strip()
                    if not dropi_id or dropi_id.lower() == 'nan' or dropi_id == '':
                        dropi_id = f"NO-ID-{idx}"
                        rows_synthetic_id += 1
                    else:
                        try:
                            int(dropi_id)
                        except (ValueError, TypeError):
                            dropi_id = f"NO-ID-{idx}"
                            rows_synthetic_id += 1
                    dropi_id = (dropi_id or f"NO-ID-{idx}")[:100]

                    # Parse fecha venta
                    fecha_val = self._row_val(row, col_map, 'FECHA')
                    order_date_obj = None
                    if pd.notna(fecha_val):
                        if isinstance(fecha_val, str):
                            for fmt in ['%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d']:
                                try:
                                    order_date_obj = datetime.strptime(fecha_val, fmt).date()
                                    break
                                except Exception:
                                    continue
                        else:
                            try:
                                order_date_obj = fecha_val.date()
                            except Exception:
                                pass
                    
                    # Validar producto
                    raw_product = self._row_val(row, col_map, 'PRODUCTO')
                    if pd.notna(raw_product):
                        if isinstance(raw_product, (datetime, pd.Timestamp)):
                            product_name = raw_product.strftime('%Y-%m-%d')
                        else:
                            product_name = str(raw_product).strip()
                    else:
                        product_name = "Sin Producto"
                    
                    # Validar shopify_order_id
                    shopify_id_raw = self._row_val(row, col_map, 'NUMERO DE PEDIDO DE TIENDA') or ''
                    shopify_order_id = None
                    if pd.notna(shopify_id_raw):
                        shopify_order_id = str(shopify_id_raw).split('.')[0].strip()
                        if shopify_order_id == '' or shopify_order_id.lower() == 'nan':
                            shopify_order_id = None
                    
                    # Validar cantidad
                    quantity = 1
                    try:
                        cantidad_raw = self._row_val(row, col_map, 'CANTIDAD') or 1
                        if pd.notna(cantidad_raw):
                            quantity = int(float(cantidad_raw))
                    except (ValueError, TypeError):
                        quantity = 1
                    
                    # Validar total_amount
                    total_amount = 0.0
                    try:
                        total_raw = self._row_val(row, col_map, 'TOTAL DE LA ORDEN') or 0
                        if pd.notna(total_raw):
                            total_amount = float(total_raw)
                    except (ValueError, TypeError):
                        total_amount = 0.0
                    
                    # Validar longitudes de campos
                    current_status_val = str(self._row_val(row, col_map, 'ESTATUS') or 'PENDIENTE').strip()[:100]
                    guide_num_raw = self._row_val(row, col_map, 'NÚMERO GUIA', 'NUMERO GUIA')
                    guide_num = str(guide_num_raw).strip()[:100] if pd.notna(guide_num_raw) and str(guide_num_raw).strip() else None
                    carrier_raw = self._row_val(row, col_map, 'TRANSPORTADORA')
                    carrier_val = str(carrier_raw).strip()[:100] if pd.notna(carrier_raw) and str(carrier_raw).strip() else None
                    customer_name_raw = self._row_val(row, col_map, 'NOMBRE CLIENTE')
                    customer_name_val = str(customer_name_raw).strip()[:255] if pd.notna(customer_name_raw) and str(customer_name_raw).strip() else None
                    customer_phone_raw = self._row_val(row, col_map, 'TELÉFONO', 'TELEFONO')
                    customer_phone_val = str(customer_phone_raw).strip()[:50] if pd.notna(customer_phone_raw) and str(customer_phone_raw).strip() else None
                    city_raw = self._row_val(row, col_map, 'CIUDAD DESTINO')
                    city_val = str(city_raw).strip()[:100] if pd.notna(city_raw) and str(city_raw).strip() else None
                    department_raw = self._row_val(row, col_map, 'DEPARTAMENTO DESTINO')
                    department_val = str(department_raw).strip()[:100] if pd.notna(department_raw) and str(department_raw).strip() else None
                    address_raw = self._row_val(row, col_map, 'DIRECCION')
                    address_val = str(address_raw).strip() if pd.notna(address_raw) and str(address_raw).strip() else None

                    # Campos adicionales para análisis
                    def _parse_date(val):
                        if val is None or (isinstance(val, float) and pd.isna(val)):
                            return None
                        if isinstance(val, str):
                            for fmt in ['%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d']:
                                try:
                                    return datetime.strptime(val.strip(), fmt).date()
                                except Exception:
                                    continue
                        try:
                            return val.date() if hasattr(val, 'date') else None
                        except Exception:
                            return None

                    def _decimal(val, default=None):
                        if val is None or (isinstance(val, float) and pd.isna(val)) or val == '':
                            return default
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            return default

                    report_date_obj = _parse_date(self._row_val(row, col_map, 'FECHA DE REPORTE'))
                    order_time_val = self._row_val(row, col_map, 'HORA')
                    order_time_str = str(order_time_val).strip()[:20] if pd.notna(order_time_val) and str(order_time_val).strip() and str(order_time_val) != 'nan' else None
                    customer_email_raw = self._row_val(row, col_map, 'EMAIL')
                    customer_email_val = str(customer_email_raw).strip()[:255] if pd.notna(customer_email_raw) and str(customer_email_raw).strip() and str(customer_email_raw) != 'nan' else None
                    shipping_price_val = _decimal(self._row_val(row, col_map, 'PRECIO FLETE'))
                    supplier_price_val = _decimal(self._row_val(row, col_map, 'PRECIO PROVEEDOR'))
                    product_id_val = str(self._row_val(row, col_map, 'PRODUCTO ID') or '').strip()[:100] or None
                    sku_val = str(self._row_val(row, col_map, 'SKU') or '').strip()[:100] or None
                    variation_val = str(self._row_val(row, col_map, 'VARIACION') or '').strip()[:255] or None
                    store_type_val = str(self._row_val(row, col_map, 'TIPO DE TIENDA') or '').strip()[:50] or None
                    store_name_val = str(self._row_val(row, col_map, 'TIENDA') or '').strip()[:100] or None

                    # GANANCIA calculada: total - flete - proveedor (no se extrae del Excel)
                    profit_val = None
                    if total_amount is not None and shipping_price_val is not None and supplier_price_val is not None:
                        try:
                            profit_val = total_amount - shipping_price_val - supplier_price_val
                        except (TypeError, ValueError):
                            pass

                    # Crear snapshot
                    snapshot = RawOrderSnapshot(
                        batch=batch,
                        dropi_order_id=dropi_id[:100],
                        shopify_order_id=shopify_order_id[:100] if shopify_order_id else None,
                        guide_number=guide_num,
                        current_status=current_status_val,
                        carrier=carrier_val,
                        customer_name=customer_name_val,
                        customer_phone=customer_phone_val,
                        customer_email=customer_email_val,
                        address=address_val,
                        city=city_val,
                        department=department_val,
                        product_name=product_name[:500],
                        product_id=product_id_val,
                        sku=sku_val,
                        variation=variation_val,
                        quantity=quantity,
                        total_amount=total_amount,
                        profit=profit_val,
                        shipping_price=shipping_price_val,
                        supplier_price=supplier_price_val,
                        store_type=store_type_val,
                        store_name=store_name_val,
                        order_date=order_date_obj,
                        order_time=order_time_str,
                        report_date=report_date_obj,
                    )
                    snapshots.append(snapshot)
                    rows_processed += 1
                    
                    # Inserción controlada
                    if len(snapshots) >= batch_size:
                        try:
                            RawOrderSnapshot.objects.bulk_create(snapshots)
                            if self.logger:
                                self.logger.info(f"      📥 Insertados {batch_size} registros... (Total procesados: {rows_processed})")
                        except Exception as bulk_error:
                            if self.logger:
                                self.logger.error(f"      ❌ Error en bulk_create: {str(bulk_error)}")
                            # Intentar insertar uno por uno
                            for snap in snapshots:
                                try:
                                    snap.save()
                                except Exception:
                                    pass
                        snapshots = []
                        
                except Exception as row_error:
                    if self.logger:
                        self.logger.error(f"      ❌ Error en fila {idx}: {str(row_error)}")
                    continue
            
            # Insertar los que queden
            if snapshots:
                try:
                    RawOrderSnapshot.objects.bulk_create(snapshots)
                    if self.logger:
                        self.logger.info(f"      📥 Insertados restantes {len(snapshots)} registros")
                except Exception:
                    for snap in snapshots:
                        try:
                            snap.save()
                        except Exception:
                            pass

            snapshots_count = RawOrderSnapshot.objects.filter(batch_id=batch.id).count()
            batch.total_records = snapshots_count
            batch.status = "SUCCESS" if snapshots_count > 0 else "FAILED"
            batch.save()

            if self.logger:
                self.logger.info(f"   ✅ Lote {batch.id} guardado: {snapshots_count} registros (Excel: {total_rows} filas)")
                if rows_synthetic_id:
                    self.logger.info(f"   ℹ️ Filas con ID sintético (sin ID en Excel): {rows_synthetic_id}")
            
            # Borrar archivo
            try:
                os.remove(file_path)
                if self.logger:
                    self.logger.info(f"   🗑️ Archivo eliminado: {Path(file_path).name}")
            except Exception:
                pass
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error DB: {e}")
            if 'batch' in locals():
                batch.status = "FAILED"
                batch.save()
