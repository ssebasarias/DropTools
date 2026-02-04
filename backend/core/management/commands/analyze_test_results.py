from django.core.management.base import BaseCommand
from core.models import ReporterRun, ReporterRunUser, ReporterReservation

class Command(BaseCommand):
    help = 'Analiza los resultados del test del reporter'

    def handle(self, *args, **options):
        self.stdout.write("="*70)
        self.stdout.write("📊 ANÁLISIS DE RESULTADOS DEL TEST")
        self.stdout.write("="*70)
        self.stdout.write("")

        # Buscar el run más reciente
        run = ReporterRun.objects.filter(slot__hour=17).order_by('-created_at').first()

        if not run:
            self.stdout.write(self.style.ERROR("❌ No se encontró ningún run para el slot de las 17:00"))
            return
        
        self.stdout.write(f"✅ Run ID: {run.id}")
        self.stdout.write(f"   Slot: {run.slot.hour}:00")
        self.stdout.write(f"   Status: {run.status}")
        self.stdout.write(f"   Scheduled: {run.scheduled_at}")
        self.stdout.write(f"   Started: {run.started_at}")
        self.stdout.write("")
        
        # Ver usuarios en el run
        run_users = ReporterRunUser.objects.filter(run=run).order_by('user_id')
        
        self.stdout.write("👥 USUARIOS EN EL RUN:")
        self.stdout.write("-"*70)
        
        for ru in run_users:
            reservation = ReporterReservation.objects.filter(user_id=ru.user_id).first()
            weight = reservation.calculated_weight if reservation else "?"
            
            self.stdout.write(f"   User {ru.user_id} ({ru.user.username}):")
            self.stdout.write(f"      Peso: {weight}")
            self.stdout.write(f"      DC Status: {ru.download_compare_status}")
            self.stdout.write(f"      Pending orders: {ru.total_pending_orders}")
            self.stdout.write(f"      Total ranges: {ru.total_ranges}")
            self.stdout.write(f"      Ranges completed: {ru.ranges_completed}")
            self.stdout.write("")
        
        # Validaciones
        self.stdout.write("="*70)
        self.stdout.write("✅ VALIDACIONES:")
        self.stdout.write("="*70)
        self.stdout.write("")
        
        # Validación 1: Solo 1 usuario ejecutó download_compare
        completed = run_users.filter(download_compare_status='completed').count()
        running = run_users.filter(download_compare_status='running').count()
        pending = run_users.filter(download_compare_status='pending').count()
        failed = run_users.filter(download_compare_status='failed').count()
        
        self.stdout.write(f"1. ¿Solo 1 usuario ejecutó DC? (Esperado: 1 completed/failed, 2 pending)")
        self.stdout.write(f"   ✓ Completed: {completed}")
        self.stdout.write(f"   ✓ Running: {running}")
        self.stdout.write(f"   ✓ Pending: {pending}")
        self.stdout.write(f"   ✓ Failed: {failed}")
        
        if (completed + running + failed) == 1 and pending == 2:
            self.stdout.write(self.style.SUCCESS("   ✅ CORRECTO: Solo 1 usuario ejecutó, 2 quedaron pendientes"))
        else:
            self.stdout.write(self.style.ERROR("   ❌ INCORRECTO: Distribución inesperada"))
        self.stdout.write("")
        
        # Validación 2: Los usuarios pendientes son los correctos
        pending_users = list(run_users.filter(download_compare_status='pending').values_list('user_id', flat=True))
        self.stdout.write(f"2. ¿Usuarios 3 y 4 quedaron pendientes?")
        self.stdout.write(f"   Usuarios pendientes: {pending_users}")
        
        if set(pending_users) == {3, 4}:
            self.stdout.write(self.style.SUCCESS("   ✅ CORRECTO: Usuarios 3 y 4 pendientes"))
        elif set(pending_users) == {2, 3} or set(pending_users) == {2, 4}:
            self.stdout.write(self.style.SUCCESS("   ✅ ACEPTABLE: 2 usuarios pendientes (orden diferente)"))
        else:
            self.stdout.write(self.style.WARNING("   ⚠️ INESPERADO"))
        self.stdout.write("")
        
        self.stdout.write("="*70)
        self.stdout.write("🔍 PROBLEMAS DETECTADOS:")
        self.stdout.write("="*70)
        
        # Verificar si hay login failures
        user_executed = run_users.exclude(download_compare_status='pending').first()
        if user_executed:
            if user_executed.total_pending_orders == 0:
                self.stdout.write(self.style.WARNING("⚠️ Usuario ejecutado no detectó órdenes pendientes"))
                self.stdout.write("   Posible causa: Login falló (página en blanco)")
                self.stdout.write("   Screenshot: /app/backend/results/screenshots/login_fail_*.png")
            else:
                self.stdout.write(self.style.SUCCESS("✅ Usuario detectó órdenes pendientes correctamente"))
