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
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from core.models import ReportBatch, RawOrderSnapshot, User


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
        self.wait = WebDriverWait(driver, 30)
        
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
        
        # PASO 1: Validar si existe reporte generado AYER
        # El comparador necesita el reporte de ayer y de hoy para verificar estancados.
        # Si el usuario no ejecutó el bot ayer, necesitamos descargar ese reporte hoy.
        
        yesterday = datetime.now().date() - timedelta(days=1)
        
        # Verificar si existe un batch exitoso con fecha de creación = AYER
        exists_batch_yesterday = ReportBatch.objects.filter(
            user_id=self.user_id,
            status='SUCCESS',
            created_at__year=yesterday.year,
            created_at__month=yesterday.month,
            created_at__day=yesterday.day
        ).exists()
        
        dates_to_download = []
        
        if not exists_batch_yesterday:
            if self.logger:
                self.logger.info("   📋 No se detectó ejecución ayer -> Agendando descarga de reporte de AYER.")
            dates_to_download.append(datetime.now() - timedelta(days=1))
        else:
            if self.logger:
                self.logger.info("   📋 Reporte de ayer detectado en BD -> Omitiendo descarga de ayer.")
        
        # Siempre descargar el reporte de HOY
        dates_to_download.append(datetime.now())
        
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
            label = "AYER" if report_date.date() < datetime.now().date() else "HOY"
            
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
        
        # 2. Setear fechas
        if not self._set_date_range(start_date, end_date):
            return None
        
        # 3. Click Descargar
        if not self._click_download_action():
            return None
        
        # 4. Esperar y Descargar (Manejo de Modal + Espera de archivo)
        return self._wait_for_report_and_download()

    def _open_filters(self):
        """Abre panel de filtros"""
        try:
            filter_button = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class, 'btn-success') and contains(@title, 'Mostrar Filtros')]"
                ))
            )
            filter_button.click()
            time.sleep(1.5)
            return True
        except Exception:
            return False

    def _set_date_range(self, fecha_inicio, fecha_fin):
        """
        Configura fechas tratando de escribir directamente en los inputs (bypass readonly).
        Es mucho más robusto que navegar el widget de calendario.
        """
        try:
            if self.logger:
                self.logger.info(f"   📅 Configurando rango de fechas (JS Injection)...")
                self.logger.info(f"      Desde: {fecha_inicio.strftime('%d/%m/%Y')}")
                self.logger.info(f"      Hasta: {fecha_fin.strftime('%d/%m/%Y')}")
            
            def set_date_via_js(placeholders, date_obj):
                """Helper para inyectar fecha"""
                xpath = " | ".join([f"//input[contains(@placeholder, '{p}')]" for p in placeholders])
                
                input_el = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                
                # 1. Quitar readonly y disabled
                self.driver.execute_script("arguments[0].removeAttribute('readonly');", input_el)
                self.driver.execute_script("arguments[0].removeAttribute('disabled');", input_el)
                
                # 2. Limpiar y Escribir
                date_str = date_obj.strftime("%d/%m/%Y")
                input_el.click()
                input_el.send_keys(Keys.CONTROL + "a")
                input_el.send_keys(Keys.BACKSPACE)
                input_el.send_keys(date_str)
                time.sleep(0.5)
                input_el.send_keys(Keys.TAB)
                
                # 3. Disparar eventos JS para notificar a Angular
                self.driver.execute_script("""
                    let evInput = new Event('input', { bubbles: true });
                    let evChange = new Event('change', { bubbles: true });
                    arguments[0].dispatchEvent(evInput);
                    arguments[0].dispatchEvent(evChange);
                """, input_el)
            
            # --- 1. DESDE ---
            set_date_via_js(['From', 'Desde'], fecha_inicio)
            time.sleep(1)
            
            # --- 2. HASTA ---
            # Si es hoy, Dropi ya lo pone por defecto, pero forzamos para asegurar
            if fecha_fin.date() != datetime.now().date():
                set_date_via_js(['Until', 'Hasta'], fecha_fin)
                time.sleep(1)
            
            # Cerrar cualquier popup que haya quedado (send keys Escape al body)
            try:
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            except:
                pass
                
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"   ⚠️ Falló set date range UI (JS): {e}")
            return False

    def _navigate_calendar_to_date(self, target_date):
        """
        Navega el widget de calendario al mes/año correcto
        
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
            time.sleep(0.5)
            
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
                'september': 8, 'october': 9, 'november': 10, 'december': 11,
                'enero': 0, 'febrero': 1, 'marzo': 2, 'abril': 3,
                'mayo': 4, 'junio': 5, 'julio': 6, 'agosto': 7,
                'septiembre': 8, 'octubre': 9, 'noviembre': 10, 'diciembre': 11
            }
            current_month = meses.get(current_month_text.lower(), 0)
            
            # Calcular diferencia en meses
            months_diff = (target_year - current_year) * 12 + (target_month - current_month)
            
            if self.logger:
                self.logger.info(f"         📍 Calendario actual: {current_month_text} {current_year}")
                self.logger.info(f"         🎯 Objetivo: {target_date.strftime('%B %Y')} (diferencia: {months_diff} meses)")
            
            # Navegar hacia atrás o adelante
            if months_diff < 0:
                # Ir hacia atrás
                if self.logger:
                    self.logger.info(f"         ⬅️ Navegando {abs(months_diff)} meses hacia atrás...")
                for i in range(abs(months_diff)):
                    prev_button = self.wait.until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            "//button[contains(@class, 'p-datepicker-prev')]"
                        ))
                    )
                    prev_button.click()
                    time.sleep(0.7)
            elif months_diff > 0:
                # Ir hacia adelante
                if self.logger:
                    self.logger.info(f"         ➡️ Navegando {months_diff} meses hacia adelante...")
                for i in range(months_diff):
                    next_button = self.wait.until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            "//button[contains(@class, 'p-datepicker-next')]"
                        ))
                    )
                    next_button.click()
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

    def _click_download_action(self):
        """
        Clic en Acciones -> Órdenes con Productos -> Confirmar
        
        Returns:
            bool: True si fue exitoso
        """
        try:
            # Dropdown Acciones
            dropdown = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//a[contains(@class, 'dropdown-toggle') and contains(normalize-space(.), 'Acciones')]"
            )))
            dropdown.click()
            time.sleep(1)
            
            # Opción Reporte (Soporte Bilingüe)
            # El usuario indicó explícitamente: Orders with Products (One product per row)
            option = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, 
                "//button[contains(normalize-space(.), 'Órdenes con Productos') or contains(normalize-space(.), 'Orders with Products')]"
            )))
            option.click()
            
            # Modal Confirmación
            confirm = self.wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, "button.swal2-confirm"
            )))
            confirm.click()
            
            # Esperar redirección
            self.wait.until(EC.url_contains("/dashboard/reports/downloads"))
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"   ❌ Error click descarga: {e}")
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
            
            # Leer Excel
            df = pd.read_excel(file_path)
            df.columns = [str(c).strip() for c in df.columns]
            
            if df.empty:
                if self.logger:
                    self.logger.warning("   ⚠️ El archivo Excel está vacío")
                batch.status = "FAILED"
                batch.save()
                return
            
            total_rows = len(df)
            if self.logger:
                self.logger.info(f"   📊 Filas encontradas: {total_rows}")
            
            # Procesar en lotes
            batch_size = 500
            snapshots = []
            rows_processed = 0
            rows_skipped = 0
            
            for idx, row in df.iterrows():
                try:
                    # Validar ID
                    dropi_id_raw = row.get('ID', '')
                    dropi_id = str(dropi_id_raw).strip()
                    if not dropi_id or dropi_id.lower() == 'nan' or dropi_id == '':
                        rows_skipped += 1
                        continue
                    
                    # Validar que sea numérico
                    try:
                        int(dropi_id)
                    except (ValueError, TypeError):
                        rows_skipped += 1
                        continue
                    
                    # Parse fecha venta
                    fecha_val = row.get('FECHA')
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
                    raw_product = row.get('PRODUCTO')
                    if pd.notna(raw_product):
                        if isinstance(raw_product, (datetime, pd.Timestamp)):
                            product_name = raw_product.strftime('%Y-%m-%d')
                        else:
                            product_name = str(raw_product).strip()
                    else:
                        product_name = "Sin Producto"
                    
                    # Validar shopify_order_id
                    shopify_id_raw = row.get('NUMERO DE PEDIDO DE TIENDA', '')
                    shopify_order_id = None
                    if pd.notna(shopify_id_raw):
                        shopify_order_id = str(shopify_id_raw).split('.')[0].strip()
                        if shopify_order_id == '' or shopify_order_id.lower() == 'nan':
                            shopify_order_id = None
                    
                    # Validar cantidad
                    quantity = 1
                    try:
                        cantidad_raw = row.get('CANTIDAD', 1)
                        if pd.notna(cantidad_raw):
                            quantity = int(float(cantidad_raw))
                    except (ValueError, TypeError):
                        quantity = 1
                    
                    # Validar total_amount
                    total_amount = 0.0
                    try:
                        total_raw = row.get('TOTAL DE LA ORDEN', 0)
                        if pd.notna(total_raw):
                            total_amount = float(total_raw)
                    except (ValueError, TypeError):
                        total_amount = 0.0
                    
                    # Validar longitudes de campos
                    current_status_val = str(row.get('ESTATUS', 'PENDIENTE')).strip()[:100]
                    guide_num = str(row.get('NÚMERO GUIA', '')).strip()[:100] if pd.notna(row.get('NÚMERO GUIA')) else None
                    carrier_val = str(row.get('TRANSPORTADORA', '')).strip()[:100] if pd.notna(row.get('TRANSPORTADORA')) else None
                    customer_name_val = str(row.get('NOMBRE CLIENTE', '')).strip()[:255] if pd.notna(row.get('NOMBRE CLIENTE')) else None
                    customer_phone_val = str(row.get('TELÉFONO', '')).strip()[:50] if pd.notna(row.get('TELÉFONO')) else None
                    city_val = str(row.get('CIUDAD DESTINO', '')).strip()[:100] if pd.notna(row.get('CIUDAD DESTINO')) else None
                    department_val = str(row.get('DEPARTAMENTO DESTINO', '')).strip()[:100] if pd.notna(row.get('DEPARTAMENTO DESTINO')) else None
                    address_val = str(row.get('DIRECCION', '')).strip() if pd.notna(row.get('DIRECCION')) else None
                    
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
                        address=address_val,
                        city=city_val,
                        department=department_val,
                        product_name=product_name[:500],
                        quantity=quantity,
                        total_amount=total_amount,
                        order_date=order_date_obj
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
                                    rows_skipped += 1
                        snapshots = []
                        
                except Exception as row_error:
                    rows_skipped += 1
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
                            rows_skipped += 1
            
            # Verificar registros insertados
            snapshots_count = RawOrderSnapshot.objects.filter(batch_id=batch.id).count()
            
            # Actualizar batch
            batch.total_records = snapshots_count
            batch.status = "SUCCESS" if snapshots_count > 0 else "FAILED"
            batch.save()
            
            if self.logger:
                self.logger.info(f"   ✅ Lote {batch.id} guardado ({snapshots_count} regs)")
            
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
