"""
Comando Django para ejecutar el flujo unificado de reportes

Este comando utiliza el UnifiedReporter del paquete reporter_bot
para ejecutar todo el flujo en una única sesión de navegador.
"""

from django.core.management.base import BaseCommand
from core.reporter_bot.unified_reporter import UnifiedReporter
from core.utils.stdio import configure_utf8_stdio


class Command(BaseCommand):
    """
    Comando de Django para ejecutar el flujo unificado de reportes.
    
    Ejecuta: Login -> Descarga -> Compara -> Reporta
    Todo en una única sesión de navegador persistente.
    """
    
    help = 'Flujo Unificado: Login -> Descarga -> Compara -> Reporta (Una sola sesión)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            required=True,
            help='ID del usuario Django'
        )
        parser.add_argument(
            '--headless',
            action='store_true',
            help='Ejecutar el navegador en modo headless (sin interfaz gráfica)'
        )
        parser.add_argument(
            '--download-dir',
            type=str,
            help='Directorio donde se guardarán los archivos descargados (opcional)'
        )
        parser.add_argument(
            '--browser',
            type=str,
            choices=['chrome', 'edge', 'brave', 'firefox'],
            default='edge',
            help='Navegador a usar (default: edge)'
        )

    def handle(self, *args, **options):
        configure_utf8_stdio()
        
        user_id = options['user_id']
        headless = options.get('headless', False)
        download_dir = options.get('download_dir')
        browser = options.get('browser', 'edge')
        
        # Validar usuario
        from core.models import User
        if not User.objects.filter(id=user_id).exists():
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Usuario con ID {user_id} no existe')
            )
            return
        
        # Ejecutar flujo unificado
        unified = UnifiedReporter(
            user_id=user_id,
            headless=headless,
            download_dir=download_dir,
            browser=browser
        )
        
        try:
            stats = unified.run()
            
            if stats:
                self.stdout.write(
                    self.style.SUCCESS('[OK] Flujo unificado ejecutado exitosamente')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('[WARN] Flujo unificado ejecutado con advertencias')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error al ejecutar flujo unificado: {str(e)}')
            )
            raise
