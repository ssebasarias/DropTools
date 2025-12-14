"""
Script de Verificación Completa del Sistema Dahell Intelligence
================================================================

Este script verifica que todos los componentes del sistema estén
funcionando correctamente y puedan comunicarse entre sí.

Uso:
    .\activate_env.bat
    python utils/verificar_sistema.py
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar config_encoding
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar configuración UTF-8
from config_encoding import setup_utf8
setup_utf8()

import psycopg2
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

# ============================================================================
# VERIFICACIÓN 1: Variables de Entorno
# ============================================================================

def verificar_variables_entorno():
    print_header("VERIFICACIÓN 1: Variables de Entorno")
    
    variables = {
        'POSTGRES_DB': os.getenv('POSTGRES_DB'),
        'POSTGRES_USER': os.getenv('POSTGRES_USER'),
        'POSTGRES_PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'POSTGRES_HOST': os.getenv('POSTGRES_HOST'),
        'POSTGRES_PORT': os.getenv('POSTGRES_PORT'),
        'DROPI_EMAIL': os.getenv('DROPI_EMAIL'),
        'DROPI_PASSWORD': os.getenv('DROPI_PASSWORD'),
    }
    
    todas_ok = True
    for var, valor in variables.items():
        if valor:
            # No mostrar contraseñas completas
            if 'PASSWORD' in var:
                print_success(f"{var}: {'*' * len(valor)}")
            else:
                print_success(f"{var}: {valor}")
        else:
            print_error(f"{var}: NO CONFIGURADA")
            todas_ok = False
    
    return todas_ok

# ============================================================================
# VERIFICACIÓN 2: Conexión a Base de Datos
# ============================================================================

def verificar_conexion_db():
    print_header("VERIFICACIÓN 2: Conexión a Base de Datos")
    
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('POSTGRES_DB', 'dahell_db'),
            user=os.getenv('POSTGRES_USER', 'dahell_admin'),
            password=os.getenv('POSTGRES_PASSWORD', 'secure_password_123'),
            host=os.getenv('POSTGRES_HOST', '127.0.0.1'),
            port=os.getenv('POSTGRES_PORT', '5433'),
            options='-c client_encoding=UTF8'
        )
        
        cur = conn.cursor()
        
        # Verificar versión de PostgreSQL
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print_success(f"Conexión exitosa a PostgreSQL")
        print_info(f"Versión: {version.split(',')[0]}")
        
        # Verificar extensión pgvector
        cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        if cur.fetchone():
            print_success("Extensión pgvector instalada")
        else:
            print_error("Extensión pgvector NO instalada")
            return False
        
        # Verificar encoding
        cur.execute("SHOW client_encoding;")
        encoding = cur.fetchone()[0]
        if encoding == 'UTF8':
            print_success(f"Encoding: {encoding}")
        else:
            print_warning(f"Encoding: {encoding} (esperado: UTF8)")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print_error(f"Error de conexión: {e}")
        return False

# ============================================================================
# VERIFICACIÓN 3: Tablas de la Base de Datos
# ============================================================================

def verificar_tablas():
    print_header("VERIFICACIÓN 3: Tablas de la Base de Datos")
    
    tablas_esperadas = [
        'warehouses',
        'suppliers',
        'categories',
        'products',
        'product_categories',
        'product_stock_log',
        'product_embeddings',
        'unique_product_clusters',
        'product_cluster_membership'
    ]
    
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('POSTGRES_DB', 'dahell_db'),
            user=os.getenv('POSTGRES_USER', 'dahell_admin'),
            password=os.getenv('POSTGRES_PASSWORD', 'secure_password_123'),
            host=os.getenv('POSTGRES_HOST', '127.0.0.1'),
            port=os.getenv('POSTGRES_PORT', '5433'),
            options='-c client_encoding=UTF8'
        )
        
        cur = conn.cursor()
        
        # Obtener lista de tablas
        cur.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        
        tablas_existentes = [row[0] for row in cur.fetchall()]
        
        todas_ok = True
        for tabla in tablas_esperadas:
            if tabla in tablas_existentes:
                # Contar registros
                cur.execute(f"SELECT COUNT(*) FROM {tabla};")
                count = cur.fetchone()[0]
                print_success(f"{tabla}: {count:,} registros")
            else:
                print_error(f"{tabla}: NO EXISTE")
                todas_ok = False
        
        cur.close()
        conn.close()
        return todas_ok
        
    except Exception as e:
        print_error(f"Error verificando tablas: {e}")
        return False

# ============================================================================
# VERIFICACIÓN 4: Archivos de Datos
# ============================================================================

def verificar_archivos_datos():
    print_header("VERIFICACIÓN 4: Archivos de Datos")
    
    raw_data_dir = Path('raw_data')
    
    if not raw_data_dir.exists():
        print_warning("Carpeta raw_data/ no existe")
        return False
    
    jsonl_files = list(raw_data_dir.glob('*.jsonl'))
    
    if not jsonl_files:
        print_warning("No hay archivos .jsonl en raw_data/")
        print_info("Ejecuta el scraper para generar datos")
        return True  # No es un error crítico
    
    total_size = 0
    for file in jsonl_files:
        size_mb = file.stat().st_size / (1024 * 1024)
        total_size += size_mb
        print_success(f"{file.name}: {size_mb:.2f} MB")
    
    print_info(f"Total: {len(jsonl_files)} archivos, {total_size:.2f} MB")
    return True

# ============================================================================
# VERIFICACIÓN 5: Encoding UTF-8
# ============================================================================

def verificar_encoding():
    print_header("VERIFICACIÓN 5: Encoding UTF-8")
    
    # Verificar encoding de Python
    import sys
    stdout_encoding = sys.stdout.encoding
    
    if stdout_encoding.lower() == 'utf-8':
        print_success(f"Python stdout: {stdout_encoding}")
    else:
        print_warning(f"Python stdout: {stdout_encoding} (esperado: utf-8)")
    
    # Verificar variables de entorno
    pythonioencoding = os.getenv('PYTHONIOENCODING')
    pythonutf8 = os.getenv('PYTHONUTF8')
    
    if pythonioencoding == 'utf-8':
        print_success(f"PYTHONIOENCODING: {pythonioencoding}")
    else:
        print_warning(f"PYTHONIOENCODING: {pythonioencoding or 'NO CONFIGURADA'}")
    
    if pythonutf8 == '1':
        print_success(f"PYTHONUTF8: {pythonutf8}")
    else:
        print_warning(f"PYTHONUTF8: {pythonutf8 or 'NO CONFIGURADA'}")
    
    return True

# ============================================================================
# VERIFICACIÓN 6: Comandos de Django
# ============================================================================

def verificar_comandos_django():
    print_header("VERIFICACIÓN 6: Comandos de Django")
    
    commands_dir = Path('backend/core/management/commands')
    
    comandos_esperados = [
        'scraper.py',
        'loader.py',
        'vectorizer.py',
        'clusterizer.py',
        'diagnose_stats.py'
    ]
    
    todas_ok = True
    for comando in comandos_esperados:
        comando_path = commands_dir / comando
        if comando_path.exists():
            size_kb = comando_path.stat().st_size / 1024
            print_success(f"{comando}: {size_kb:.1f} KB")
        else:
            print_error(f"{comando}: NO EXISTE")
            todas_ok = False
    
    return todas_ok

# ============================================================================
# VERIFICACIÓN 7: Dependencias Python
# ============================================================================

def verificar_dependencias():
    print_header("VERIFICACIÓN 7: Dependencias Python")
    
    dependencias_criticas = [
        'django',
        'psycopg2',
        'selenium',
        'torch',
        'transformers',
        'sqlalchemy',
        'requests',
        'pillow',
        'numpy',
        'pandas'
    ]
    
    todas_ok = True
    for dep in dependencias_criticas:
        try:
            __import__(dep)
            print_success(f"{dep}: Instalado")
        except ImportError:
            print_error(f"{dep}: NO INSTALADO")
            todas_ok = False
    
    return todas_ok

# ============================================================================
# RESUMEN FINAL
# ============================================================================

def resumen_final(resultados):
    print_header("RESUMEN FINAL")
    
    total = len(resultados)
    exitosos = sum(resultados.values())
    
    print(f"\nVerificaciones completadas: {exitosos}/{total}")
    
    if exitosos == total:
        print_success("\n🎉 ¡TODOS LOS COMPONENTES ESTÁN FUNCIONANDO CORRECTAMENTE!")
        print_info("\nPuedes ejecutar las 4 terminales:")
        print_info("  Terminal 1: python backend/manage.py scraper")
        print_info("  Terminal 2: python backend/manage.py loader")
        print_info("  Terminal 3: python backend/manage.py vectorizer")
        print_info("  Terminal 4: python backend/manage.py clusterizer")
        return True
    else:
        print_error("\n⚠️  ALGUNOS COMPONENTES TIENEN PROBLEMAS")
        print_info("\nRevisa los errores arriba y:")
        print_info("  1. Verifica que Docker está corriendo")
        print_info("  2. Verifica el archivo .env")
        print_info("  3. Instala dependencias faltantes: pip install -r requirements.txt")
        return False

# ============================================================================
# MAIN
# ============================================================================

def main():
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{'VERIFICACIÓN COMPLETA DEL SISTEMA'.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{'Dahell Intelligence v2.0'.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")
    
    resultados = {
        'Variables de Entorno': verificar_variables_entorno(),
        'Conexión a DB': verificar_conexion_db(),
        'Tablas': verificar_tablas(),
        'Archivos de Datos': verificar_archivos_datos(),
        'Encoding UTF-8': verificar_encoding(),
        'Comandos Django': verificar_comandos_django(),
        'Dependencias': verificar_dependencias()
    }
    
    return resumen_final(resultados)

if __name__ == '__main__':
    try:
        exito = main()
        sys.exit(0 if exito else 1)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Verificación interrumpida por el usuario{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Error inesperado: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
