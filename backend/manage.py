#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # if sys.platform == 'win32':
    #    sys.stdout.reconfigure(encoding='utf-8')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'droptools_backend.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    try:
        execute_from_command_line(sys.argv)
    except UnicodeDecodeError as e:
        # PostgreSQL con SQL_ASCII puede devolver mensajes en latin-1
        # Intentamos reconfigurar y reintentar
        print("⚠️  Warning: Unicode decode error detected. Attempting workaround...", file=sys.stderr)
        try:
            # Configurar encoding para manejar SQL_ASCII
            import locale
            locale.setlocale(locale.LC_ALL, 'C')
            # Reintentar con configuración ajustada
            execute_from_command_line(sys.argv)
        except Exception as retry_error:
            print(f"❌ Error after retry: {retry_error}", file=sys.stderr)
            sys.exit(1)
    except Exception:
        import traceback
        sys.stderr.buffer.write(traceback.format_exc().encode('utf-8', 'replace'))
        sys.exit(1)


if __name__ == '__main__':
    main()
