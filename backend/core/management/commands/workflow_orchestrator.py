"""
Orquestador de Flujo de Trabajo para Reportes Dropi

Este script coordina la ejecución secuencial de los tres comandos:
1. reporterdownloader.py - Descarga reportes base y actual
2. reportcomparer.py - Compara reportes y genera CSV de órdenes sin movimiento
3. reporter.py - Procesa las órdenes sin movimiento

El flujo es completamente automático con listeners que detectan cuando
cada paso termina para iniciar el siguiente.
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
import subprocess
from io import StringIO

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from core.utils.stdio import configure_utf8_stdio


class WorkflowOrchestrator:
    """
    Orquestador del flujo de trabajo completo
    
    Flujo:
    1. reporterdownloader → Genera archivos en backend/results/downloads/
    2. reportcomparer → Lee archivos de downloads/ y genera CSV en backend/results/ordenes_sin_movimiento/
    3. reporter → Lee el último CSV de ordenes_sin_movimiento/ y procesa las órdenes
    """
    
    def __init__(self, headless=False, max_wait_time=600, dropi_email=None, dropi_password=None, user_id=None, use_chrome_fallback=False):
        """
        Inicializa el orquestador
        
        Args:
            headless: Si True, ejecuta los bots en modo headless
            max_wait_time: Tiempo máximo de espera por cada paso (en segundos)
            dropi_email: Email de DropiAccount a usar (se pasa a comandos hijos)
            dropi_password: Password de DropiAccount a usar (se pasa a comandos hijos)
            user_id: ID del usuario (requerido para reporter BD)
            use_chrome_fallback: Si True, usa Chrome en lugar de Edge
        """
        self.headless = headless
        self.max_wait_time = max_wait_time
        self.dropi_email = dropi_email
        self.dropi_password = dropi_password
        self.user_id = user_id
        self.use_chrome_fallback = use_chrome_fallback
        self.logger = self._setup_logger()
        self.workflow_progress = None  # Se inicializará en run() si user_id está disponible
        
        # Directorios de trabajo
        self.base_dir = Path(__file__).parent.parent.parent.parent
        self.downloads_dir = self.base_dir / 'results' / 'downloads'
        self.ordenes_dir = self.base_dir / 'results' / 'ordenes_sin_movimiento'
        self.logs_dir = self.base_dir / 'logs'
        
        # Crear directorios si no existen
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.ordenes_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Logging de configuración inicial
        self.logger.info("="*80)
        self.logger.info("CONFIGURACIÓN INICIAL DEL ORQUESTADOR")
        self.logger.info("="*80)
        self.logger.info(f"Directorio base: {self.base_dir}")
        self.logger.info(f"Directorio de descargas: {self.downloads_dir}")
        self.logger.info(f"Directorio de órdenes: {self.ordenes_dir}")
        self.logger.info(f"Directorio de logs: {self.logs_dir}")
        self.logger.info("="*80)
        
        # Estadísticas
        self.stats = {
            'inicio': None,
            'fin': None,
            'paso1_inicio': None,
            'paso1_fin': None,
            'paso1_exito': False,
            'paso2_inicio': None,
            'paso2_fin': None,
            'paso2_exito': False,
            'paso3_inicio': None,
            'paso3_fin': None,
            'paso3_exito': False,
            'archivos_descargados': [],
            'csv_generado': None,
            'ordenes_procesadas': 0
        }
    
    def _setup_logger(self):
        """Configura el logger para el orquestador"""
        logger = logging.getLogger('WorkflowOrchestrator')
        logger.setLevel(logging.INFO)
        
        # Limpiar handlers existentes
        logger.handlers.clear()
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Handler para archivo
        log_dir = Path(__file__).parent.parent.parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_handler = logging.FileHandler(
            log_dir / f'workflow_orchestrator_{timestamp}.log',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Formato
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def _update_workflow_progress(self, status, message=None, add_to_messages=True):
        """
        Actualiza el progreso del workflow en la base de datos
        
        Args:
            status: Nuevo estado del workflow
            message: Mensaje opcional a agregar
            add_to_messages: Si True, agrega el mensaje a la lista de mensajes
        """
        if not self.user_id or not self.workflow_progress:
            return
        
        try:
            from django.utils import timezone
            from core.models import WorkflowProgress
            
            # Obtener el progreso actual
            progress = WorkflowProgress.objects.filter(id=self.workflow_progress.id).first()
            if not progress:
                return
            
            # Actualizar estado
            progress.status = status
            if message:
                progress.current_message = message
                if add_to_messages:
                    if not progress.messages:
                        progress.messages = []
                    progress.messages.append(message)
            
            # Actualizar timestamps según el paso completado
            if status == 'step1_completed':
                progress.step1_completed_at = timezone.now()
            elif status == 'step2_completed':
                progress.step2_completed_at = timezone.now()
            elif status == 'step3_completed':
                progress.step3_completed_at = timezone.now()
            elif status == 'completed':
                progress.completed_at = timezone.now()
            
            progress.save()
            
        except Exception as e:
            # No fallar el workflow si hay error al actualizar progreso
            self.logger.warning(f"   ⚠️ Error al actualizar progreso: {str(e)}")
    
    def _get_latest_file(self, directory, pattern, recursive=False):
        """
        Obtiene el archivo más reciente que coincida con el patrón
        
        Args:
            directory: Directorio donde buscar
            pattern: Patrón de búsqueda (glob)
            recursive: Si True, busca recursivamente en subdirectorios
        
        Returns:
            Path del archivo más reciente o None
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            return None
        
        # Buscar archivos (recursivamente si se especifica)
        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))
        
        if not files:
            return None
        
        # Ordenar por fecha de modificación (más reciente primero)
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return files[0]
    
    def _wait_for_new_file(self, directory, pattern, initial_files, timeout=600):
        """
        Espera a que aparezca un nuevo archivo en el directorio
        
        Args:
            directory: Directorio a monitorear
            pattern: Patrón de archivos a buscar
            initial_files: Set de archivos que ya existían antes
            timeout: Tiempo máximo de espera en segundos
        
        Returns:
            Path del nuevo archivo o None si timeout
        """
        self.logger.info(f"   Monitoreando directorio: {directory}")
        self.logger.info(f"   Patrón de búsqueda: {pattern}")
        self.logger.info(f"   Timeout: {timeout} segundos")
        
        start_time = time.time()
        check_interval = 5  # Verificar cada 5 segundos
        
        while time.time() - start_time < timeout:
            elapsed = int(time.time() - start_time)
            
            # Obtener archivos actuales
            current_files = set(Path(directory).glob(pattern))
            
            # Buscar archivos nuevos
            new_files = current_files - initial_files
            
            if new_files:
                # Hay archivos nuevos, obtener el más reciente
                new_files_list = list(new_files)
                new_files_list.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                newest_file = new_files_list[0]
                
                self.logger.info(f"   ✅ Nuevo archivo detectado: {newest_file.name}")
                return newest_file
            
            # Log de progreso cada 30 segundos
            if elapsed % 30 == 0 and elapsed > 0:
                self.logger.info(f"   ⏳ Esperando... ({elapsed}/{timeout}s)")
            
            time.sleep(check_interval)
        
        self.logger.error(f"   ❌ Timeout: No se detectó ningún archivo nuevo en {timeout}s")
        return None
    
    def _get_manage_py_path(self):
        """
        Obtiene la ruta absoluta a manage.py
        
        Returns:
            Path: Ruta absoluta a manage.py
        
        Raises:
            FileNotFoundError: Si no se encuentra manage.py
        """
        # Buscar manage.py desde el directorio base
        manage_py = self.base_dir / 'manage.py'
        
        if manage_py.exists():
            return manage_py
        
        # Si no se encuentra, intentar desde el directorio actual
        current = Path.cwd()
        manage_py = current / 'manage.py'
        if manage_py.exists():
            return manage_py
        
        # Si aún no se encuentra, buscar en el directorio padre
        manage_py = current.parent / 'manage.py'
        if manage_py.exists():
            return manage_py
        
        # Si no se encuentra en ningún lugar, lanzar error
        raise FileNotFoundError(
            f"No se encontró manage.py. Buscado en:\n"
            f"  - {self.base_dir / 'manage.py'}\n"
            f"  - {current / 'manage.py'}\n"
            f"  - {current.parent / 'manage.py'}"
        )
    
    def _run_command(self, command, step_name):
        """
        Ejecuta un comando de Django usando call_command (más robusto que subprocess)
        
        Args:
            command: Lista con el comando a ejecutar (ej: ['reporterdownloader', '--email', '...'])
            step_name: Nombre del paso (para logging)
        
        Returns:
            True si el comando se ejecutó exitosamente, False en caso contrario
        """
        if not command:
            self.logger.error(f"   [ERROR] Comando vacío")
            return False
        
        command_name = command[0]
        command_args = command[1:] if len(command) > 1 else []
        
        # Convertir args a diccionario para call_command
        # Formato: ['--email', 'test@test.com', '--headless'] -> {'email': 'test@test.com', 'headless': True}
        kwargs = {}
        i = 0
        while i < len(command_args):
            arg = command_args[i]
            if arg.startswith('--'):
                key = arg[2:].replace('-', '_')
                # Verificar si hay un valor siguiente
                if i + 1 < len(command_args) and not command_args[i + 1].startswith('--'):
                    kwargs[key] = command_args[i + 1]
                    i += 2
                else:
                    # Es un flag booleano
                    kwargs[key] = True
                    i += 1
            else:
                i += 1
        
        self.logger.info(f"   Ejecutando comando Django: {command_name}")
        if kwargs:
            self.logger.info(f"   Argumentos: {kwargs}")
        
        try:
            # Usar call_command que es más robusto y mantiene el contexto de Django
            # Capturar salida en StringIO para logging
            out = StringIO()
            err = StringIO()
            
            # Ejecutar el comando con mejor manejo de errores
            try:
                call_command(
                    command_name,
                    stdout=out,
                    stderr=err,
                    **kwargs
                )
                command_success = True
            except SystemExit as exit_e:
                # call_command puede hacer sys.exit(0) o sys.exit(1)
                # Si es 0, fue exitoso
                command_success = (exit_e.code == 0)
                if not command_success:
                    self.logger.error(f"   [ERROR] Comando falló con código: {exit_e.code}")
            except Exception as cmd_e:
                # Capturar el error pero continuar para loggear la salida
                command_success = False
                self.logger.error(f"   [ERROR] Excepción al ejecutar comando: {str(cmd_e)}")
                import traceback
                self.logger.error(f"   [ERROR] Traceback: {traceback.format_exc()}")
            
            # Log de salida estándar (siempre, incluso si falló)
            output = out.getvalue()
            if output:
                for line in output.split('\n'):
                    if line.strip():
                        # Detectar errores en la salida
                        if any(keyword in line.lower() for keyword in ['error', 'exception', 'traceback', 'failed', 'falló']):
                            self.logger.error(f"   [{step_name}] {line}")
                        else:
                            self.logger.info(f"   [{step_name}] {line}")
            
            # Log de errores
            error_output = err.getvalue()
            if error_output:
                for line in error_output.split('\n'):
                    if line.strip():
                        self.logger.error(f"   [{step_name}] STDERR: {line}")
            
            if command_success:
                self.logger.info(f"   [OK] Comando ejecutado exitosamente")
                return True
            else:
                self.logger.error(f"   [ERROR] Comando falló")
                return False
                
        except Exception as e:
            self.logger.error(f"   ❌ Error crítico al ejecutar comando: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def paso1_reporterdownloader(self):
        """
        PASO 1: Ejecutar reporterdownloader para descargar reportes
        
        Returns:
            dict con 'exito' (bool) y 'archivos' (list)
        """
        self.logger.info("="*80)
        self.logger.info("PASO 1: DESCARGANDO REPORTES (reporterdownloader)")
        self.logger.info("="*80)
        
        self.stats['paso1_inicio'] = datetime.now()
        
        try:
            # Obtener archivos existentes antes de ejecutar (búsqueda recursiva en subcarpetas)
            initial_files = set(self.downloads_dir.rglob('*.xlsx'))
            self.logger.info(f"   Archivos existentes antes: {len(initial_files)}")
            self.logger.info(f"   Buscando en: {self.downloads_dir} (recursivo)")
            
            # Construir comando (sin 'python' ni 'manage.py', ya se agregan en _run_command)
            command = ['reporterdownloader']

            # Pasar credenciales directamente a los comandos hijos
            if self.dropi_email:
                command += ['--email', self.dropi_email]
            if self.dropi_password:
                command += ['--password', self.dropi_password]
            
            if self.headless:
                command.append('--headless')
            
            if self.use_chrome_fallback:
                command.append('--use-chrome-fallback')
            
            # Ejecutar comando
            success = self._run_command(command, "PASO1")
            
            if not success:
                self.logger.error("   ❌ reporterdownloader falló durante la ejecución")
                # Actualizar progreso con error específico
                if self.workflow_progress:
                    self._update_workflow_progress(
                        'failed',
                        'Error: Falló la descarga de reportes',
                        add_to_messages=True
                    )
                return {'exito': False, 'archivos': []}
            
            # Esperar a que aparezcan los archivos (incluso si el comando falló por encoding)
            self.logger.info("   Esperando archivos descargados...")
            time.sleep(10)  # Espera inicial para que se completen las descargas
            
            # Obtener archivos nuevos (búsqueda recursiva)
            current_files = set(self.downloads_dir.rglob('*.xlsx'))
            new_files = current_files - initial_files
            
            # Si no hay archivos nuevos, intentar obtener los más recientes con formato correcto
            if not new_files:
                self.logger.warning("   ⚠️ No se detectaron archivos nuevos")
                self.logger.info("   Buscando archivos más recientes con formato reporte_*.xlsx...")
                
                # Buscar archivos con el formato correcto: reporte_YYYYMMDD.xlsx
                latest_report = self._get_latest_file(self.downloads_dir, 'reporte_*.xlsx', recursive=True)
                
                if latest_report:
                    # Verificar que sea reciente (modificado en los últimos 5 minutos)
                    file_age = time.time() - latest_report.stat().st_mtime
                    if file_age < 300:  # 5 minutos
                        new_files = {latest_report}
                        self.logger.info(f"   ℹ️ Usando archivo más reciente: {latest_report.name}")
                    else:
                        self.logger.error(f"   ❌ Archivo encontrado pero es muy antiguo ({file_age:.0f}s)")
                        return {'exito': False, 'archivos': []}
                else:
                    self.logger.error("   ❌ No se encontraron archivos de reportes")
                    return {'exito': False, 'archivos': []}
            
            # Si encontramos archivos, el paso fue exitoso (incluso si el comando retornó error)
            if new_files:
                if not success:
                    self.logger.warning("   ⚠️ El comando reporterdownloader retornó error, pero los archivos se generaron correctamente")
                    self.logger.info("   ✅ Continuando con el flujo...")
            
            new_files_list = list(new_files)
            self.logger.info(f"   ✅ Archivos detectados: {len(new_files_list)}")
            for f in new_files_list:
                self.logger.info(f"      - {f.relative_to(self.base_dir)}")
            
            self.stats['paso1_exito'] = True
            self.stats['archivos_descargados'] = [str(f) for f in new_files_list]
            
            # Actualizar progreso si hay órdenes reportadas hoy
            if self.workflow_progress:
                from django.utils import timezone
                from core.models import OrderReport
                today_reports = OrderReport.objects.filter(
                    user_id=self.user_id,
                    status='reportado',
                    updated_at__date=timezone.now().date()
                ).count()
                if today_reports > 0:
                    self._update_workflow_progress(
                        'step1_completed',
                        f'Se ha creado el reporte del día (puedes ver el resumen en la página dashboard). {today_reports} órdenes reportadas hoy.',
                        add_to_messages=False
                    )
            
            return {'exito': True, 'archivos': new_files_list}
            
        except Exception as e:
            self.logger.error(f"   ❌ Error en PASO 1: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {'exito': False, 'archivos': []}
        
        finally:
            self.stats['paso1_fin'] = datetime.now()
    
    def paso2_reportcomparer(self):
        """
        PASO 2: Ejecutar reportcomparer para comparar reportes
        
        Returns:
            dict con 'exito' (bool) y 'csv_path' (str)
        """
        self.logger.info("")
        self.logger.info("="*80)
        self.logger.info("PASO 2: COMPARANDO REPORTES (reportcomparer)")
        self.logger.info("="*80)
        
        self.stats['paso2_inicio'] = datetime.now()
        
        try:
            # Obtener archivos existentes antes de ejecutar
            initial_files = set(self.ordenes_dir.glob('*.csv'))
            self.logger.info(f"   Archivos CSV existentes antes: {len(initial_files)}")
            
            # Construir comando (sin argumentos, buscará automáticamente)
            # reportcomparer busca automáticamente en results/downloads/ con subcarpetas por mes
            command = ['reportcomparer']
            
            # Ejecutar comando
            success = self._run_command(command, "PASO2")
            
            if not success:
                self.logger.error("   ❌ reportcomparer falló")
                return {'exito': False, 'csv_path': None}
            
            # Esperar a que aparezca el CSV (dar tiempo suficiente para escritura)
            self.logger.info("   Esperando generación de CSV...")
            time.sleep(5)
            
            # Buscar el CSV más reciente
            csv_file = self._get_latest_file(self.ordenes_dir, 'ordenes_sin_movimiento_*.csv')
            
            if not csv_file:
                self.logger.error("   ❌ No se encontró el CSV generado")
                self.logger.error(f"   Buscado en: {self.ordenes_dir}")
                return {'exito': False, 'csv_path': None}
            
            # Verificar que el CSV sea reciente (generado en los últimos 2 minutos)
            file_age = time.time() - csv_file.stat().st_mtime
            if file_age > 120:
                self.logger.warning(f"   ⚠️ CSV encontrado pero es antiguo ({file_age:.0f}s)")
                self.logger.warning("   Puede ser un archivo de una ejecución anterior")
            
            self.logger.info(f"   ✅ CSV generado: {csv_file.name}")
            self.logger.info(f"   Ruta completa: {csv_file}")
            
            self.stats['paso2_exito'] = True
            self.stats['csv_generado'] = str(csv_file)
            
            return {'exito': True, 'csv_path': str(csv_file)}
            
        except Exception as e:
            self.logger.error(f"   ❌ Error en PASO 2: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {'exito': False, 'csv_path': None}
        
        finally:
            self.stats['paso2_fin'] = datetime.now()
    
    def paso3_reporter(self, csv_path):
        """
        PASO 3: Ejecutar reporter para procesar órdenes
        
        Args:
            csv_path: Ruta al CSV con las órdenes sin movimiento
        
        Returns:
            dict con 'exito' (bool)
        """
        self.logger.info("")
        self.logger.info("="*80)
        self.logger.info("PASO 3: PROCESANDO ÓRDENES (reporter)")
        self.logger.info("="*80)
        
        self.stats['paso3_inicio'] = datetime.now()
        
        try:
            # Verificar que el archivo CSV existe
            csv_file = Path(csv_path)
            if not csv_file.exists():
                self.logger.error(f"   ❌ El archivo CSV no existe: {csv_path}")
                return {'exito': False}
            
            # Convertir a ruta absoluta si es relativa
            if not csv_file.is_absolute():
                csv_file = self.base_dir / csv_path
                if not csv_file.exists():
                    self.logger.error(f"   ❌ El archivo CSV no existe en ruta absoluta: {csv_file}")
                    return {'exito': False}
            
            self.logger.info(f"   Archivo CSV a procesar: {csv_file}")
            self.logger.info(f"   Tamaño del archivo: {csv_file.stat().st_size:,} bytes")
            
            # Construir comando
            command = ['reporter', '--excel', str(csv_file)]

            # Pasar user_id (requerido para BD)
            if hasattr(self, 'user_id') and self.user_id:
                command += ['--user-id', str(self.user_id)]

            # Pasar credenciales directamente a los comandos hijos
            if self.dropi_email:
                command += ['--email', self.dropi_email]
            if self.dropi_password:
                command += ['--password', self.dropi_password]
            
            if self.headless:
                command.append('--headless')
            
            # Ejecutar comando
            success = self._run_command(command, "PASO3")
            
            if not success:
                self.logger.error("   ❌ reporter falló")
                return {'exito': False}
            
            self.logger.info(f"   ✅ Órdenes procesadas exitosamente")
            
            self.stats['paso3_exito'] = True
            
            return {'exito': True}
            
        except Exception as e:
            self.logger.error(f"   ❌ Error en PASO 3: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {'exito': False}
        
        finally:
            self.stats['paso3_fin'] = datetime.now()
    
    def run(self):
        """Ejecuta el flujo de trabajo completo"""
        self.logger.info("="*80)
        self.logger.info("INICIANDO FLUJO DE TRABAJO COMPLETO")
        self.logger.info("="*80)
        self.logger.info(f"Modo headless: {self.headless}")
        self.logger.info(f"Tiempo máximo por paso: {self.max_wait_time}s")
        
        # Inicializar progreso del workflow si user_id está disponible
        if self.user_id:
            try:
                from core.models import User
                from core.models import WorkflowProgress
                from django.utils import timezone
                
                user = User.objects.filter(id=self.user_id).first()
                if user:
                    # Obtener el progreso más reciente del usuario que esté en estado inicial o corriendo
                    # Esto asegura que usemos el progreso creado por ReporterStartView
                    self.workflow_progress = WorkflowProgress.objects.filter(
                        user=user
                    ).filter(
                        status__in=['pending', 'step1_running', 'step2_running', 'step3_running']
                    ).order_by('-started_at').first()
                    
                    # Si no hay progreso activo, buscar el más reciente de cualquier estado
                    if not self.workflow_progress:
                        self.workflow_progress = WorkflowProgress.objects.filter(user=user).order_by('-started_at').first()
                    
                    # Si aún no existe, crear uno nuevo (fallback)
                    if not self.workflow_progress:
                        self.workflow_progress = WorkflowProgress.objects.create(
                            user=user,
                            status='step1_running',
                            current_message='Esto puede tardar unos minutos...',
                            messages=['Esto puede tardar unos minutos...']
                        )
            except Exception as e:
                self.logger.warning(f"   ⚠️ No se pudo inicializar progreso del workflow: {str(e)}")
        
        # Validar que manage.py existe antes de comenzar
        try:
            manage_py = self._get_manage_py_path()
            self.logger.info(f"manage.py encontrado: {manage_py}")
        except FileNotFoundError as e:
            self.logger.error("="*80)
            self.logger.error("❌ ERROR: No se encontró manage.py")
            self.logger.error("="*80)
            self.logger.error(str(e))
            if self.workflow_progress:
                self._update_workflow_progress('failed', 'Error: No se encontró manage.py')
            return False
        
        self.logger.info("="*80)
        
        self.stats['inicio'] = datetime.now()
        
        try:
            # PASO 1: Descargar reportes
            self._update_workflow_progress('step1_running', 'Descargando reportes del día...')
            resultado1 = self.paso1_reporterdownloader()
            
            if not resultado1['exito']:
                self.logger.error("")
                self.logger.error("="*80)
                self.logger.error("❌ FLUJO INTERRUMPIDO: PASO 1 FALLÓ")
                self.logger.error("="*80)
                if self.workflow_progress:
                    self._update_workflow_progress('failed', 'Error: Falló la descarga de reportes')
                return False
            
            # Paso 1 completado
            self._update_workflow_progress('step1_completed', 'Se ha creado el reporte del día (puedes ver el resumen en la página dashboard)')
            
            # PASO 2: Comparar reportes
            self._update_workflow_progress('step2_running', 'Comparando reportes y obteniendo órdenes sin movimiento...')
            resultado2 = self.paso2_reportcomparer()
            
            if not resultado2['exito']:
                self.logger.error("")
                self.logger.error("="*80)
                self.logger.error("❌ FLUJO INTERRUMPIDO: PASO 2 FALLÓ")
                self.logger.error("="*80)
                if self.workflow_progress:
                    self._update_workflow_progress('failed', 'Error: Falló la comparación de reportes')
                return False
            
            # Verificar que se generó el CSV
            if not resultado2['csv_path']:
                self.logger.error("")
                self.logger.error("="*80)
                self.logger.error("❌ FLUJO INTERRUMPIDO: NO SE GENERÓ CSV")
                self.logger.error("="*80)
                if self.workflow_progress:
                    self._update_workflow_progress('failed', 'Error: No se generó el CSV de órdenes')
                return False
            
            # Paso 2 completado
            self._update_workflow_progress('step2_completed', 'Se han obtenido las órdenes sin movimiento')
            
            # PASO 3: Procesar órdenes
            self._update_workflow_progress('step3_running', 'Comenzando a reportar CAS, puedes ver la lista de las órdenes reportadas')
            resultado3 = self.paso3_reporter(resultado2['csv_path'])
            
            if not resultado3['exito']:
                self.logger.error("")
                self.logger.error("="*80)
                self.logger.error("❌ FLUJO INTERRUMPIDO: PASO 3 FALLÓ")
                self.logger.error("="*80)
                if self.workflow_progress:
                    self._update_workflow_progress('failed', 'Error: Falló el proceso de reporte CAS')
                return False
            
            # Paso 3 completado
            self._update_workflow_progress('step3_completed', 'Proceso de reporte CAS completado')
            
            # ÉXITO COMPLETO
            self.logger.info("")
            self.logger.info("="*80)
            self.logger.info("✅ FLUJO DE TRABAJO COMPLETADO EXITOSAMENTE")
            self.logger.info("="*80)
            
            if self.workflow_progress:
                self._update_workflow_progress('completed', 'Workflow completado exitosamente')
            
            self._print_final_stats()
            
            return True
            
        except Exception as e:
            self.logger.error("")
            self.logger.error("="*80)
            self.logger.error(f"❌ ERROR FATAL EN FLUJO DE TRABAJO: {str(e)}")
            self.logger.error("="*80)
            import traceback
            self.logger.error(traceback.format_exc())
            return False
        
        finally:
            self.stats['fin'] = datetime.now()
    
    def _print_final_stats(self):
        """Imprime las estadísticas finales del flujo"""
        self.logger.info("")
        self.logger.info("="*80)
        self.logger.info("RESUMEN DEL FLUJO DE TRABAJO")
        self.logger.info("="*80)
        
        # Tiempos
        if self.stats['inicio'] and self.stats['fin']:
            duracion_total = self.stats['fin'] - self.stats['inicio']
            self.logger.info(f"Duración total: {duracion_total}")
        
        # PASO 1
        self.logger.info("")
        self.logger.info("PASO 1: Descarga de reportes")
        self.logger.info(f"  Estado: {'✅ ÉXITO' if self.stats['paso1_exito'] else '❌ FALLO'}")
        if self.stats['paso1_inicio'] and self.stats['paso1_fin']:
            duracion = self.stats['paso1_fin'] - self.stats['paso1_inicio']
            self.logger.info(f"  Duración: {duracion}")
        if self.stats['archivos_descargados']:
            self.logger.info(f"  Archivos descargados: {len(self.stats['archivos_descargados'])}")
            for archivo in self.stats['archivos_descargados']:
                self.logger.info(f"    - {Path(archivo).name}")
        
        # PASO 2
        self.logger.info("")
        self.logger.info("PASO 2: Comparación de reportes")
        self.logger.info(f"  Estado: {'✅ ÉXITO' if self.stats['paso2_exito'] else '❌ FALLO'}")
        if self.stats['paso2_inicio'] and self.stats['paso2_fin']:
            duracion = self.stats['paso2_fin'] - self.stats['paso2_inicio']
            self.logger.info(f"  Duración: {duracion}")
        if self.stats['csv_generado']:
            self.logger.info(f"  CSV generado: {Path(self.stats['csv_generado']).name}")
        
        # PASO 3
        self.logger.info("")
        self.logger.info("PASO 3: Procesamiento de órdenes")
        self.logger.info(f"  Estado: {'✅ ÉXITO' if self.stats['paso3_exito'] else '❌ FALLO'}")
        if self.stats['paso3_inicio'] and self.stats['paso3_fin']:
            duracion = self.stats['paso3_fin'] - self.stats['paso3_inicio']
            self.logger.info(f"  Duración: {duracion}")
        
        self.logger.info("="*80)


class Command(BaseCommand):
    """Comando de Django para ejecutar el orquestador de flujo de trabajo"""
    
    help = 'Ejecuta el flujo de trabajo completo: reporterdownloader → reportcomparer → reporter'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--headless',
            action='store_true',
            help='Ejecutar los bots en modo headless (sin interfaz gráfica)'
        )
        
        parser.add_argument(
            '--max-wait',
            type=int,
            default=600,
            help='Tiempo máximo de espera por cada paso en segundos (default: 600)'
        )

        parser.add_argument(
            '--user-id',
            type=int,
            default=None,
            help='ID del usuario (tabla users.id) con suscripción activa. Alternativa a --user-email.'
        )

        parser.add_argument(
            '--user-email',
            type=str,
            default=None,
            help='Email del usuario cliente con suscripción activa. El orquestador buscará el usuario por email y obtendrá sus credenciales DropiAccount.'
        )

        parser.add_argument(
            '--dropi-label',
            type=str,
            default='reporter',
            help='Etiqueta DropiAccount a usar para el workflow (default: reporter).'
        )
        
        parser.add_argument(
            '--use-chrome-fallback',
            action='store_true',
            help='Usar Chrome en lugar de Edge (útil si Edge no funciona o no está disponible)'
        )
    
    def handle(self, *args, **options):
        configure_utf8_stdio()
        headless = options['headless']
        max_wait = options['max_wait']
        user_id = options.get('user_id')
        user_email = options.get('user_email')
        dropi_label = options.get('dropi_label', 'reporter')
        use_chrome_fallback = options.get('use_chrome_fallback', False)
        
        self.stdout.write("="*80)
        self.stdout.write(self.style.SUCCESS('INICIANDO ORQUESTADOR DE FLUJO DE TRABAJO'))
        self.stdout.write("="*80)
        
        # Validar que se proporcionó user_id o user_email
        if not user_id and not user_email:
            self.stdout.write(
                self.style.ERROR(
                    '[ERROR] Debes proporcionar --user-id o --user-email para identificar al usuario cliente'
                )
            )
            sys.exit(1)
        
        # Obtener credenciales DropiAccount del usuario
        dropi_email = None
        dropi_password = None
        
        try:
            from core.models import User
            
            # Buscar usuario por ID o email
            user = None

            if user_id:
                user = User.objects.filter(id=user_id).first()
                if not user:
                    self.stdout.write(
                        self.style.ERROR(f'[ERROR] Usuario con ID {user_id} no existe')
                    )
                    sys.exit(1)
            elif user_email:
                # Buscar por email o username (ahora todo está en la tabla users)
                user = (
                    User.objects.filter(email=user_email).first()
                    or User.objects.filter(username=user_email).first()
                )
                
                if not user:
                    self.stdout.write(
                        self.style.ERROR(
                            f'[ERROR] Usuario con email "{user_email}" no existe'
                        )
                    )
                    sys.exit(1)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'[INFO] Usuario encontrado: ID={user.id}, Email={user.email}'
                        )
                    )
            
            # Verificar que el usuario tiene suscripción activa (ahora está en User directamente)
            if user.role != "ADMIN" and not user.subscription_active:
                self.stdout.write(
                    self.style.ERROR(
                        f'[ERROR] Usuario {user.email} (ID: {user.id}) no tiene suscripción activa. '
                        f'Rol: {user.role}, Suscripción activa: {user.subscription_active}'
                    )
                )
                sys.exit(1)
            # Mostrar información de suscripción
            self.stdout.write(
                self.style.SUCCESS(
                    f'[INFO] Usuario verificado: Rol={user.role}, '
                    f'Tier={user.subscription_tier}, Suscripción activa={user.subscription_active}'
                )
            )
            
            # Obtener credenciales Dropi directamente del usuario (ahora están en la tabla users)
            if not user.dropi_email or not user.dropi_password:
                self.stdout.write(
                    self.style.ERROR(
                        f'[ERROR] Usuario {user.email} (ID: {user.id}) no tiene credenciales Dropi configuradas. '
                        f'Por favor configura dropi_email y dropi_password para este usuario.'
                    )
                )
                sys.exit(1)
            
            dropi_email = user.dropi_email
            dropi_password = user.get_dropi_password_plain()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'[INFO] Credenciales Dropi obtenidas exitosamente: '
                    f'Email={dropi_email}, Usuario={user.email} (ID: {user.id})'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error al obtener credenciales: {str(e)}')
            )
            import traceback
            self.stdout.write(traceback.format_exc())
            sys.exit(1)
        
        # Obtener user_id del usuario encontrado
        user_id_for_orchestrator = user.id if user else None
        
        # Crear y ejecutar el orquestador con credenciales
        orchestrator = WorkflowOrchestrator(
            headless=headless,
            max_wait_time=max_wait,
            dropi_email=dropi_email,
            dropi_password=dropi_password,
            user_id=user_id_for_orchestrator,
            use_chrome_fallback=use_chrome_fallback
        )
        
        try:
            success = orchestrator.run()
            
            if success:
                self.stdout.write("")
                self.stdout.write(
                    self.style.SUCCESS('[OK] Flujo de trabajo completado exitosamente')
                )
            else:
                self.stdout.write("")
                self.stdout.write(
                    self.style.ERROR('[ERROR] Flujo de trabajo falló')
                )
                sys.exit(1)
                
        except Exception as e:
            self.stdout.write("")
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error fatal: {str(e)}')
            )
            raise
