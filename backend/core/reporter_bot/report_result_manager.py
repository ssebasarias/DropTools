"""
Report Result Manager - Gestión de resultados y guardado en BD

Este módulo se encarga de:
1. Guardar resultados en OrderReport (histórico)
2. Actualizar OrderMovementReport (marcar como resuelto)
3. Calcular tiempos de próximo intento
4. Gestionar estados y transiciones
"""

from datetime import datetime, timedelta
from django.utils import timezone
from core.models import User, OrderReport, OrderMovementReport


class ReportResultManager:
    """
    Módulo encargado de gestionar y guardar los resultados de los reportes.
    """
    
    def __init__(self, user_id, logger):
        """
        Inicializa el result manager
        
        Args:
            user_id: ID del usuario Django
            logger: Logger configurado
        """
        self.user_id = user_id
        self.logger = logger
    
    def calculate_next_attempt_time(self, status, retry_count=0):
        """
        Calcula el tiempo del próximo intento según el estado.
        
        Args:
            status: Estado del reporte
            retry_count: Número de reintentos
            
        Returns:
            datetime o None si no se requiere reintento
        """
        now = timezone.now()
        
        if status == 'cannot_generate_yet':
            # 24 horas para órdenes que aún no cumplen el tiempo requerido
            return now + timedelta(hours=24)
        else:
            # Para otros estados, no se calcula (None = puede reintentar inmediatamente)
            return None
    
    def save_result(self, result, row_data=None):
        """
        Guarda un resultado en la base de datos (OrderReport).
        
        Args:
            result: Dict con el resultado del procesamiento
            row_data: Dict con datos adicionales de la orden (opcional)
        """
        try:
            user = User.objects.get(id=self.user_id)
            phone = str(result.get('phone', ''))
            
            if not phone:
                return
            
            # Extraer información adicional (datos de valor para análisis e historial)
            order_info = result.get('order_info', {}) or {}
            customer_name = order_info.get('customer_name') or result.get('customer_name')
            product_name = order_info.get('product_name') or result.get('product_name')
            order_id = order_info.get('order_id') or result.get('order_id', '')
            order_state = result.get('order_state')
            days_since_order = result.get('days_since_order')

            if row_data is not None:
                customer_name = customer_name or row_data.get('Cliente')
                product_name = product_name or row_data.get('Producto')
                order_id = order_id or row_data.get('ID Orden', '')
                order_state = order_state if order_state is not None else row_data.get('Estado Actual')
                if days_since_order is None and row_data.get('Días desde Orden') is not None:
                    try:
                        days_since_order = int(row_data.get('Días desde Orden'))
                    except (TypeError, ValueError):
                        pass
            
            # Convertir next_attempt_time si existe
            next_attempt_time = None
            if result.get('next_attempt_time'):
                try:
                    if isinstance(result['next_attempt_time'], str):
                        next_attempt_time = datetime.strptime(result['next_attempt_time'], '%Y-%m-%d %H:%M:%S')
                        next_attempt_time = timezone.make_aware(next_attempt_time)
                    elif isinstance(result['next_attempt_time'], datetime):
                        next_attempt_time = timezone.make_aware(result['next_attempt_time']) if timezone.is_naive(result['next_attempt_time']) else result['next_attempt_time']
                except Exception:
                    pass
            
            # Obtener o crear el reporte (guarda datos de valor: estado, días, producto, cliente)
            OrderReport.objects.update_or_create(
                user=user,
                order_phone=phone,
                defaults={
                    'order_id': order_id,
                    'status': result.get('status', 'error'),
                    'report_generated': result.get('report_generated', False),
                    'customer_name': customer_name,
                    'product_name': product_name,
                    'order_state': order_state,
                    'days_since_order': days_since_order,
                    'next_attempt_time': next_attempt_time,
                }
            )
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error al guardar resultado en BD: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def mark_order_resolved(self, db_report_id, resolution_note="Reportado exitosamente por Bot"):
        """
        Marca una orden como resuelta en OrderMovementReport.
        
        Args:
            db_report_id: ID del OrderMovementReport
            resolution_note: Nota de resolución (opcional)
        """
        try:
            OrderMovementReport.objects.filter(id=db_report_id).update(
                is_resolved=True,
                resolved_at=timezone.now(),
                resolution_note=resolution_note
            )
            self.logger.info(f"   💾 Registro DB {db_report_id} marcado como RESUELTO.")
        except Exception as e:
            self.logger.error(f"   ❌ Error actualizando OrderMovementReport: {e}")
