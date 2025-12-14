"""
Configuración global de encoding para el proyecto Dahell Intelligence.

Este archivo debe ser importado al inicio de cada script para garantizar
que todo el sistema use UTF-8 de manera consistente.

Uso:
    import sys
    import os
    
    # Importar al inicio de cada script
    from config_encoding import setup_utf8
    setup_utf8()
"""

import sys
import os
import locale


def setup_utf8():
    """
    Configura el sistema para usar UTF-8 en todas las operaciones de I/O.
    
    Esta función debe llamarse al inicio de cada script para garantizar
    consistencia en el manejo de caracteres especiales (tildes, ñ, etc.).
    """
    
    # 1. Configurar encoding por defecto de Python
    if sys.version_info >= (3, 7):
        # Python 3.7+ usa UTF-8 por defecto en la mayoría de casos
        pass
    
    # 2. Forzar UTF-8 en stdout/stderr (para prints y logs)
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')
    
    # 3. Variables de entorno para forzar UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    
    # 4. Configurar locale (solo si es necesario)
    try:
        locale.setlocale(locale.LC_ALL, 'es_CO.UTF-8')  # Colombia
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')  # Fallback
        except locale.Error:
            pass  # Ignorar si no se puede configurar
    
    # 5. Configurar encoding para PostgreSQL (psycopg2)
    os.environ['PGCLIENTENCODING'] = 'UTF8'
    
    print("✅ Encoding configurado: UTF-8 en todo el sistema")


def get_db_connection_args():
    """
    Retorna los argumentos de conexión estándar para PostgreSQL.
    
    Returns:
        dict: Diccionario con opciones de conexión que fuerzan UTF-8
    """
    return {
        'options': '-c client_encoding=UTF8',
        'client_encoding': 'UTF8'
    }


# Configuración automática al importar este módulo
# (Comentar esta línea si prefieres llamar setup_utf8() manualmente)
setup_utf8()
