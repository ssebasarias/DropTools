"""
Utilidad para añadir CPU y RAM del proceso a los logs del worker Celery.
Permite identificar picos de consumo en cada paso (downloader, reporter, etc.).
"""

import logging

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

# psutil: la primera llamada a cpu_percent(interval=None) devuelve 0.0; hay que "primar" por proceso.
_cpu_primed_pids = set()


def get_process_resources():
    """
    Obtiene uso actual de CPU (%) y RAM (MB) del proceso actual.
    En Linux/Docker la primera llamada a cpu_percent(interval=None) devuelve 0; se primea por PID.
    Usamos interval=0.1 en el priming para obtener una muestra real (evita 0% constante en workers).
    """
    if not _PSUTIL_AVAILABLE:
        return 0.0, 0
    try:
        p = psutil.Process()
        pid = p.pid
        if pid not in _cpu_primed_pids:
            # Priming: interval=0.1 da una muestra real (bloquea 0.1s); en workers fork el primer None da 0
            p.cpu_percent(interval=0.1)
            _cpu_primed_pids.add(pid)
        cpu = p.cpu_percent(interval=None)
        mem = p.memory_info().rss / (1024 * 1024)
        return round(cpu, 1), round(mem, 0)
    except Exception:
        return 0.0, 0


def format_resources():
    """Devuelve string corto 'CPU: X% RAM: Y MB' para insertar en logs."""
    cpu, ram = get_process_resources()
    return f"CPU: {cpu}% RAM: {ram:.0f} MB"


class ResourceLogger:
    """
    Wrapper de un logger que añade al final de cada mensaje el uso de recursos
    (CPU y RAM) del proceso. Así cada línea de log muestra en qué punto se
    consume más.
    """

    def __init__(self, logger):
        self._logger = logger
        # Primar CPU para que la primera línea de log ya muestre % real (no 0.0%)
        get_process_resources()

    def _msg_with_resources(self, msg, *args):
        suffix = " | " + format_resources()
        try:
            if args:
                base = msg % args
            else:
                base = str(msg)
            return base + suffix
        except (TypeError, ValueError):
            return str(msg) + suffix

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(self._msg_with_resources(msg, *args), **kwargs)

    def info(self, msg, *args, **kwargs):
        self._logger.info(self._msg_with_resources(msg, *args), **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._logger.warning(self._msg_with_resources(msg, *args), **kwargs)

    def error(self, msg, *args, **kwargs):
        self._logger.error(self._msg_with_resources(msg, *args), **kwargs)

    def exception(self, msg, *args, **kwargs):
        self._logger.exception(self._msg_with_resources(msg, *args), **kwargs)

    def critical(self, msg, *args, **kwargs):
        self._logger.critical(self._msg_with_resources(msg, *args), **kwargs)

    @property
    def logger(self):
        return self._logger
