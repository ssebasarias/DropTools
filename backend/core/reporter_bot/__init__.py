"""
Reporter Bot - Sistema Modular Unificado para Automatización Dropi

Este paquete contiene todos los módulos necesarios para ejecutar el flujo completo
de descarga, comparación y reporte de órdenes en una única sesión de navegador.

Módulos:
- driver_manager: Gestión del WebDriver (Singleton)
- auth_manager: Autenticación y gestión de sesión
- downloader: Descarga de reportes Excel
- comparer: Comparación de reportes (lógica BD pura)
- reporter: Generación de reportes en la web (módulo principal)
  - order_data_loader: Carga de órdenes desde BD
  - order_searcher: Búsqueda y validación de órdenes
  - report_form_handler: Manejo del formulario de reporte
  - popup_handler: Manejo de popups y alertas
  - report_result_manager: Guardado de resultados en BD
- unified_reporter: Orquestador del flujo completo (Downloader + Comparer + Reporter)
- utils: Utilidades compartidas (logger, etc.)
"""

from .driver_manager import DriverManager
from .auth_manager import AuthManager
from .downloader import DropiDownloader
from .comparer import ReportComparer
from .reporter import DropiReporter
from .unified_reporter import UnifiedReporter, Command as UnifiedReporterCommand
from .utils import setup_logger

__all__ = [
    'DriverManager',
    'AuthManager',
    'DropiDownloader',
    'ReportComparer',
    'DropiReporter',
    'UnifiedReporter',
    'UnifiedReporterCommand',
    'setup_logger',
]
