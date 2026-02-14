"""
Report Result Manager - Gestión de resultados y guardado en BD

Este módulo se encarga de:
1. Guardar resultados en OrderReport (histórico)
2. Actualizar OrderMovementReport (marcar como resuelto)
3. Calcular tiempos de próximo intento
4. Gestionar estados y transiciones
"""

from datetime import date, datetime, time as dt_time, timedelta
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
    
    def calculate_next_attempt_time(self, status, retry_count=0, last_movement_date=None):
        """
        Calcula el tiempo del próximo intento según el estado.
        
        Args:
            status: Estado del reporte
            retry_count: Número de reintentos
            last_movement_date: date opcional capturada desde Dropi
            
        Returns:
            datetime o None si no se requiere reintento
        """
        now = timezone.now()
        
        if status == 'cannot_generate_yet':
            # Si Dropi muestra fecha de último movimiento, usar ese dato para
            # calcular un próximo intento más real (inicio del día siguiente).
            if isinstance(last_movement_date, date):
                next_date = last_movement_date + timedelta(days=1)
                next_attempt = timezone.make_aware(
                    datetime.combine(next_date, dt_time.min),
                    timezone.get_current_timezone()
                )
                if next_attempt > now:
                    return next_attempt
            # Fallback: 24 horas para órdenes que aún no cumplen el tiempo requerido
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
            last_movement_date = result.get('last_movement_date')
            if isinstance(last_movement_date, datetime):
                last_movement_date = last_movement_date.date()
            elif isinstance(last_movement_date, str):
                try:
                    last_movement_date = datetime.strptime(last_movement_date, '%Y-%m-%d').date()
                except ValueError:
                    last_movement_date = None
            last_movement_status = result.get('last_movement_status')
            inactivity_days_real = result.get('inactivity_days_real')
            if inactivity_days_real is not None:
                try:
                    inactivity_days_real = int(inactivity_days_real)
                except (TypeError, ValueError):
                    inactivity_days_real = None

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
            
            # DEBUG: Log antes de guardar para diagnosticar problemas de KPIs
            self.logger.info(f"[ReportResultManager] Guardando OrderReport: Phone={phone} | UserID={user.id} | Status={result.get('status')} | State={order_state}")

            # Obtener o crear el reporte (guarda datos de valor: estado, días, producto, cliente)
            status = result.get('status', 'error')
            obj, created = OrderReport.objects.update_or_create(
                user=user,
                order_phone=phone,
                defaults={
                    'order_id': order_id,
                    'status': status,
                    'report_generated': result.get('report_generated', False),
                    'customer_name': customer_name,
                    'product_name': product_name,
                    'order_state': order_state,
                    'days_since_order': days_since_order,
                    'last_movement_date': last_movement_date,
                    'last_movement_status': last_movement_status,
                    'inactivity_days_real': inactivity_days_real,
                    'next_attempt_time': next_attempt_time,
                }
            )
            # Registrar fecha/hora del reporte exitoso (solo la primera vez)
            reported_at_set = None
            if status == 'reportado' and (created or not obj.reported_at):
                reported_at_set = timezone.now()
                OrderReport.objects.filter(pk=obj.pk).update(reported_at=reported_at_set)
                obj.refresh_from_db()
                self.logger.info(
                    f"[ReportResultManager] ✅ Orden {phone} marcada como reportada: "
                    f"OrderReport.reported_at={obj.reported_at} | OrderReport.id={obj.id}"
                )
            self.logger.info(f"[ReportResultManager] Resultado BD: {'Creado' if created else 'Actualizado'} ID={obj.id} | Status={status} | Timestamp={obj.updated_at}")

            # Mantener sincronizado el registro de cola (OrderMovementReport) para análisis posterior
            db_report_id = result.get('db_report_id')
            if not db_report_id and row_data is not None:
                db_report_id = row_data.get('_db_report_id')
            if db_report_id:
                movement_updates = {}
                if last_movement_date is not None:
                    movement_updates['last_movement_date'] = last_movement_date
                if last_movement_status:
                    movement_updates['last_movement_status'] = last_movement_status
                if inactivity_days_real is not None:
                    movement_updates['inactivity_days_real'] = inactivity_days_real
                if movement_updates:
                    OrderMovementReport.objects.filter(id=db_report_id).update(**movement_updates)
            
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
            resolved_at_now = timezone.now()
            OrderMovementReport.objects.filter(id=db_report_id).update(
                is_resolved=True,
                resolved_at=resolved_at_now,
                resolution_note=resolution_note
            )
            # Obtener datos para log
            mov_report = OrderMovementReport.objects.filter(id=db_report_id).select_related('snapshot', 'batch').first()
            phone = mov_report.snapshot.customer_phone if mov_report and mov_report.snapshot_id else "N/A"
            self.logger.info(
                f"   💾 OrderMovementReport.id={db_report_id} marcado como RESUELTO: "
                f"resolved_at={resolved_at_now} | phone={phone} | user_id={mov_report.batch.user_id if mov_report else 'N/A'}"
            )
        except Exception as e:
            self.logger.error(f"   ❌ Error actualizando OrderMovementReport: {e}")
