#!/usr/bin/env python
"""
Verificación directa de conexión a PostgreSQL sin Django.
"""
import psycopg2

try:
    # Intentar conexión directa
    print("Intentando conectar a PostgreSQL...")
    
    conn = psycopg2.connect(
        host='127.0.0.1',
        port=5433,
        database='dahell_db',
        user='dahell_admin',
        password='secure_password_123',
        options='-c client_encoding=LATIN1'
    )
    
    print("✅ Conexión exitosa!")
    
    # Crear cursor
    cur = conn.cursor()
    
    # Consulta simple
    cur.execute("SELECT COUNT(*) FROM domain_reputation;")
    count = cur.fetchone()[0]
    print(f"✅ DomainReputation count: {count}")
    
    cur.execute("SELECT COUNT(*) FROM market_analysis_reports;")
    count = cur.fetchone()[0]
    print(f"✅ MarketAnalysisReport count: {count}")
    
    # Cerrar
    cur.close()
    conn.close()
    
    print("\n✅ Verificación completada exitosamente!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
