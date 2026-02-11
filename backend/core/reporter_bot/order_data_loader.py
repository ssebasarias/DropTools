"""
Order Data Loader - Carga de órdenes desde OrderMovementReport

Este módulo se encarga de:
1. Consultar OrderMovementReport para obtener órdenes pendientes
2. Aplicar filtros inteligentes (excluir < 2 días, PENDIENTE CONFIRMACION)
3. Verificar si las órdenes pueden ser procesadas (tiempos, estado previo)
4. Retornar DataFrame listo para procesar
"""

import pandas as pd
from datetime import timedelta
from django.utils import timezone
from core.models import User, OrderReport, ReportBatch, OrderMovementReport


class OrderDataLoader:
    """
    Módulo encargado de cargar y filtrar órdenes pendientes desde BD.
    """
    
    def __init__(self, user_id, logger):
        """
        Inicializa el loader
        
        Args:
            user_id: ID del usuario Django
            logger: Logger configurado
        """
        self.user_id = user_id
        self.logger = logger
    
    def load_pending_orders(self):
        """
        Carga las órdenes pendientes desde OrderMovementReport.
        Aplica filtros inteligentes para evitar errores de "muy pronto".
        
        Returns:
            DataFrame con las columnas esperadas
        """
        self.logger.info("")
        self.logger.info("="*60)
        self.logger.info("📊 PASO 1: CARGANDO ÓRDENES DESDE BASE DE DATOS")
        self.logger.info("="*60)
        self.logger.info("🔍 Consultando OrderMovementReport...")
        
        try:
            # Validar usuario
            from core.models import User
            try:
                user = User.objects.get(id=self.user_id)
                self.logger.info(f"   👤 Usuario: {user.email} (ID: {user.id})")
            except User.DoesNotExist:
                self.logger.error(f"   ❌ ERROR: Usuario ID {self.user_id} no existe en la base de datos")
                return pd.DataFrame()
            
            # 1. Buscar último Batch exitoso del usuario
            self.logger.info("   🔎 Buscando último lote exitoso del usuario...")
            latest_batch = ReportBatch.objects.filter(
                user_id=self.user_id,
                status='SUCCESS'
            ).order_by('-created_at').first()
            
            if not latest_batch:
                self.logger.error("   ❌ No se encontraron lotes de reportes para este usuario.")
                self.logger.error("   💡 SOLUCIÓN: Ejecute primero el downloader para crear un lote.")
                return pd.DataFrame()
            
            self.logger.info(f"   ✅ Lote encontrado: ID {latest_batch.id}")
            self.logger.info(f"   📅 Fecha: {latest_batch.created_at}")
            
            # 2. Buscar órdenes pendientes con filtros inteligentes
            limit_date = timezone.now().date() - timedelta(days=2)
            
            # Buscar inhabilitados por tiempo (wait time alerts recientes)
            # Ordenes que tienen un reporte reciente diciendo 'cannot_generate_yet' y su tiempo no ha expirado
            excluded_phones = OrderReport.objects.filter(
                user_id=self.user_id,
                status='cannot_generate_yet',
                next_attempt_time__gt=timezone.now()
            ).values_list('order_phone', flat=True)

            pending_items = OrderMovementReport.objects.filter(
                batch=latest_batch,
                is_resolved=False
            ).exclude(
                snapshot__current_status='PENDIENTE CONFIRMACION'
            ).filter(
                snapshot__order_date__lte=limit_date  # Solo órdenes de hace 2+ días
            ).exclude(
                snapshot__customer_phone__in=excluded_phones # Excluir las que están en tiempo de espera
            ).select_related('snapshot')
            
            count = pending_items.count()
            self.logger.info(f"   📊 Órdenes pendientes por resolver: {count}")
            self.logger.info(f"   [DEBUG] Filtro Fecha: <= {limit_date} (Excluyendo ayer y hoy)")
            
            if count == 0:
                self.logger.info("   ✅ Nada pendiente (o solo quedan Pendientes de Confirmación / Muy recientes).")
                return pd.DataFrame()

            # 3. Construir lista de diccionarios
            data_list = []
            for item in pending_items:
                snap = item.snapshot
                data_list.append({
                    'Teléfono': snap.customer_phone,
                    'Estado Actual': snap.current_status,
                    'ID Orden': snap.dropi_order_id,
                    'Cliente': snap.customer_name,
                    'Producto': snap.product_name,
                    'Días desde Orden': item.days_since_order,
                    '_db_report_id': item.id,  # Para marcar resolved después
                })
            
            # 4. Crear DataFrame
            df = pd.DataFrame(data_list)
            df['Teléfono'] = df['Teléfono'].astype(str)
            
            self.logger.info(f"   ✅ DataFrame construido con {len(df)} registros.")
            return df
        except Exception as e:
            self.logger.error(f"   ❌ Error cargando órdenes: {e}")
            return pd.DataFrame()

    def load_pending_orders_slice(self, range_start, range_end):
        """
        Carga las órdenes pendientes y devuelve solo el slice [range_start, range_end] (1-based).
        Útil para report_range_task: cada worker procesa un rango de índices.
        Returns:
            DataFrame con las filas range_start-1 hasta range_end (inclusive), o vacío si no hay datos.
        """
        df = self.load_pending_orders()
        if df.empty:
            return df
        # 1-based to 0-based: range_start=1, range_end=100 -> iloc[0:100]
        start_idx = max(0, range_start - 1)
        end_idx = min(len(df), range_end)
        return df.iloc[start_idx:end_idx].copy()

    def check_order_can_be_processed(self, phone):
        """
        Verifica si una orden puede ser procesada según tiempos requeridos y estado previo.
        
        Args:
            phone: Número de teléfono de la orden
            
        Returns:
            tuple: (can_process: bool, time_info: dict o None)
        """
        # Primero verificar si ya fue reportada exitosamente
        if self._check_order_already_reported(phone):
            return False, {
                'status': 'reportado',
                'reason': 'already_reported',
                'message': 'Orden ya fue reportada exitosamente'
            }
        
        # Obtener el reporte más reciente
        report = self._get_order_report(phone)
        
        if not report:
            # No hay reporte previo, se puede procesar
            return True, None
        
        # Verificar si tiene next_attempt_time y aún no ha llegado
        if report.next_attempt_time:
            now = timezone.now()
            if now < report.next_attempt_time:
                hours_remaining = (report.next_attempt_time - now).total_seconds() / 3600
                return False, {
                    'status': report.status,
                    'hours_remaining': hours_remaining,
                    'next_attempt_time': report.next_attempt_time,
                    'reason': 'waiting_time'
                }
        
        # Si el estado es 'reportado', no se puede procesar
        if report.status == 'reportado':
            return False, {
                'status': 'reportado',
                'reason': 'already_reported',
                'message': 'Orden ya fue reportada exitosamente'
            }
        
        return True, None
    
    def _check_order_already_reported(self, phone):
        """Verifica si una orden ya fue reportada exitosamente"""
        try:
            user = User.objects.get(id=self.user_id)
            report = OrderReport.objects.filter(
                user=user,
                order_phone=str(phone),
                status='reportado'
            ).first()
            
            if report:
                self.logger.info(f"✅ Orden {phone} ya fue reportada exitosamente (ID: {report.id})")
                return report
            return None
        except Exception as e:
            self.logger.warning(f"⚠️ Error al verificar orden reportada: {str(e)}")
            return None
    
    def _get_order_report(self, phone):
        """Obtiene el reporte más reciente de una orden (si existe)"""
        try:
            user = User.objects.get(id=self.user_id)
            report = OrderReport.objects.filter(
                user=user,
                order_phone=str(phone)
            ).order_by('-created_at').first()
            
            return report
        except Exception as e:
            self.logger.warning(f"⚠️ Error al obtener reporte: {str(e)}")
            return None
