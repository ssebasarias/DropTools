"""
Comparer - Módulo de comparación de reportes (Lógica pura de BD)

Este módulo compara dos lotes (ReportBatch) almacenados en la base de datos
para encontrar órdenes sin movimiento, guarda los hallazgos en OrderMovementReport.

NO requiere navegador - es pura lógica de base de datos.
"""

import logging
from datetime import datetime
from django.db.models import F
from django.utils import timezone
from core.models import User, ReportBatch, RawOrderSnapshot, OrderMovementReport


class ReportComparer:
    """
    Comparador de Reportes (Database Version)
    
    Lógica:
    1. Identifica el último lote exitoso (Actual).
    2. Identifica un lote anterior (Base) con una diferencia de ~2 días.
    3. Compara via SQL snapshots de ambos lotes.
    4. Detecta órdenes con el MISMO estado en ambos lotes (sin movimiento).
    5. Guarda resultados en OrderMovementReport.
    """
    
    # Estados de interés para el filtrado
    ESTADOS_INTERES = [
        'BODEGA DESTINO', 'DESPACHADA', 'EN BODEGA ORIGEN', 'EN BODEGA TRANSPORTADORA',
        'EN CAMINO', 'EN DESPACHO', 'EN PROCESAMIENTO', 'EN PROCESO DE DEVOLUCION',
        'EN REPARTO', 'EN RUTA', 'EN TRANSITO', 'ENTREGADA A CONEXIONES',
        'ENTREGADO A TRANSPORTADORA', 'NOVEDAD SOLUCIONADA', 'RECOGIDO POR DROPI',
        'TELEMERCADEO', 'PENDIENTE', 'PENDIENTE CONFIRMACION'
    ]

    def __init__(self, user_id, logger):
        """
        Inicializa el comparador
        
        Args:
            user_id: ID del usuario Django
            logger: Logger configurado
        """
        self.user_id = user_id
        self.logger = logger
        self.user = self._get_user()
        
        # Stats
        self.stats = {
            'actual_batch_id': None,
            'base_batch_id': None,
            'total_orders_compared': 0,
            'total_detected': 0
        }

    def _get_user(self):
        """Obtiene el usuario"""
        if self.user_id:
            return User.objects.filter(id=self.user_id).first()
        return User.objects.filter(role='ADMIN').first() or User.objects.first()

    def find_batches(self):
        """
        Encuentra el lote Actual (más reciente) y Base (anterior)
        
        Returns:
            tuple: (actual_batch, base_batch) o (None, None) si no se encuentran
        """
        if not self.user:
            self.logger.error("No user found.")
            return None, None

        # 1. Actual = batch más reciente SUCCESS; Base = el anterior (segundo más reciente).
        # Así no dependemos de fecha calendario/timezone: cuando descargas Ayer y Hoy en la misma
        # ejecución, comparamos Hoy (actual) vs Ayer (base) sin buscar "día anterior".
        batches = list(
            ReportBatch.objects.filter(user=self.user, status='SUCCESS')
            .order_by('-created_at')[:2]
        )
        if len(batches) < 2:
            if not batches:
                self.logger.error("No SUCCESS batches found for this user.")
                return None, None
            self.logger.error("   ❌ No hay al menos 2 batches SUCCESS para comparar (necesitas Ayer + Hoy).")
            return None, None

        actual_batch = batches[0]
        base_batch = batches[1]
        self.logger.info(
            f"   📅 Batch ACTUAL: ID {actual_batch.id} (creado {actual_batch.created_at.strftime('%Y-%m-%d %H:%M')})"
        )
        self.logger.info(
            f"   📅 Batch BASE (anterior): ID {base_batch.id} (creado {base_batch.created_at.strftime('%Y-%m-%d %H:%M')})"
        )
        days_diff = (actual_batch.created_at - base_batch.created_at).days
        self.logger.info(f"      Diferencia temporal: {days_diff} días")

        return actual_batch, base_batch

    def run(self):
        """
        Ejecuta la comparación completa
        
        Returns:
            bool: True si la comparación fue exitosa
        """
        self.logger.info("="*60)
        self.logger.info("🔄 INICIANDO COMPARACIÓN DB")
        self.logger.info("="*60)

        actual, base = self.find_batches()
        if not actual or not base:
            return False

        self.stats['actual_batch_id'] = actual.id
        self.stats['base_batch_id'] = base.id

        self.logger.info("   📥 Cargando snapshots en memoria para comparación rápida...")
        
        # Load Base: {dropi_order_id: status} — solo IDs reales (no NO-ID-*)
        base_map = {}
        base_qs = RawOrderSnapshot.objects.filter(
            batch=base,
            current_status__in=self.ESTADOS_INTERES
        ).exclude(
            dropi_order_id__startswith='NO-ID-'
        ).values('dropi_order_id', 'current_status')

        for item in base_qs:
            base_map[item['dropi_order_id']] = item['current_status']

        self.logger.info(f"      Snapshots Base relevantes: {len(base_map)}")
        if len(base_map) == 0:
            self.logger.warning("      ⚠️ No hay snapshots relevantes en el batch base!")

        # Load Actual and Compare — solo IDs reales; mismo ID + mismo estado = sin movimiento
        actual_qs = RawOrderSnapshot.objects.filter(
            batch=actual,
            current_status__in=self.ESTADOS_INTERES
        ).exclude(
            dropi_order_id__startswith='NO-ID-'
        )

        total_actual = actual_qs.count()
        self.stats['total_orders_compared'] = total_actual
        self.logger.info(f"      Snapshots Actual relevantes: {total_actual}")
        if actual_qs.count() == 0:
            self.logger.warning("      ⚠️ No hay snapshots relevantes en el batch actual!")

        stagnant_snapshots = []
        no_match_count = 0
        status_changed_count = 0

        for snapshot in actual_qs:
            prev_status = base_map.get(snapshot.dropi_order_id)
            if prev_status:
                if prev_status == snapshot.current_status:
                    # MATCH FOUND: Same ID, Same Status
                    stagnant_snapshots.append(snapshot)
                else:
                    status_changed_count += 1
            else:
                no_match_count += 1

        self.logger.info(f"   ✅ Órdenes Sin Movimiento detectadas: {len(stagnant_snapshots)}")
        self.logger.info(f"      - Órdenes con estado cambiado: {status_changed_count}")
        self.logger.info(f"      - Órdenes nuevas/no encontradas: {no_match_count}")

        if len(stagnant_snapshots) == 0:
            self.logger.warning("   ⚠️ No se detectaron órdenes sin movimiento.")
        
        # Save findings
        return self._save_findings(actual, stagnant_snapshots)

    def _save_findings(self, batch, snapshots):
        """
        Guarda los hallazgos en OrderMovementReport
        
        Args:
            batch: Batch actual
            snapshots: Lista de snapshots sin movimiento
            
        Returns:
            bool: True si se guardaron exitosamente
        """
        # 1. Clear previous findings for this batch
        deleted_count, _ = OrderMovementReport.objects.filter(batch=batch).delete()
        if deleted_count:
            self.logger.info(f"      Limpiados {deleted_count} reportes previos de este batch.")

        # 2. Bulk Create Findings
        reports_to_create = []
        now_date = timezone.now().date()

        for snap in snapshots:
            # Calculate days since order
            days_since = 0
            if snap.order_date:
                days_since = (now_date - snap.order_date).days
            
            reports_to_create.append(OrderMovementReport(
                batch=batch,
                snapshot=snap,
                days_since_order=days_since,
                is_resolved=False
            ))

        if reports_to_create:
            OrderMovementReport.objects.bulk_create(reports_to_create)
            self.logger.info("      💾 Guardados resultados en Base de Datos.")
            self.stats['total_detected'] = len(reports_to_create)

        self.logger.info("   ✅ Comparación finalizada y guardada en BD.")
        return True
