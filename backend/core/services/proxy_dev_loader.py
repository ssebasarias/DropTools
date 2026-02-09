# -*- coding: utf-8 -*-
"""
Carga de proxy desde archivo JSON solo en DEV.
Usado cuando DROPTOOLS_ENV=development y existe proxy_dev_config.json.
No loguea contraseñas.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Ruta: backend/proxy_dev_config.json (BASE_DIR de Django = backend)
def _get_config_path():
    from django.conf import settings
    base = getattr(settings, 'BASE_DIR', Path(__file__).resolve().parent.parent.parent)
    return Path(base) / 'proxy_dev_config.json'


def get_dev_proxy_config(user_id):
    """
    Devuelve la config de proxy para Selenium si existe proxy_dev_config.json
    y el user_id está en user_ids. Solo para desarrollo.

    Returns:
        dict con keys: host, port, username (opcional), password (opcional).
        None si no es DEV, no existe el archivo o el usuario no está en la lista.
    """
    try:
        from django.conf import settings
        if not getattr(settings, 'IS_DEVELOPMENT', False):
            return None
    except Exception:
        return None

    path = _get_config_path()
    if not path.exists():
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.warning("proxy_dev_config.json: error leyendo archivo: %s", e)
        return None

    proxy = data.get('proxy') or {}
    user_ids = data.get('user_ids') or []
    if not isinstance(user_ids, list) or user_id not in user_ids:
        return None

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
