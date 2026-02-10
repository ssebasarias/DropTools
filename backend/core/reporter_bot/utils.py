
import logging
import sys
from datetime import datetime
from pathlib import Path


class FlushingStreamHandler(logging.StreamHandler):
    """StreamHandler que hace flush tras cada mensaje (útil para ver logs en tiempo real en Docker)."""
    def emit(self, record):
        super().emit(record)
        self.flush()


def setup_logger(name='ReporterBot'):
    """
    Configura un logger centralizado para todo el módulo del bot.
    Evita duplicidad de logs y asegura formato consistente.
    Flush en consola para que Docker/terminal muestre cada línea al instante.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.hasHandlers():
        # Handler para consola (con flush para ver en tiempo real)
        console_handler = FlushingStreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Handler para archivo (rotativo idealmente, pero simple por ahora)
        # Buscar raíz del proyecto asumiendo estructura: backend/core/reporter_bot/utils.py
        log_dir = Path(__file__).resolve().parent.parent.parent.parent / 'logs'
        try:
            log_dir.mkdir(exist_ok=True)
        except: pass
        
        timestamp = datetime.now().strftime('%Y%m%d')
        file_handler = logging.FileHandler(
            log_dir / f'reporter_bot_{timestamp}.log',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Formato unificado
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    logger.propagate = False
    return logger
