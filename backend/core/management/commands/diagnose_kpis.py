"""
Comando de diagnóstico para verificar el estado de los KPIs del reporter
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta, time as dt_time
from core.models import OrderReport, OrderMovementReport, ReportBatch, RawOrderSnapshot, WorkflowProgress


class Command(BaseCommand):
    help = 'Diagnostica el estado de los datos para los KPIs del reporter'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='ID del usuario a diagnosticar (opcional, si no se especifica usa el primer usuario con datos)'
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('DIAGNÓSTICO DE KPIs DEL REPORTER'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))

        # Obtener usuario
        from core.models import User
        if user_id:
            user = User.objects.filter(id=user_id).first()
            if not user:
                self.stdout.write(self.style.ERROR(f'❌ Usuario con ID {user_id} no encontrado'))
                return
        else:
            # Buscar primer usuario con datos
            user = User.objects.filter(order_reports__isnull=False).distinct().first()
            if not user:
                user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR('❌ No hay usuarios en el sistema'))
                return

        self.stdout.write(self.style.WARNING(f'👤 Usuario: {user.username} (ID: {user.id}, Email: {user.email})'))
        self.stdout.write(self.style.WARNING(f'   Dropi Email: {user.dropi_email or "No configurado"}\n'))

        # Configuración de timezone
        now = timezone.localtime(timezone.now())
        today = now.date()
        first_of_month = today.replace(day=1)
        
        tz = timezone.get_current_timezone()
        today_start = tz.localize(datetime.combine(today, dt_time.min))
        today_end = today_start + timedelta(days=1)
        month_start = tz.localize(datetime.combine(first_of_month, dt_time.min))

        self.stdout.write(self.style.WARNING(f'📅 Fecha actual: {now.strftime("%Y-%m-%d %H:%M:%S")}'))
        self.stdout.write(self.style.WARNING(f'   Timezone: {tz}'))
        self.stdout.write(self.style.WARNING(f'   Inicio del día: {today_start}'))
        self.stdout.write(self.style.WARNING(f'   Fin del día: {today_end}'))
        self.stdout.write(self.style.WARNING(f'   Inicio del mes: {month_start}\n'))

        # 1. REPORTADOS HOY
        self.stdout.write(self.style.HTTP_INFO('📊 KPI 1: REPORTADOS HOY'))
        self.stdout.write('-' * 80)
        
        total_reported_today = OrderReport.objects.filter(
            user=user,
            status='reportado',
            updated_at__gte=today_start,
            updated_at__lt=today_end
        ).count()
        
        self.stdout.write(f'   Total reportados hoy: {total_reported_today}')
        
        # Mostrar todos los OrderReport del usuario
        all_order_reports = OrderReport.objects.filter(user=user).order_by('-updated_at')
        self.stdout.write(f'   Total OrderReport del usuario: {all_order_reports.count()}')
        
        if all_order_reports.exists():
            self.stdout.write('\n   Últimos 5 OrderReport:')
            for report in all_order_reports[:5]:
                self.stdout.write(f'      - ID: {report.id}, Phone: {report.order_phone}, Status: {report.status}')
                self.stdout.write(f'        Created: {report.created_at}, Updated: {report.updated_at}')
        
        # Contar por status
        self.stdout.write('\n   Distribución por status:')
        from django.db.models import Count
        status_counts = OrderReport.objects.filter(user=user).values('status').annotate(count=Count('id')).order_by('-count')
        for item in status_counts:
            self.stdout.write(f'      - {item["status"]}: {item["count"]}')

        # 2. REPORTADOS MES
        self.stdout.write(self.style.HTTP_INFO('\n📊 KPI 2: REPORTADOS MES'))
        self.stdout.write('-' * 80)
        
        total_reported_month = OrderReport.objects.filter(
            user=user,
            status='reportado',
            updated_at__gte=month_start
        ).count()
        
        self.stdout.write(f'   Total reportados este mes: {total_reported_month}')

        # 3. ÓRDENES PENDIENTES
        self.stdout.write(self.style.HTTP_INFO('\n📊 KPI 3: ÓRDENES PENDIENTES'))
        self.stdout.write('-' * 80)
        
        # Pendientes según OrderReport (no reportados)
        total_pending_orderreport = OrderReport.objects.filter(
            user=user
        ).exclude(status='reportado').count()
        
        self.stdout.write(f'   Pendientes según OrderReport (status != reportado): {total_pending_orderreport}')
        
        # Pendientes según OrderMovementReport (sin movimiento no resueltos)
        # Primero verificar si hay batches
        batches = ReportBatch.objects.filter(user=user, status='SUCCESS').order_by('-created_at')
        self.stdout.write(f'\n   Total ReportBatch del usuario: {batches.count()}')
        
        if batches.exists():
            latest_batch = batches.first()
            self.stdout.write(f'   Último batch: ID {latest_batch.id}, creado {latest_batch.created_at}')
            
            # OrderMovementReport del último batch
            movement_reports = OrderMovementReport.objects.filter(
                batch=latest_batch,
                is_resolved=False
            )
            total_pending_movement = movement_reports.count()
            
            self.stdout.write(f'   Órdenes sin movimiento (OrderMovementReport, no resueltas): {total_pending_movement}')
            
            if movement_reports.exists():
                self.stdout.write('\n   Primeras 5 órdenes sin movimiento:')
                for mr in movement_reports[:5]:
                    snap = mr.snapshot
                    self.stdout.write(f'      - Order ID: {snap.dropi_order_id}, Status: {snap.current_status}')
                    self.stdout.write(f'        Cliente: {snap.customer_name}, Días: {mr.days_since_order}')
        else:
            self.stdout.write(self.style.WARNING('   ⚠️ No hay ReportBatch para este usuario'))
            self.stdout.write(self.style.WARNING('   Esto significa que el downloader no ha ejecutado o falló'))

        # 4. WORKFLOW PROGRESS
        self.stdout.write(self.style.HTTP_INFO('\n📊 WORKFLOW PROGRESS'))
        self.stdout.write('-' * 80)
        
        workflow = WorkflowProgress.objects.filter(user=user).order_by('-started_at').first()
        if workflow:
            self.stdout.write(f'   Último workflow: ID {workflow.id}')
            self.stdout.write(f'   Status: {workflow.status}')
            self.stdout.write(f'   Mensaje: {workflow.current_message}')
            self.stdout.write(f'   Iniciado: {workflow.started_at}')
            if workflow.completed_at:
                self.stdout.write(f'   Completado: {workflow.completed_at}')
        else:
            self.stdout.write(self.style.WARNING('   ⚠️ No hay WorkflowProgress para este usuario'))

        # 5. RAW ORDER SNAPSHOTS
        self.stdout.write(self.style.HTTP_INFO('\n📊 RAW ORDER SNAPSHOTS'))
        self.stdout.write('-' * 80)
        
        if batches.exists():
            latest_batch = batches.first()
            snapshots = RawOrderSnapshot.objects.filter(batch=latest_batch)
            self.stdout.write(f'   Total snapshots en último batch: {snapshots.count()}')
            
            if snapshots.exists():
                self.stdout.write('\n   Distribución por status:')
                status_counts = snapshots.values('current_status').annotate(count=Count('id')).order_by('-count')[:10]
                for item in status_counts:
                    self.stdout.write(f'      - {item["current_status"]}: {item["count"]}')

        # RESUMEN Y RECOMENDACIONES
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('RESUMEN Y DIAGNÓSTICO'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))

        issues = []
        
        if total_reported_today == 0 and total_reported_month == 0:
            issues.append('❌ No hay órdenes reportadas (ni hoy ni este mes)')
            issues.append('   Posibles causas:')
            issues.append('   - El bot no ha ejecutado exitosamente')
            issues.append('   - El reporter no está marcando órdenes como "reportado"')
            issues.append('   - Hay un problema con las fechas/timezone')
        
        if not batches.exists():
            issues.append('❌ No hay ReportBatch (el downloader no ha ejecutado)')
            issues.append('   Solución: Ejecutar el reporter manualmente o verificar el scheduler')
        
        if batches.exists() and batches.count() < 2:
            issues.append('⚠️ Solo hay 1 batch (se necesitan al menos 2 para comparar)')
            issues.append('   El comparer necesita 2 batches para detectar órdenes sin movimiento')
        
        if batches.exists() and batches.count() >= 2:
            latest_batch = batches.first()
            movement_reports = OrderMovementReport.objects.filter(batch=latest_batch, is_resolved=False)
            if movement_reports.count() == 0:
                issues.append('⚠️ No hay órdenes sin movimiento detectadas')
                issues.append('   Esto puede ser normal si todas las órdenes tienen movimiento')
                issues.append('   O puede indicar que el comparer no está funcionando correctamente')

        if issues:
            self.stdout.write(self.style.ERROR('PROBLEMAS DETECTADOS:\n'))
            for issue in issues:
                self.stdout.write(self.style.WARNING(issue))
        else:
            self.stdout.write(self.style.SUCCESS('✅ No se detectaron problemas obvios'))
            self.stdout.write(self.style.SUCCESS('   Los KPIs deberían estar mostrando datos correctamente'))

        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('FIN DEL DIAGNÓSTICO'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
