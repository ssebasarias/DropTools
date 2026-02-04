"""
Verifica el proxy de DEV usando requests (igual que el ejemplo de ResiProx).
Sin Selenium: solo comprueba si el proxy responde y devuelve una IP.

Si esto funciona y el reporter sigue con página en blanco, el fallo está
en cómo Chrome/Selenium usa el proxy (extensión de auth, etc.).
Si esto falla, el proxy no es alcanzable desde Docker o las credenciales son incorrectas.

Uso:
  python manage.py verify_proxy_requests

Con Docker (misma red que celery_worker):
  docker compose exec backend python manage.py verify_proxy_requests
  docker compose exec celery_worker python manage.py verify_proxy_requests
"""
import json
from pathlib import Path
from urllib.parse import quote

from django.core.management.base import BaseCommand
from django.conf import settings


def _load_proxy_config():
    """Carga proxy desde backend/proxy_dev_config.json."""
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
    host = (proxy.get('host') or '').strip()
    port = proxy.get('port') or 8080
    if not host:
        return None
    return {
        'host': host,
        'port': int(port),
        'username': (proxy.get('username') or '').strip(),
        'password': (proxy.get('password') or '').strip(),
    }


class Command(BaseCommand):
    help = 'Verifica el proxy de proxy_dev_config.json con requests (sin Selenium).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            default='https://ipv4.icanhazip.com',
            help='URL a la que hacer GET a través del proxy (default: icanhazip)',
        )

    def handle(self, *args, **options):
        config = _load_proxy_config()
        if not config:
            self.stdout.write(self.style.ERROR('No se encontró proxy_dev_config.json o proxy vacío.'))
            return

        host, port = config['host'], config['port']
        user, password = config.get('username') or '', config.get('password') or ''
        if user and password:
            # Formato como ResiProx: http://user:pass@host:port
            proxy_url = f"http://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}"
        else:
            proxy_url = f"http://{host}:{port}"

        self.stdout.write(f"Proxy: {host}:{port} (usuario configurado: {'sí' if user else 'no'})")
        self.stdout.write("Probando con requests (igual que ejemplo ResiProx)...")

        try:
            import requests
            target = options['url']
            proxies = {'http': proxy_url, 'https': proxy_url}
            r = requests.get(target, proxies=proxies, timeout=15)
            r.raise_for_status()
            body = (r.text or '').strip()
            self.stdout.write(self.style.SUCCESS(f'OK. IP/respuesta: {body}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            self.stdout.write(
                'Si falla aquí, el proxy no es alcanzable desde este contenedor o las credenciales son incorrectas.'
            )
