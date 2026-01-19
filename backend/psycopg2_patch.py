#!/usr/bin/env python
"""
Parche para psycopg2 para manejar encoding SQL_ASCII.
Este archivo debe ser importado ANTES de cualquier conexión a la BD.
"""
import psycopg2
import psycopg2.extensions

# Registrar adaptador para SQL_ASCII que use latin-1 como fallback
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

# Monkey-patch para el método connect
_original_connect = psycopg2.connect

def patched_connect(*args, **kwargs):
    """
    Versión parcheada de psycopg2.connect que maneja SQL_ASCII.
    """
    # Forzar client_encoding a SQL_ASCII para coincidir con el servidor
    kwargs['options'] = kwargs.get('options', '') + ' -c client_encoding=SQL_ASCII'
    try:
        conn = _original_connect(*args, **kwargs)
        return conn
    except UnicodeDecodeError as e:
        # Si falla, intentar con latin1
        print(f"⚠️  Warning: Retrying connection with latin1 encoding workaround", file=sys.stderr)
        kwargs['options'] = kwargs.get('options', '').replace('SQL_ASCII', 'LATIN1')
        return _original_connect(*args, **kwargs)

psycopg2.connect = patched_connect

print("✅ psycopg2 patched for SQL_ASCII compatibility")
