"""
Comando de Django para probar el UnifiedReporter con proxy
"""
from django.core.management.base import BaseCommand
from core.reporter_bot.unified_reporter import UnifiedReporter
from core.reporter_bot.utils import setup_logger
import time

class Command(BaseCommand):
    help = 'Prueba el UnifiedReporter con proxy hardcodeado'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            default=2,
            help='ID del usuario (default: 2)'
        )
        parser.add_argument(
            '--headless',
            action='store_true',
            help='Ejecutar en modo headless'
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        headless = options['headless']
        
        logger = setup_logger('TestUnifiedReporterProxy')
        
        logger.info("="*80)
        logger.info("🧪 TEST: UnifiedReporter con Proxy Hardcodeado")
        logger.info("="*80)
        
        try:
            # Crear instancia del UnifiedReporter
            logger.info(f"📦 Creando UnifiedReporter para user_id={user_id}")
            unified = UnifiedReporter(
                user_id=user_id,
                headless=headless,
                logger=logger,
                browser='edge',
                browser_priority=['edge', 'chrome', 'firefox']
            )
            
            # Verificar que el proxy esté configurado
            proxy_config = unified._get_proxy_config()
            if proxy_config:
                logger.info("✅ Proxy configurado correctamente:")
                logger.info(f"   Host: {proxy_config['host']}")
                logger.info(f"   Port: {proxy_config['port']}")
                logger.info(f"   Username: {proxy_config.get('username', 'N/A')}")
            else:
                logger.warning("⚠️ No se configuró proxy")
            
            # Ejecutar solo la inicialización del driver y login
            logger.info("\n" + "="*80)
            logger.info("🚀 Iniciando driver y login...")
            logger.info("="*80)
            
            if unified._ensure_driver_and_login():
                logger.info("✅ Driver inicializado y login exitoso")
                
                # Verificar la IP actual
                logger.info("\n" + "="*80)
                logger.info("🌐 Verificando IP actual...")
                logger.info("="*80)
                
                try:
                    unified.driver.get("https://api.ipify.org?format=json")
                    time.sleep(2)
                    
                    # Obtener el texto de la página
                    page_source = unified.driver.page_source
                    logger.info(f"Respuesta de ipify: {page_source}")
                    
                    # Intentar navegar a Dropi
                    logger.info("\n" + "="*80)
                    logger.info("🏪 Navegando a Dropi...")
                    logger.info("="*80)
                    
                    unified.driver.get("https://app.dropi.co/dashboard/orders")
                    time.sleep(5)
                    
                    current_url = unified.driver.current_url
                    logger.info(f"URL actual: {current_url}")
                    
                    if "dropi.co" in current_url:
                        logger.info("✅ Navegación a Dropi exitosa")
                        self.stdout.write(self.style.SUCCESS('✅ TEST EXITOSO: Proxy funcionando correctamente'))
                    else:
                        logger.warning(f"⚠️ URL inesperada: {current_url}")
                        self.stdout.write(self.style.WARNING(f'⚠️ URL inesperada: {current_url}'))
                    
                except Exception as e:
                    logger.error(f"❌ Error verificando IP o navegando: {e}")
                    self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
                
                # Cerrar el driver
                logger.info("\n" + "="*80)
                logger.info("🔌 Cerrando driver...")
                logger.info("="*80)
                
                if unified.driver_manager:
                    unified.driver_manager.close()
                    logger.info("✅ Driver cerrado correctamente")
            else:
                logger.error("❌ Falló la inicialización del driver o el login")
                self.stdout.write(self.style.ERROR('❌ Falló la inicialización del driver o el login'))
            
            logger.info("\n" + "="*80)
            logger.info("✅ TEST COMPLETADO")
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"❌ Error en el test: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
