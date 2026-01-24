
"""
Comparador de Reportes (Database Version)
Este comando compara dos lotes (ReportBatch) almacenados en la base de datos para encontrar
órdenes sin movimiento, guarda los hallazgos en la tabla OrderMovementReport y genera un CSV.

Lógica:
1. Identifica el último lote exitoso (Actual).
2. Identifica un lote anterior (Base) con una diferencia de ~2 días.
3. Compara via SQL snapshots de ambos lotes.
4. Detecta órdenes con el MISMO estado en ambos lotes (sin movimiento).
5. Guarda resultados en DB y CSV.
"""

import os
import sys
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db.models import F
from django.utils import timezone
from core.models import User, ReportBatch, RawOrderSnapshot, OrderMovementReport
from core.utils.stdio import configure_utf8_stdio

class ReportComparatorDB:
    
    # Estados de interés para el filtrado
    ESTADOS_INTERES = [
        'BODEGA DESTINO', 'DESPACHADA', 'EN BODEGA ORIGEN', 'EN BODEGA TRANSPORTADORA',
        'EN CAMINO', 'EN DESPACHO', 'EN PROCESAMIENTO', 'EN PROCESO DE DEVOLUCION',
        'EN REPARTO', 'EN RUTA', 'EN TRANSITO', 'ENTREGADA A CONEXIONES',
        'ENTREGADO A TRANSPORTADORA', 'NOVEDAD SOLUCIONADA', 'RECOGIDO POR DROPI',
        'TELEMERCADEO'
    ]

    def __init__(self, user_id=None, gap_days=2):
        self.logger = self._setup_logger()
        self.user = self._get_user(user_id)
        self.gap_days = gap_days
        
        # Stats
        self.stats = {
            'actual_batch_id': None,
            'base_batch_id': None,
            'total_detected': 0
        }

    def _setup_logger(self):
        logger = logging.getLogger('ReportComparatorDB')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
        
        # File handler
        log_dir = Path(__file__).parent.parent.parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_dir / f'comparer_db_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        
        return logger

    def _get_user(self, user_id):
        if user_id:
            return User.objects.filter(id=user_id).first()
        # Default strategy: "reporter" user or first admin
        return User.objects.filter(role='ADMIN').first() or User.objects.first()

    def find_batches(self):
        """Find the Actual (latest) and Base (latency gap) batches."""
        if not self.user:
            self.logger.error("No user found.")
            return None, None

        # 1. Get Actual (Latest SUCCESS batch)
        # Assuming we want the VERY latest available, typically created today by the downloader
        actual_batch = ReportBatch.objects.filter(
            user=self.user, 
            status='SUCCESS'
        ).order_by('-created_at').first()

        if not actual_batch:
            self.logger.error("No SUCCESS batches found for this user.")
            return None, None
        
        self.logger.info(f"   📅 Batch ACTUAL encontrado: ID {actual_batch.id} ({actual_batch.created_at.date()})")

        # 2. Get Base (Approx X days ago)
        # Look for batches older than (Actual - Gap)
        # We start looking from (ActualDate - GapDays) backwards.
        
        target_max_date = actual_batch.created_at - timezone.timedelta(days=self.gap_days)
        # Window of tolerance: Look for batches created between (Target - 5 days) and (Target)
        # We want the CLOSEST one to the target gap date.
        
        base_batch = ReportBatch.objects.filter(
            user=self.user,
            status='SUCCESS',
            created_at__lte=target_max_date
        ).order_by('-created_at').first()

        if not base_batch:
            self.logger.warning(f"   ⚠️ No se encontró un Batch BASE con {self.gap_days} días de antigüedad.")
            self.logger.warning(f"      Buscando el inmediatamente anterior...")
            base_batch = ReportBatch.objects.filter(
                user=self.user,
                status='SUCCESS',
                created_at__lt=actual_batch.created_at
            ).order_by('-created_at').first()
            
            if not base_batch:
                self.logger.error("   ❌ No hay historial suficiente para comparar (solo existe 1 batch).")
                return None, None
        
        days_diff = (actual_batch.created_at - base_batch.created_at).days
        self.logger.info(f"   📅 Batch BASE encontrado: ID {base_batch.id} ({base_batch.created_at.date()})")
        self.logger.info(f"      Diferencia temporal: {days_diff} días")

        return actual_batch, base_batch

    def run_comparison(self):
        self.logger.info("="*60)
        self.logger.info("🔄 INICIANDO COMPARACIÓN DB")
        self.logger.info("="*60)

        actual, base = self.find_batches()
        if not actual or not base:
            return None

        self.stats['actual_batch_id'] = actual.id
        self.stats['base_batch_id'] = base.id

        # --- SQL LOGIC ---
        # Find orders present in BOTH batches where status is SAME and INTERESTING
        
        # Subquery or Join via Django ORM
        # Strategy: Get Actual orders, filter by status, annotate with Base status
        
        # Fetch snapshots efficiently
        # We use a dictionary approach for memory efficiency if datasets are <100k
        # Or distinct queryset if very large. Assuming <50k daily rows, dicts are fast.
        
        self.logger.info("   📥 Cargando snapshots en memoria para comparación rápida...")
        
        # Load Base: {dropi_id: status}
        base_map = {}
        base_qs = RawOrderSnapshot.objects.filter(
            batch=base, 
            current_status__in=self.ESTADOS_INTERES
        ).values('dropi_order_id', 'current_status')
        
        for item in base_qs:
            base_map[item['dropi_order_id']] = item['current_status']
            
        self.logger.info(f"      Snapshots Base relevantes: {len(base_map)}")

        # Load Actual and Compare
        actual_qs = RawOrderSnapshot.objects.filter(
            batch=actual,
            current_status__in=self.ESTADOS_INTERES
        )
        
        stagnant_snapshots = []
        
        for snapshot in actual_qs:
            prev_status = base_map.get(snapshot.dropi_order_id)
            if prev_status and prev_status == snapshot.current_status:
                # MATCH FOUND: Same ID, Same Status (and status is "Interesting")
                stagnant_snapshots.append(snapshot)

        self.logger.info(f"   ✅ Órdenes Sin Movimiento detectadas: {len(stagnant_snapshots)}")
        
        # --- SAVE RESULTS ---
        return self._save_findings(actual, stagnant_snapshots)

    def _save_findings(self, batch, snapshots):
        """Save findings to OrderMovementReport and CSV."""
        
        # 1. Clear previous findings for this batch to avoid duplicates if re-run
        deleted_count, _ = OrderMovementReport.objects.filter(batch=batch).delete()
        if deleted_count:
            self.logger.info(f"      Limpiados {deleted_count} reportes previos de este batch.")

        # 2. Bulk Create Findings
        reports_to_create = []
        now_date = timezone.now().date()
        
        csv_rows = []

        for snap in snapshots:
            # Calculate days since order
            days_since = 0
            if snap.order_date:
                days_since = (now_date - snap.order_date).days
            
            # DB Object
            reports_to_create.append(OrderMovementReport(
                batch=batch,
                snapshot=snap,
                days_since_order=days_since,
                is_resolved=False
            ))
            
            # CSV Data (Legacy Format Compatibility)
            csv_rows.append({
                'ID Orden': snap.dropi_order_id,
                'Guía': snap.guide_number or '',
                # 'Tipo Envío': '', # Not in DB yet
                'Estado Actual': snap.current_status,
                'Transportadora': snap.carrier or '',
                'Cliente': snap.customer_name or '',
                'Teléfono': snap.customer_phone or '',
                'Ciudad': snap.city or '',
                'Departamento': snap.department or '',
                'Producto': snap.product_name or '',
                'Cantidad': snap.quantity,
                'Total': snap.total_amount or 0,
                'Fecha': snap.order_date.strftime('%d/%m/%Y') if snap.order_date else '',
                'Días desde Orden': days_since
            })

        if reports_to_create:
            OrderMovementReport.objects.bulk_create(reports_to_create)
            self.logger.info("      💾 Guardados resultados en Base de Datos.")

        # 3. No CSV Generation
        self.logger.info("   ✅ Comparación finalizada y guardada en BD.")
        return True


class Command(BaseCommand):
    help = 'Compara reportes desde la base de datos para detectar órdenes sin movimiento'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, help='ID del usuario')
        
        # Arguments kept for compatibility but might be ignored by new logic
        parser.add_argument('--base', type=str, help='(Ignored) Path to base report')
        parser.add_argument('--actual', type=str, help='(Ignored) Path to actual report')

    def handle(self, *args, **options):
        configure_utf8_stdio()
        
        user_id = options.get('user_id')
        
        comparator = ReportComparatorDB(user_id=user_id)
        result_csv = comparator.run_comparison()
        
        if result_csv:
            self.stdout.write(self.style.SUCCESS(f'[OK] Comparación exitosa y guardada en BD.'))
        else:
            self.stdout.write(self.style.WARNING('[INFO] No se encontraron órdenes o hubo error.'))
