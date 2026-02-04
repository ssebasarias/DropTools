"""
Test local: login a Dropi con proxy en modo visible (usuario 2).

Usa la misma configuración de proxy que el resto de la app (proxy_dev_config.json
o variables de entorno). Solo abre el navegador, pone correo/contraseña e ingresa,
para verificar que la configuración proxy funciona.

Con proxy: espera más a que la extensión cargue, hace un warm-up en una página
ligera (icanhazip) y luego va directo a la página de login de Dropi (sin landing).
"""
import os
import time
from django.core.management.base import BaseCommand
from core.reporter_bot.driver_manager import DriverManager
from core.reporter_bot.auth_manager import AuthManager
from core.reporter_bot.utils import setup_logger


def get_proxy_config_for_user(user_id, logger=None):
    """Misma lógica global que unified_reporter / novedadreporter."""
    from core.services.proxy_dev_loader import get_dev_proxy_config

    if os.environ.get("DROPI_NO_PROXY", "").strip().lower() in ("1", "true", "yes"):
        if logger:
            logger.info("   🌐 Sin proxy (DROPI_NO_PROXY=1)")
        return None

    config = get_dev_proxy_config(user_id)
    if config:
        if logger:
            logger.info(f"🌐 Proxy (dev): {config.get('host')}:{config.get('port')}")
        return config

    host = os.environ.get("DROPI_PROXY_HOST") or "gw.dataimpulse.com"
    port = int(os.environ.get("DROPI_PROXY_PORT", "823"))
    username = os.environ.get("DROPI_PROXY_USER") or "2b3a0e0b5c2e4_country-co_session-1"
    password = os.environ.get("DROPI_PROXY_PASS") or "bigotes2001"
    config = {"host": host, "port": port, "username": username, "password": password}
    if logger:
        logger.info(f"🌐 Proxy: {host}:{port}")
    return config


class Command(BaseCommand):
    help = 'Test local: login a Dropi con proxy en modo visible (usuario 2). Solo correo, contraseña e ingresar.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=int,
            default=2,
            help='ID del usuario (default: 2)',
        )
        parser.add_argument(
            '--no-proxy',
            action='store_true',
            help='Ejecutar sin proxy (DROPI_NO_PROXY=1)',
        )
        parser.add_argument(
            '--stay',
            type=int,
            default=30,
            help='Segundos que el navegador permanece abierto tras login (default: 30)',
        )
        parser.add_argument(
            '--landing',
            action='store_true',
            help='Usar landing Dropi + Colombia (por defecto va directo a login)',
        )

    def handle(self, *args, **options):
        user_id = options['user']
        no_proxy = options['no_proxy']
        stay_seconds = options['stay']
        use_landing = options['landing']
        logger = setup_logger('TestProxyLogin')

        if no_proxy:
            os.environ["DROPI_NO_PROXY"] = "1"
        else:
            # Ir directo a app.dropi.co/auth/login (evita landing que da ERR_TOO_MANY_RETRIES con proxy)
            os.environ["DROPI_LOGIN_DIRECT"] = "1" if not use_landing else "0"

        self.stdout.write("=" * 60)
        self.stdout.write("🧪 TEST: Login a Dropi con proxy (modo visible)")
        self.stdout.write("=" * 60)
        self.stdout.write(f"   Usuario ID: {user_id}")
        self.stdout.write(f"   Proxy: {'no' if no_proxy else 'sí (config global)'}")
        self.stdout.write(f"   Login: {'landing + Colombia' if use_landing else 'directo a app.dropi.co/login (como novedadreporter)'}")
        self.stdout.write("=" * 60)

        proxy_config = get_proxy_config_for_user(user_id, logger)
        if not proxy_config and not no_proxy:
            logger.warning("No hay configuración de proxy para este usuario (revisa proxy_dev_config.json o env).")

        DriverManager.reset_singleton()
        dm = DriverManager(
            headless=False,
            logger=logger,
            download_dir=None,
            browser='edge',
            proxy_config=proxy_config,
        )
        try:
            driver = dm.init_driver(browser_priority=['edge', 'chrome', 'firefox'])
            if not driver:
                self.stdout.write(self.style.ERROR("No se pudo iniciar el navegador."))
                return

            if proxy_config:
                logger.info("   ⏳ Esperando 8s para que la extensión del proxy esté lista...")
                time.sleep(8)

            auth = AuthManager(driver=driver, user_id=user_id, logger=logger)
            auth.load_credentials()

            logger.info("🔐 Iniciando login (correo + contraseña + ingresar)...")
            if not auth.login():
                self.stdout.write(self.style.ERROR("Login fallido. Revisa logs y/o captura en results/screenshots."))
                return

            self.stdout.write(self.style.SUCCESS("✅ Login correcto. Navegador en Dropi."))
            self.stdout.write(f"   Dejando navegador abierto {stay_seconds}s para que puedas ver...")
            time.sleep(stay_seconds)
        finally:
            dm.close()

        self.stdout.write("Test finalizado.")
