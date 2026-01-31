"""
Unified Reporter - Orquestador del flujo unificado

Este módulo orquesta el flujo de trabajo unificado:
1. Inicia el driver una vez (Singleton)
2. Hace login una vez
3. Pasa el driver "en caliente" al Downloader
4. Ejecuta el Comparer (lógica BD pura - no requiere navegador)
5. Cierra el driver al finalizar

Todo en una única sesión de navegador persistente.
Flujo completo: Descarga -> Comparación -> Reporte
"""

import logging
from django.core.management.base import BaseCommand
from core.reporter_bot.utils import setup_logger
from core.reporter_bot.driver_manager import DriverManager
from core.reporter_bot.auth_manager import AuthManager
from core.reporter_bot.downloader import DropiDownloader
from core.reporter_bot.comparer import ReportComparer
from core.reporter_bot.reporter import DropiReporter
from core.models import User, WorkflowProgress
from django.utils import timezone


class UnifiedReporter:
    """
    Orquestador del flujo unificado de trabajo.
    
    Ejecuta en una única sesión de navegador:
    1. Downloader: Descarga reportes Excel desde Dropi
    2. Comparer: Compara reportes y detecta órdenes sin movimiento (BD pura)
    3. Reporter: Genera reportes en la página web para órdenes sin movimiento
    
    Características:
    - Una sola sesión de navegador (Singleton)
    - Un solo login
    - Driver compartido entre módulos
    - Gestión centralizada de errores
    """
    
    def __init__(self, user_id, headless=False, logger=None, download_dir=None, browser='edge', browser_priority=None):
        """
        Inicializa el orquestador
        
        Args:
            user_id: ID del usuario Django
            headless: Si True, ejecuta en modo headless
            logger: Logger configurado (opcional)
            download_dir: Directorio para descargas (opcional)
            browser: Navegador por defecto si no se usa fallback
            browser_priority: Lista de navegadores a intentar en orden, ej. ['chrome','firefox','edge'].
                              Si es None, se usa env BROWSER_ORDER o valor por defecto según entorno.
        """
        import os
        self.user_id = user_id
        self.headless = headless
        self.logger = logger or setup_logger('UnifiedReporter')
        self.download_dir = download_dir
        self.browser = browser
        # Fallback: orden de navegadores según entorno (una sola fuente: docker_config)
        from core.reporter_bot.docker_config import get_reporter_browser_order
        if browser_priority is not None:
            self.browser_priority = browser_priority if isinstance(browser_priority, list) else [
                b.strip() for b in str(browser_priority).split(',') if b.strip()
            ]
        else:
            self.browser_priority = get_reporter_browser_order()
        
        # Validar usuario
        try:
            from core.models import User
            user = User.objects.get(id=user_id)
            self.logger.info(f"👤 Usuario validado: {user.email} (ID: {user.id})")
            
            # Verificar credenciales
            if not user.dropi_email or not user.dropi_password:
                raise ValueError(
                    f"Usuario {user.email} no tiene credenciales Dropi configuradas. "
                    "Configure dropi_email y dropi_password en el perfil del usuario."
                )
            self.logger.info("✅ Credenciales Dropi encontradas")
        except User.DoesNotExist:
            raise ValueError(f"Usuario ID {user_id} no existe en la base de datos")
        except Exception as e:
            self.logger.error(f"❌ Error validando usuario: {e}")
            raise
        
        # Managers
        self.driver_manager = None
        self.auth_manager = None
        self.driver = None
        
        # Stats
        self.stats = {
            'downloader': None,
            'comparer': None,
            'reporter': None
        }
        
        # Progress Tracking
        self.workflow_progress = None
        
    def _init_progress(self):
        """Initialize or retrieve WorkflowProgress for user."""
        from django.utils import timezone
        try:
            user = User.objects.get(id=self.user_id)
            # Find running or recent pending progress
            wp = WorkflowProgress.objects.filter(
                user=user,
                status__in=['pending', 'step1_running', 'step2_running', 'step3_running']
            ).order_by('-started_at').first()

            if not wp:
                wp = WorkflowProgress.objects.create(
                    user=user,
                    status='step1_running',
                    current_message='Iniciando flujo de trabajo unificado...',
                    messages=['Iniciando orquestador...'],
                    started_at=timezone.now(),
                )
            else:
                # Si la BD devuelve started_at naive (p. ej. columna sin time zone), convertir a aware para evitar RuntimeWarning al guardar
                if wp.started_at and timezone.is_naive(wp.started_at):
                    wp.started_at = timezone.make_aware(wp.started_at, timezone.get_current_timezone())
                    wp.save(update_fields=['started_at'])
            self.workflow_progress = wp
        except Exception as e:
            self.logger.error(f"Error initializing workflow progress: {e}")

    def _update_progress(self, status, message):
        """Update DB progress."""
        if not self.workflow_progress:
            return
        try:
            self.workflow_progress.status = status
            self.workflow_progress.current_message = message
            if not self.workflow_progress.messages:
                self.workflow_progress.messages = []
            self.workflow_progress.messages.append(message)
            
            now = timezone.now()
            if status == 'step1_completed': self.workflow_progress.step1_completed_at = now
            elif status == 'step2_completed': self.workflow_progress.step2_completed_at = now
            elif status == 'step3_completed': self.workflow_progress.step3_completed_at = now
            elif status == 'completed': self.workflow_progress.completed_at = now
            
            self.workflow_progress.save()
        except Exception as e:
            self.logger.warning(f"Failed to update progress: {e}")
    
    def run(self):
        """
        Ejecuta el flujo completo unificado
        
        Returns:
            dict: Estadísticas del proceso completo
        """
        self.logger.info("="*80)
        self.logger.info("🚀 INICIANDO FLUJO UNIFICADO DE REPORTES")
        self.logger.info("="*80)
        self.logger.info(f"   👤 Usuario ID: {self.user_id}")
        self.logger.info(f"   🌐 Navegador: {self.browser.upper()}")
        self.logger.info(f"   {'🔇 Headless' if self.headless else '👀 Modo Visible'}: {self.headless}")
        self.logger.info("="*80)
        
        self._init_progress()
        self._update_progress('step1_running', 'Iniciando flujo unificado (Descarga + Comparación + Reporte)...')
        
        try:
            # ========================================================================
            # PASO 1: INICIAR DRIVER (Una sola vez - Singleton)
            # ========================================================================
            self.logger.info("")
            self.logger.info("="*60)
            self.logger.info("📦 PASO 1: INICIALIZANDO DRIVER")
            self.logger.info("="*60)
            
            self.driver_manager = DriverManager(
                headless=self.headless,
                logger=self.logger,
                download_dir=self.download_dir,
                browser=self.browser_priority[0] if self.browser_priority else self.browser
            )
            self.driver = self.driver_manager.init_driver(browser_priority=self.browser_priority)
            
            if not self.driver:
                self.logger.error("❌ No se pudo inicializar el driver")
                return self.stats
            
            # ========================================================================
            # PASO 2: LOGIN (Una sola vez)
            # ========================================================================
            self.logger.info("")
            self.logger.info("="*60)
            self.logger.info("🔐 PASO 2: AUTENTICACIÓN")
            self.logger.info("="*60)
            
            self.auth_manager = AuthManager(
                driver=self.driver,
                user_id=self.user_id,
                logger=self.logger
            )
            
            self.auth_manager.load_credentials()
            
            if not self.auth_manager.login():
                self.logger.error("🛑 Login fallido. Terminando.")
                self._update_progress('failed', 'Error: Autenticación fallida.')
                return self.stats
            
            # ========================================================================
            # PASO 3: DOWNLOADER (Usa driver logueado)
            # ========================================================================
            self.logger.info("")
            self.logger.info("="*60)
            self.logger.info("📥 PASO 3: DESCARGA DE REPORTES")
            self.logger.info("="*60)
            # Siempre visible en docker compose logs (Celery suele mostrar WARNING)
            self.logger.warning("📥 PASO 3: DESCARGA - Iniciando (Mis Pedidos → Acciones → Orders with Products)...")
            
            downloader = DropiDownloader(
                driver=self.driver,
                user_id=self.user_id,
                logger=self.logger,
                download_dir=self.download_dir
            )
            
            downloaded_files = downloader.run()
            
            downloader_success = len(downloaded_files) > 0 if downloaded_files else False
            
            self.stats['downloader'] = {
                'files_downloaded': len(downloaded_files) if downloaded_files else 0,
                'success': downloader_success
            }
            
            # Si no hay descargas exitosas, no se puede ejecutar la comparación
            if not downloader_success:
                self.logger.error("❌ No se descargaron archivos. El proceso de comparación no puede ejecutarse.")
                self.logger.warning("🛑 PASO 3: DESCARGA FALLIDA - Abortando. No se ejecutan Comparer ni Reporter.")
                self.stats['comparer'] = {
                    'success': False,
                    'total_detected': 0
                }
                self.stats['reporter'] = {
                    'procesados': 0,
                    'total': 0
                }
                self._update_progress('failed', 'Error: No se pudieron descargar los reportes.')
                return self.stats
                
            self._update_progress('step1_completed', f'Descarga completada: {len(downloaded_files)} archivos.')
            self.logger.warning(f"✅ PASO 3: DESCARGA OK - {len(downloaded_files)} archivo(s). Iniciando comparación.")
            
            # ========================================================================
            # PASO 4: COMPARER (Lógica BD pura - No requiere browser)
            # Solo se ejecuta si hubo descargas exitosas
            # ========================================================================
            self.logger.info("")
            self.logger.info("="*60)
            self.logger.info("🕵️ PASO 4: COMPARACIÓN DE REPORTES (BD)")
            self.logger.info("="*60)
            self.logger.warning("🕵️ PASO 4: COMPARACIÓN - Iniciando (solo BD, sin navegador)...")
            
            comparer = ReportComparer(
                user_id=self.user_id,
                logger=self.logger
            )
            
            comparison_success = comparer.run()
            
            self.stats['comparer'] = {
                'success': comparison_success,
                'total_detected': comparer.stats.get('total_detected', 0)
            }
            
            if not comparison_success:
                self.logger.warning("⚠️ Comparación falló o no encontró órdenes sin movimiento. Continuando con reporter...")
            else:
                self._update_progress('step2_completed', f"Comparación completada: {comparer.stats.get('total_detected', 0)} órdenes detectadas.")
            
            # ========================================================================
            # PASO 5: REPORTER (Usa driver logueado - Sesión persistente)
            # ========================================================================
            self.logger.info("")
            self.logger.info("="*60)
            self.logger.info("🤖 PASO 5: REPORTE DE ÓRDENES (Sesión Persistente)")
            self.logger.info("="*60)
            self.logger.warning("🤖 PASO 5: REPORTER - Iniciando (formulario Siguiente + reportes en Dropi)...")
            
            self._update_progress('step3_running', 'Generando reportes en Dropi...')

            def on_order_processed(current, total, processed_count):
                self._update_progress('step3_running', f'Procesando orden {current}/{total} ({processed_count} reportadas)...')

            reporter = DropiReporter(
                driver=self.driver,
                user_id=self.user_id,
                logger=self.logger,
                on_order_processed=on_order_processed
            )

            reporter_stats = reporter.run()
            
            self.stats['reporter'] = reporter_stats
            
            self._update_progress('step3_completed', f"Reporte completado: {reporter_stats.get('procesados', 0)} órdenes reportadas.")
            self._update_progress('completed', 'Flujo unificado completado exitosamente.')
            
            # ========================================================================
            # RESUMEN FINAL
            # ========================================================================
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("✅ FLUJO UNIFICADO FINALIZADO")
            self.logger.info("="*80)
            self.logger.info("   📊 Resumen:")
            self.logger.info(f"      • Descargas: {self.stats['downloader']['files_downloaded']} archivo(s)")
            self.logger.info(f"      • Comparación: {self.stats['comparer']['total_detected']} orden(es) sin movimiento detectada(s)")
            self.logger.info(f"      • Reportes: {self.stats['reporter'].get('procesados', 0)} orden(es) reportada(s)")
            self.logger.info("="*80)
            
            return self.stats
            
        except Exception as e:
            self.logger.error(f"❌ Error fatal en flujo unificado: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            self._update_progress('failed', f'Error fatal: {str(e)}')
            
            # --- CORRECCION ZOMBIE PROCESS ---
            # Asegurar cierre de recursos si hay error fatal
            if self.driver_manager:
                self.logger.warning("🔌 Cerrando navegador por error fatal...")
                self.driver_manager.close()
            # ---------------------------------
            
            return self.stats
            
        finally:
            # ========================================================================
            # LIMPIEZA: Cerrar driver
            # ========================================================================
            if self.driver_manager:
                self.logger.info("")
                self.logger.info("🔌 Cerrando navegador...")
                self.driver_manager.close()
                self.logger.info("   ✅ Navegador cerrado")

    def _ensure_driver_and_login(self):
        """
        Inicializa driver y hace login. Devuelve True si OK, False si falló.
        No cierra el driver (responsabilidad del caller).
        """
        from core.reporter_bot.docker_config import get_download_dir
        download_dir = self.download_dir or str(get_download_dir())
        self.driver_manager = DriverManager(
            headless=self.headless,
            logger=self.logger,
            download_dir=download_dir,
            browser=self.browser_priority[0] if self.browser_priority else self.browser
        )
        self.driver = self.driver_manager.init_driver(browser_priority=self.browser_priority)
        if not self.driver:
            self.logger.error("❌ No se pudo inicializar el driver")
            return False
        self.auth_manager = AuthManager(
            driver=self.driver,
            user_id=self.user_id,
            logger=self.logger
        )
        self.auth_manager.load_credentials()
        if not self.auth_manager.login():
            self.logger.error("🛑 Login fallido.")
            return False
        return True

    def run_download_compare_only(self):
        """
        Ejecuta solo Download + Compare (sin Reporter). Para uso por download_compare_task.
        Cierra el driver al finalizar.
        Returns:
            dict: stats con 'downloader' y 'comparer'; total_detected en comparer.
        """
        self.stats['downloader'] = None
        self.stats['comparer'] = None
        self.stats['reporter'] = None
        self.logger.info("🔄 run_download_compare_only: Iniciando (Download + Compare)")
        try:
            if not self._ensure_driver_and_login():
                return self.stats
            from core.reporter_bot.docker_config import get_download_dir
            download_dir = self.download_dir or str(get_download_dir())
            downloader = DropiDownloader(
                driver=self.driver,
                user_id=self.user_id,
                logger=self.logger,
                download_dir=download_dir
            )
            downloaded_files = downloader.run()
            downloader_success = bool(downloaded_files)
            self.stats['downloader'] = {
                'files_downloaded': len(downloaded_files) if downloaded_files else 0,
                'success': downloader_success
            }
            if not downloader_success:
                self.stats['comparer'] = {'success': False, 'total_detected': 0}
                return self.stats
            comparer = ReportComparer(user_id=self.user_id, logger=self.logger)
            comparison_success = comparer.run()
            self.stats['comparer'] = {
                'success': comparison_success,
                'total_detected': comparer.stats.get('total_detected', 0)
            }
            return self.stats
        except Exception as e:
            self.logger.exception(f"Error en run_download_compare_only: {e}")
            return self.stats
        finally:
            if self.driver_manager:
                self.driver_manager.close()
                self.logger.info("   ✅ Navegador cerrado (download_compare_only)")

    def run_report_orders_only(self, range_start, range_end):
        """
        Ejecuta solo Reporter para el rango [range_start, range_end] (1-based).
        Asume que Download+Compare ya se ejecutó (hay OrderMovementReport pendientes).
        Cierra el driver al finalizar.
        Returns:
            dict: reporter stats (procesados, total, etc.)
        """
        self.stats['downloader'] = None
        self.stats['comparer'] = None
        self.stats['reporter'] = {'procesados': 0, 'total': 0}
        self.logger.info(f"🔄 run_report_orders_only: rango [{range_start}, {range_end}]")
        try:
            if not self._ensure_driver_and_login():
                return self.stats
            from core.reporter_bot.order_data_loader import OrderDataLoader
            loader = OrderDataLoader(user_id=self.user_id, logger=self.logger)
            df_slice = loader.load_pending_orders_slice(range_start, range_end)
            if df_slice.empty:
                self.logger.info("   No hay órdenes en este rango.")
                return self.stats
            reporter = DropiReporter(
                driver=self.driver,
                user_id=self.user_id,
                logger=self.logger,
                on_order_processed=None
            )
            reporter_stats = reporter.run(orders_df=df_slice)
            self.stats['reporter'] = reporter_stats
            return self.stats
        except Exception as e:
            self.logger.exception(f"Error en run_report_orders_only: {e}")
            return self.stats
        finally:
            if self.driver_manager:
                self.driver_manager.close()
                self.logger.info("   ✅ Navegador cerrado (report_orders_only)")


class Command(BaseCommand):
    """
    Comando de Django para ejecutar el flujo unificado
    """
    
    help = 'Flujo Unificado: Login -> Descarga -> Compara -> Reporta (Una sola sesión)'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, required=True, help='ID Usuario')
        parser.add_argument('--headless', action='store_true', help='Modo oculto')
        parser.add_argument('--download-dir', type=str, help='Directorio de descargas')

    def handle(self, *args, **options):
        from core.utils.stdio import configure_utf8_stdio
        configure_utf8_stdio()
        
        user_id = options['user_id']
        headless = options.get('headless', False)
        download_dir = options.get('download_dir')
        
        # Validar usuario
        from core.models import User
        if not User.objects.filter(id=user_id).exists():
            self.stdout.write(self.style.ERROR(f'[ERROR] Usuario con ID {user_id} no existe'))
            return
        
        # Ejecutar flujo unificado
        unified = UnifiedReporter(
            user_id=user_id,
            headless=headless,
            download_dir=download_dir
        )
        
        stats = unified.run()
        
        if stats:
            self.stdout.write(self.style.SUCCESS('[OK] Flujo unificado ejecutado exitosamente'))
        else:
            self.stdout.write(self.style.WARNING('[WARN] Flujo unificado ejecutado con advertencias'))
