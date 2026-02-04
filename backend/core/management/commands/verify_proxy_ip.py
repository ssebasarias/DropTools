"""
Comando para verificar la IP real usada por Selenium con el proxy de DEV.
Abre el navegador con proxy (proxy_dev_config.json), visita api.ipify.org e imprime la IP.
No loguea contraseñas.

Uso:
  python manage.py verify_proxy_ip

Con Docker:
  docker compose exec backend python manage.py verify_proxy_ip
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings


def _load_proxy_config():
    """Carga proxy desde backend/proxy_dev_config.json. No loguea contraseñas."""
    base = getattr(settings, 'BASE_DIR', Path(__file__).resolve().parent.parent.parent.parent)
    path = Path(base) / 'proxy_dev_config.json'
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return None
    proxy = data.get('proxy') or {}
    host = proxy.get('host') or ''
    port = proxy.get('port') or 8080
    if not host:
        return None
    config = {'host': host, 'port': int(port)}
    if proxy.get('username'):
        config['username'] = proxy['username']
    if proxy.get('password'):
        config['password'] = proxy['password']
    return config


class Command(BaseCommand):
    help = 'Verifica la IP visible con el proxy de DEV (proxy_dev_config.json). Visita api.ipify.org.'

    def handle(self, *args, **options):
        proxy_config = _load_proxy_config()
        if not proxy_config:
            self.stdout.write(self.style.ERROR('No se encontró proxy_dev_config.json o proxy vacío.'))
            self.stdout.write('Copia proxy_dev_config.example.json a proxy_dev_config.json y configura host/port.')
            return

        self.stdout.write(f"Proxy configurado: {proxy_config['host']}:{proxy_config['port']} (sin loguear credenciales)")

        from core.reporter_bot.driver_manager import DriverManager

        DriverManager.reset_singleton()
        dm = DriverManager(
            headless=True,
            logger=None,
            download_dir=None,
            browser='edge',
            proxy_config=proxy_config,
        )
        try:
            driver = dm.init_driver(browser_priority=['edge', 'chrome'])
            driver.get('https://api.ipify.org')
            ip = (driver.find_element('tag name', 'body').text or '').strip()
            self.stdout.write(self.style.SUCCESS(f'IP detectada (con proxy): {ip}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
        finally:
            dm.close()
            DriverManager.reset_singleton()
