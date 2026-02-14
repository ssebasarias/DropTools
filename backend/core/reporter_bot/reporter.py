"""
Reporter - Orquestador principal del proceso de reporte

Este módulo coordina todos los módulos para generar reportes en Dropi:
1. Carga órdenes pendientes desde BD
2. Busca cada orden en la web
3. Valida estado
4. Completa el formulario de reporte
5. Maneja popups y errores
6. Guarda resultados en BD

Todo usando el driver compartido en una sesión persistente.
"""

import time
import pandas as pd
from datetime import datetime
from django.utils import timezone
from django.db import close_old_connections
from core.models import User, OrderReport
from selenium.common.exceptions import TimeoutException

from .order_data_loader import OrderDataLoader
from .order_searcher import OrderSearcher
from .report_form_handler import ReportFormHandler
from .popup_handler import PopupHandler
from .report_result_manager import ReportResultManager


class DropiReporter:
    """
    Orquestador principal del proceso de reporte.
    Coordina todos los módulos para generar reportes en Dropi.
    """
    
    ORDERS_URL = "https://app.dropi.co/dashboard/orders"
    
    def __init__(self, driver, user_id, logger, on_order_processed=None):
        """
        Inicializa el reporter

        Args:
            driver: WebDriver compartido (ya logueado)
            user_id: ID del usuario Django
            logger: Logger configurado
            on_order_processed: callback opcional (current_index, total, processed_count) para actualizar progreso en frontend
        """
        self.driver = driver
        self.user_id = user_id
        self.logger = logger
        self.on_order_processed = on_order_processed

        # Módulos
        self.data_loader = OrderDataLoader(user_id, logger)
        self.searcher = OrderSearcher(driver, logger)
        self.form_handler = ReportFormHandler(driver, logger)
        self.popup_handler = PopupHandler(driver, logger)
        self.result_manager = ReportResultManager(user_id, logger)
        
        # Estado
        self.session_expired = False
        
        # Estadísticas
        self.stats = {
            'total': 0,
            'procesados': 0,
            'ya_tienen_caso': 0,
            'errores': 0,
            'no_encontrados': 0,
            'saltados_por_tiempo': 0,
            'reintentos': 0
        }
    
    def run(self, orders_df=None):
        """
        Ejecuta el proceso completo de reporte.
        Si orders_df está definido, usa ese DataFrame en lugar de cargar desde BD (para rangos).
        Returns:
            dict: Estadísticas del proceso
        """
        self.logger.info("="*80)
        self.logger.info("🤖 INICIANDO BOT DE REPORTES DROPI (Unified Mode)")
        self.logger.info("="*80)
        
        try:
            # 1. Cargar datos desde BD o usar DataFrame proporcionado (slice de rango)
            if orders_df is not None:
                self.logger.info("🗄️ Modo: DataFrame proporcionado (rango)")
                df = orders_df
            else:
                self.logger.info("🗄️ Modo: Base de Datos (OrderMovementReport)")
                df = self.data_loader.load_pending_orders()
            
            if df.empty:
                self.logger.info("⚠️ No hay datos pendientes para procesar.")
                return self.stats

            self.logger.info(f"   📊 Registros cargados: {len(df)}")
            self.stats['total'] = len(df)
            
            # Guardar DataFrame para acceso rápido
            df_data = df.set_index('Teléfono', drop=False)
            
            # Obtener usuario
            user = User.objects.get(id=self.user_id)
            self.logger.info(f"👤 Usuario: {user.email} (ID: {user.id})")
            
            # Contar órdenes ya reportadas (histórico)
            reported_count = OrderReport.objects.filter(user=user, status='reportado').count()
            self.logger.info(f"📊 Histórico global reportado: {reported_count}")
            
            # 2. Navegar a Mis Pedidos (si no estamos ahí)
            if "/dashboard/orders" not in self.driver.current_url:
                self.logger.info("📍 Navegando a Mis Pedidos...")
                if not self._navigate_to_orders():
                    self.logger.error("❌ No se pudo navegar a Mis Pedidos")
                    return self.stats
                self.logger.info("✅ Navegado a Mis Pedidos exitosamente")
            
            # 3. Procesar cada orden
            self.logger.info("")
            self.logger.info(f"📊 Procesando {len(df)} órdenes")
            self.logger.info("")
            
            for idx, (index, row) in enumerate(df.iterrows()):
                close_old_connections()  # Safety
                
                phone = row['Teléfono']
                order_id = row.get('ID Orden')
                expected_state = row['Estado Actual']
                db_report_id = row.get('_db_report_id')
                
                self.logger.info("")
                self.logger.info(f"{'='*80}")
                self.logger.info(f"Procesando orden {idx + 1}/{len(df)}")
                self.logger.info(f"Teléfono: {phone} | ID: {order_id} | Estado: {expected_state}")
                self.logger.info(f"{'='*80}")
                
                # Verificar si la orden puede ser procesada
                can_process, time_info = self.data_loader.check_order_can_be_processed(phone)
                
                if not can_process:
                    reason = time_info.get('reason', 'unknown') if time_info else 'unknown'
                    if reason == 'already_reported':
                        self.logger.info(f"⏭️  Orden saltada - Ya fue reportada exitosamente")
                        if db_report_id:
                            self.logger.info(f"   💾 Auto-resolviendo registro DB actual (ya existía histórico).")
                            self.result_manager.mark_order_resolved(
                                db_report_id,
                                "Auto-resuelto: Ya existía en histórico"
                            )
                    elif reason == 'waiting_time':
                        self.logger.warning(f"⏳ Orden saltada - Falta tiempo para reintentar")
                    self.stats['saltados_por_tiempo'] += 1
                    continue
                
                # Obtener reporte previo si existe
                prev_report = self.data_loader._get_order_report(phone)
                retry_count = 0
                if prev_report:
                    retry_count = OrderReport.objects.filter(
                        user_id=self.user_id,
                        order_phone=phone
                    ).exclude(status='reportado').count()
                
                # Procesar orden
                result = self._process_single_order(
                    phone, expected_state, idx, order_id=order_id,
                    is_first_order=(idx == 0), retry_count=retry_count, db_report_id=db_report_id
                )
                
                # Actualizar DB (OrderMovementReport)
                if result['status'] == 'reportado' and db_report_id:
                    self.result_manager.mark_order_resolved(db_report_id)
                
                # Guardar traza histórica en OrderReport
                order_info = {
                    'customer_name': row.get('Cliente'),
                    'product_name': row.get('Producto'),
                    'order_id': row.get('ID Orden')
                }
                result['order_info'] = order_info
                self.result_manager.save_result(result, row)
                self.logger.info(f"   Orden {idx + 1}/{len(df)} terminada: status={result['status']}")

                # Notificar progreso para que el frontend actualice contador y panel
                if callable(self.on_order_processed):
                    try:
                        self.on_order_processed(idx + 1, len(df), self.stats['procesados'])
                    except Exception:
                        pass

                # Si hubo timeout y sesión expirada, salir
                if result['status'] == 'session_expired':
                    self.logger.warning("⚠️ Sesión expirada durante procesamiento")
                    break
                
                time.sleep(1)  # Pausa técnica
            
            self._print_final_stats()
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error fatal: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
        
        return self.stats
    
    def _navigate_to_orders(self):
        """Navega a la sección de Mis Pedidos"""
        try:
            self.logger.info("📍 Navegando a Mis Pedidos...")
            self.driver.get(self.ORDERS_URL)
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.url_contains("/dashboard/orders"))
            time.sleep(5)
            return True
        except Exception as e:
            self.logger.error(f"❌ Error navegando a pedidos: {e}")
            return False
    
    def _check_session_expired(self):
        """Verifica si la sesión está expirada"""
        try:
            token_exists = self.driver.execute_script("return !!localStorage.getItem('DROPI_token')")
            is_login_page = "/login" in self.driver.current_url
            
            if not token_exists or is_login_page:
                self.logger.warning("⚠️ Sesión expirada detectada")
                return True
            return False
        except Exception:
            return True
    
    def _process_single_order(self, phone, expected_state, line_number, order_id=None, is_first_order=False, retry_count=0, db_report_id=None):
        """
        Procesa una sola orden con manejo completo del flujo.
        
        Args:
            phone: Número de teléfono de la orden
            expected_state: Estado esperado de la orden
            line_number: Número de línea
            order_id: ID de la orden (opcional, preferido para búsqueda)
            is_first_order: Si es la primera orden
            retry_count: Número de reintentos
            db_report_id: ID del OrderMovementReport en la cola de trabajo
            
        Returns:
            dict con el resultado del procesamiento
        """
        result = {
            'line_number': line_number,
            'phone': str(phone),
            'order_id': str(order_id) if order_id else '',
            'db_report_id': db_report_id,
            'status_history_screenshot_path': None,
            'cas_chat_url': None,
            'cas_chat_id': None,
            'status': 'error',
            'report_generated': False,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'next_attempt_time': None,
            'retry_count': retry_count,
            'last_movement_date': None,
            'last_movement_status': None,
            'inactivity_days_real': None,
            'last_movement_raw_text': None,
        }
        
        try:
            # Verificar sesión
            if self.session_expired or self._check_session_expired():
                self.logger.warning("⚠️ Sesión expirada detectada")
                result['status'] = 'session_expired'
                return result
            
            # Navegar a Mis Pedidos si es necesario
            if is_first_order or "/dashboard/orders" not in self.driver.current_url:
                if not self._navigate_to_orders():
                    result['status'] = 'error'
                    result['message'] = 'Error al navegar a Mis Pedidos'
                    self.stats['errores'] += 1
                    return result
            
            # Buscar orden por teléfono (Dropi ya no muestra ID/guía en búsqueda, solo teléfono)
            if not self.searcher.search_order(str(phone).strip()):
                result['status'] = 'no_encontrado'
                self.stats['no_encontrados'] += 1
                return result
            
            # Validar estado; si hay varias órdenes del mismo cliente, hacer match por ID de orden
            if not self.searcher.validate_order_state(expected_state, order_id=order_id):
                result['status'] = 'error'
                self.stats['errores'] += 1
                return result
            
            # Obtener fila de la orden
            order_row = self.searcher.get_current_order_row()

            # Paso previo obligatorio: capturar Status History desde Información de la Orden
            history_capture = self.form_handler.capture_status_history_snapshot(
                order_row=order_row,
                order_id=order_id,
                phone=phone,
            )
            result['status_history_screenshot_path'] = history_capture.get('screenshot_path')
            if not history_capture.get('success'):
                self._handle_unexpected_error(
                    phone,
                    result,
                    retry_count,
                    "No se pudo capturar Status History (Información de la Orden)"
                )
                return result
            
            # Click en Nueva Consulta
            if not self.form_handler.click_new_consultation(order_row):
                self._handle_unexpected_error(phone, result, retry_count, "Nueva consulta (botón no disponible)")
                return result
            
            # Limpiar referencia a la fila
            self.searcher.clear_order_row()
            
            # Verificar popups inmediatamente
            popup_result = self.popup_handler.handle_existing_case_popup()
            
            if popup_result['found']:
                if popup_result['type'] == 'caso_existente':
                    result['status'] = 'reportado'
                    result['report_generated'] = True
                    result['next_attempt_time'] = None
                    self.stats['ya_tienen_caso'] += 1
                    self.form_handler.delete_temp_screenshot(result.get('status_history_screenshot_path'))
                    return result
                elif popup_result['type'] == 'estado_invalido':
                    self._handle_unexpected_error(phone, result, retry_count, "Popup estado no permitido")
                    return result
                else:
                    self._handle_unexpected_error(
                        phone,
                        result,
                        retry_count,
                        f"Popup inesperado: {popup_result.get('type')}"
                    )
                    return result
            
            # Flujo nuevo Dropi: opción única "Ordenes sin movimiento" (sin dropdowns)
            selection_result = self.form_handler.select_no_movement_option_and_capture_details()
            result['last_movement_date'] = selection_result.get('last_movement_date')
            result['last_movement_status'] = selection_result.get('last_movement_status')
            result['inactivity_days_real'] = selection_result.get('inactivity_days_real')
            result['last_movement_raw_text'] = selection_result.get('last_movement_raw_text')

            if not selection_result.get('selected'):
                self._handle_unexpected_error(phone, result, retry_count, "Selección de opción única (Ordenes sin movimiento)")
                return result
            
            # Verificar alert de espera
            if self.popup_handler.check_wait_time_alert():
                self.logger.warning("⚠️ Alert detectado: 'Debes esperar al menos un día sin movimiento'")
                result['status'] = 'cannot_generate_yet'
                result['report_generated'] = False
                next_attempt = self.result_manager.calculate_next_attempt_time(
                    'cannot_generate_yet',
                    retry_count,
                    last_movement_date=result.get('last_movement_date'),
                )
                result['next_attempt_time'] = next_attempt.strftime('%Y-%m-%d %H:%M:%S') if next_attempt else None
                
                self.stats['saltados_por_tiempo'] += 1
                
                # Cerrar modal
                self.form_handler._close_modal()
                self.form_handler.delete_temp_screenshot(result.get('status_history_screenshot_path'))
                return result
            
            # Click en Siguiente
            if not self.form_handler.click_next_button():
                self._handle_unexpected_error(phone, result, retry_count, "Botón Siguiente (bloqueado o no encontrado)")
                return result
            
            # Ingresar observación
            if not self.form_handler.enter_observation_text():
                self._handle_unexpected_error(phone, result, retry_count, "Campo observación")
                return result

            # Adjuntar imagen capturada previamente (Status History)
            if not self.form_handler.upload_status_history_image(result.get('status_history_screenshot_path')):
                self._handle_unexpected_error(phone, result, retry_count, "Adjuntar imagen de Status History")
                return result
            
            # Iniciar conversación
            if not self.form_handler.start_conversation():
                self._handle_unexpected_error(phone, result, retry_count, "Iniciar conversación (botón bloqueado o imprevisto)")
                return result

            # Comprobante obligatorio: validar redirección a chat CAS con cas_chat_id
            chat_check = self.form_handler.wait_for_chat_redirect(timeout_sec=25)
            result['cas_chat_url'] = chat_check.get('chat_url')
            result['cas_chat_id'] = chat_check.get('cas_chat_id')
            if not chat_check.get('success'):
                self._handle_unexpected_error(phone, result, retry_count, "No se validó chat CAS tras Start conversation")
                return result
            
            # Éxito
            result['status'] = 'reportado'
            result['report_generated'] = True
            result['next_attempt_time'] = None
            self.form_handler.delete_temp_screenshot(result.get('status_history_screenshot_path'))
            self.stats['procesados'] += 1
            
            # Tras reportar, Dropi puede redirigir a otra página; asegurar que estamos en Mis Pedidos para la siguiente orden
            time.sleep(3)
            if "/dashboard/orders" not in self.driver.current_url:
                self.logger.info("   Redirección detectada tras reportar; volviendo a Mis Pedidos...")
                if not self._navigate_to_orders():
                    self.logger.warning("   No se pudo volver a Mis Pedidos; la siguiente orden podría fallar.")
            
        except TimeoutException:
            self._handle_unexpected_error(phone, result, retry_count, "Timeout")
        except Exception as e:
            self._handle_unexpected_error(phone, result, retry_count, str(e))
        
        return result
    
    def _handle_unexpected_error(self, phone, result, retry_count, detail=""):
        """
        Manejo de error inesperado (popup nuevo, timeout, etc.):
        Refresca la página para cerrar modales/overlays y marca la orden como
        no reportada por tiempo (cannot_generate_yet) para continuar con la siguiente.
        """
        self.logger.warning(f"⚠️ Error inesperado en orden {phone}: {detail}")
        try:
            self.driver.refresh()
            time.sleep(2)
            self.logger.info("   Página refrescada; forzando retorno a Mis Pedidos.")
        except Exception as e:
            self.logger.debug("Refresh falló: %s", e)
        try:
            if "/dashboard/orders" not in self.driver.current_url:
                self._navigate_to_orders()
        except Exception as e:
            self.logger.debug("No fue posible forzar retorno a pedidos: %s", e)
        result['status'] = 'cannot_generate_yet'
        result['report_generated'] = False
        next_attempt = self.result_manager.calculate_next_attempt_time(
            'cannot_generate_yet',
            retry_count,
            last_movement_date=result.get('last_movement_date'),
        )
        result['next_attempt_time'] = next_attempt.strftime('%Y-%m-%d %H:%M:%S') if next_attempt else None
        self.stats['saltados_por_tiempo'] += 1
        self.form_handler.delete_temp_screenshot(result.get('status_history_screenshot_path'))
    
    def _print_final_stats(self):
        """Imprime las estadísticas finales"""
        self.logger.info("")
        self.logger.info("="*80)
        self.logger.info("ESTADÍSTICAS FINALES")
        self.logger.info("="*80)
        self.logger.info(f"Total de órdenes:           {self.stats['total']}")
        self.logger.info(f"Procesados exitosamente:    {self.stats['procesados']}")
        self.logger.info(f"Ya tenían caso abierto:     {self.stats['ya_tienen_caso']}")
        self.logger.info(f"No encontrados:             {self.stats['no_encontrados']}")
        self.logger.info(f"Saltados por tiempo:        {self.stats['saltados_por_tiempo']}")
        self.logger.info(f"Reintentos:                 {self.stats['reintentos']}")
        self.logger.info(f"Errores:                    {self.stats['errores']}")
        
        # Calcular suma de verificación
        verification_sum = (
            self.stats['procesados'] +
            self.stats['ya_tienen_caso'] +
            self.stats['no_encontrados'] +
            self.stats['saltados_por_tiempo'] +
            self.stats['errores']
        )
        self.logger.info(f"Suma Verificación:          {verification_sum}/{self.stats['total']}")
        self.logger.info("="*80)
        
        if self.stats['total'] > 0:
            success_rate = (self.stats['procesados'] / self.stats['total']) * 100
            self.logger.info(f"Tasa de éxito: {success_rate:.2f}%")
        
        self.logger.info("="*80)
