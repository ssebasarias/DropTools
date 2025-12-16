from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        # Evitar ejecución duplicada en modo autoreload de Django dev server
        import os
        if os.environ.get('RUN_MAIN') or os.environ.get('WERKZEUG_RUN_MAIN'):
            from .docker_utils import start_monitoring_thread
            start_monitoring_thread()
