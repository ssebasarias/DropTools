import os
import sys
import locale
import traceback

print('=== ENV ===')
for k in ['PGCLIENTENCODING','LANG','LC_ALL','PYTHONIOENCODING','PYTHONUTF8']:
    print(k, os.environ.get(k))
print('cwd:', os.getcwd())
print('sys.executable:', sys.executable)
print('defaultencoding:', sys.getdefaultencoding())
print('filesystemencoding:', sys.getfilesystemencoding())
print('locale:', locale.getpreferredencoding())

try:
    import psycopg2
    print('psycopg2 imported, version:', getattr(psycopg2, '__version__', 'n/a'))
    try:
        print('libpq_version:', psycopg2.extensions.libpq_version())
    except Exception as e:
        print('libpq_version not available:', e)
except Exception as e:
    print('Failed to import psycopg2:', e)

# DB params (from settings defaults)
DB_NAME = os.environ.get('POSTGRES_DB','dahell_db')
DB_USER = os.environ.get('POSTGRES_USER','dahell_admin')
DB_PASS = os.environ.get('POSTGRES_PASSWORD','secure_password_123')
DB_HOST = os.environ.get('POSTGRES_HOST','127.0.0.1')
DB_PORT = os.environ.get('POSTGRES_PORT','5433')

print('\n=== Connection params (repr) ===')
print(repr((DB_HOST, DB_PORT, DB_NAME, DB_USER)))

attempts = []

def try_connect(dsn=None, kwargs=None, desc=''):
    print('\n--- Try:', desc)
    try:
        if dsn:
            print('DSN repr:', repr(dsn))
            conn = psycopg2.connect(dsn)
        else:
            print('kwargs repr:', repr(kwargs))
            conn = psycopg2.connect(**kwargs)
        cur = conn.cursor()
        cur.execute("SHOW server_encoding;")
        print('server_encoding:', cur.fetchone())
        cur.close()
        conn.close()
        print('Connected OK')
    except Exception as e:
        print('ERROR:', type(e), e)
        traceback.print_exc()

# Plain connect
try_connect(kwargs={'host':DB_HOST,'port':DB_PORT,'dbname':DB_NAME,'user':DB_USER,'password':DB_PASS}, desc='plain')

# DSN with client_encoding
dsn = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASS} client_encoding=LATIN1"
try_connect(dsn=dsn, desc='dsn client_encoding=LATIN1')

# options param
try_connect(kwargs={'host':DB_HOST,'port':DB_PORT,'dbname':DB_NAME,'user':DB_USER,'password':DB_PASS,'options':'-c client_encoding=LATIN1'}, desc='options -c client_encoding')

print('\nDone')
