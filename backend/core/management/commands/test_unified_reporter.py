
import time
import os
import threading
import logging
import sys
from django.core.management.base import BaseCommand
from core.reporter_bot.unified_reporter import UnifiedReporter
from core.utils.stdio import configure_utf8_stdio

# Try importing psutil
PSUTIL_AVAILABLE = False
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    pass

class Command(BaseCommand):
    help = 'Executes the Unified Reporter in local visible mode with Matrix-style resource monitoring'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, required=True, help='User ID')

    def monitor_resources(self, stop_event):
        """Background resource monitor"""
        if not PSUTIL_AVAILABLE:
            return
            
        process = psutil.Process(os.getpid())
        logger = logging.getLogger('Recursos')
        
        while not stop_event.is_set():
            try:
                # Get stats including children (e.g. browser processes)
                total_rss = process.memory_info().rss
                cpu_percent = process.cpu_percent(interval=None)
                
                # Try to sum up children (browser)
                children = process.children(recursive=True)
                for child in children:
                    try:
                        total_rss += child.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                ram_mb = total_rss / 1024 / 1024
                # Imprimir directo a stdout para visibilidad inmediata
                sys.stdout.write(f"\r[MONITOR] CPU: {cpu_percent:.1f}% | RAM Total: {ram_mb:.1f} MB | Hilos/Procesos: {1+len(children)}   ")
                sys.stdout.flush()
                
            except Exception:
                pass
                
            time.sleep(2)

    def handle(self, *args, **options):
        configure_utf8_stdio()
        user_id = options['user_id']
        
        print("\n" + "="*80)
        print(f"🚀 INICIANDO PRUEBA DE REPORTER UNIFICADO - USUARIO {user_id}")
        print(f"👀 MODO: HEADLESS=FALSE (Navegador Visible)")
        print("="*80)

        if not PSUTIL_AVAILABLE:
            print("⚠️ ADVERTENCIA: 'psutil' no instalado. Monitoreo de RAM/CPU detallado no disponible.")
            print("   Instalar con: pip install psutil")

        # Start Monitor
        stop_monitor = threading.Event()
        monitor_thread = None
        if PSUTIL_AVAILABLE:
            print("📊 Monitoreo de recursos activado (Second plane)")
            monitor_thread = threading.Thread(target=self.monitor_resources, args=(stop_monitor,))
            monitor_thread.daemon = True
            monitor_thread.start()

        try:
            print("🤖 Instanciando UnifiedReporter...")
            # Explicitly visible and edge
            reporter = UnifiedReporter(
                user_id=user_id,
                headless=False,
                browser='edge'
            )
            
            print("🎬 Ejecutando flujo unificado...")
            start_time = time.time()
            stats = reporter.run()
            duration = time.time() - start_time
            
            # Stop monitor to clear line
            if monitor_thread:
                stop_monitor.set()
                monitor_thread.join(timeout=2)
                sys.stdout.write("\n")

            print("\n" + "="*80)
            print(f"✅ PRUEBA FINALIZADA en {duration:.1f} segundos")
            print("="*80)
            print("📈 ESTADÍSTICAS FINALES:")
            for k, v in stats.items():
                print(f" - {k}: {v}")
                
        except KeyboardInterrupt:
            if monitor_thread: stop_monitor.set()
            print("\n🛑 DETENIDO POR USUARIO")
        except Exception as e:
            if monitor_thread: stop_monitor.set()
            print(f"\n❌ ERROR CRÍTICO: {e}")
            # Solo traceback si es error inesperado
            # import traceback
            # traceback.print_exc()
        finally:
            if monitor_thread and monitor_thread.is_alive():
                stop_monitor.set()
                monitor_thread.join()
