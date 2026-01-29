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
    
    def __init__(self, driver, user_id, logger):
        """
        Inicializa el reporter
        
        Args:
            driver: WebDriver compartido (ya logueado)
            user_id: ID del usuario Django
            logger: Logger configurado
        """
        self.driver = driver
        self.user_id = user_id
        self.logger = logger
        
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
    
    def run(self):
        """
        Ejecuta el proceso completo de reporte.
        
        Returns:
            dict: Estadísticas del proceso
        """
        self.logger.info("="*80)
        self.logger.info("🤖 INICIANDO BOT DE REPORTES DROPI (Unified Mode)")
        self.logger.info("="*80)
        
        try:
            # 1. Cargar datos desde BD
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
                    is_first_order=(idx == 0), retry_count=retry_count
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
    
    def _process_single_order(self, phone, expected_state, line_number, order_id=None, is_first_order=False, retry_count=0):
        """
        Procesa una sola orden con manejo completo del flujo.
        
        Args:
            phone: Número de teléfono de la orden
            expected_state: Estado esperado de la orden
            line_number: Número de línea
            order_id: ID de la orden (opcional, preferido para búsqueda)
            is_first_order: Si es la primera orden
            retry_count: Número de reintentos
            
        Returns:
            dict con el resultado del procesamiento
        """
        result = {
            'line_number': line_number,
            'phone': str(phone),
            'order_id': str(order_id) if order_id else '',
            'status': 'error',
            'report_generated': False,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'next_attempt_time': None,
            'retry_count': retry_count
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
            
            # Buscar orden (Prioridad: ID > Teléfono)
            search_term = order_id if (order_id and str(order_id).strip()) else phone
            
            if not self.searcher.search_order(search_term):
                result['status'] = 'not_found'
                self.stats['no_encontrados'] += 1
                return result
            
            # Validar estado
            if not self.searcher.validate_order_state(expected_state):
                result['status'] = 'error'
                self.stats['errores'] += 1
                return result
            
            # Obtener fila de la orden
            order_row = self.searcher.get_current_order_row()
            
            # Click en Nueva Consulta
            if not self.form_handler.click_new_consultation(order_row):
                result['status'] = 'error'
                self.stats['errores'] += 1
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
                    return result
                elif popup_result['type'] == 'estado_invalido':
                    result['status'] = 'error'
                    self.stats['errores'] += 1
                    return result
            
            # Seleccionar tipo de consulta
            if not self.form_handler.select_consultation_type():
                result['status'] = 'error'
                self.stats['errores'] += 1
                return result
            
            # Seleccionar motivo
            reason_result = self.form_handler.select_consultation_reason()
            
            # Verificar alert de espera
            if self.popup_handler.check_wait_time_alert():
                self.logger.warning("⚠️ Alert detectado: 'Debes esperar al menos un día sin movimiento'")
                result['status'] = 'cannot_generate_yet'
                result['report_generated'] = False
                next_attempt = self.result_manager.calculate_next_attempt_time('cannot_generate_yet', retry_count)
                result['next_attempt_time'] = next_attempt.strftime('%Y-%m-%d %H:%M:%S') if next_attempt else None
                
                self.stats['saltados_por_tiempo'] += 1
                
                # Cerrar modal
                self.form_handler._close_modal()
                return result
            
            if not reason_result:
                result['status'] = 'error'
                self.stats['errores'] += 1
                return result
            
            # Click en Siguiente
            if not self.form_handler.click_next_button():
                result['status'] = 'cannot_generate_yet'
                result['report_generated'] = False
                next_attempt = self.result_manager.calculate_next_attempt_time('cannot_generate_yet', retry_count)
                result['next_attempt_time'] = next_attempt.strftime('%Y-%m-%d %H:%M:%S') if next_attempt else None
                self.stats['errores'] += 1
                return result
            
            # Ingresar observación
            if not self.form_handler.enter_observation_text():
                result['status'] = 'error'
                self.stats['errores'] += 1
                return result
            
            # Iniciar conversación
            if not self.form_handler.start_conversation():
                result['status'] = 'error'
                self.stats['errores'] += 1
                return result
            
            # Éxito
            result['status'] = 'reportado'
            result['report_generated'] = True
            result['next_attempt_time'] = None
            self.stats['procesados'] += 1
            
        except TimeoutException:
            self.logger.error(f"❌ Timeout procesando orden {phone}")
            result['status'] = 'session_expired'
            self.session_expired = True
        except Exception as e:
            result['status'] = 'error'
            self.stats['errores'] += 1
            self.logger.error(f"❌ Error procesando orden {phone}: {str(e)}")
        
        return result
    
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
