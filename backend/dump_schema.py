#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Genera una copia del esquema de la base de datos.
- Si existe docs/droptools_db.sql (dump previo), lo copia como esquema de referencia.
- Uso: python dump_schema.py [ruta_salida]
"""
import os
import sys
import shutil
from datetime import datetime

def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs = os.path.join(base, 'docs')

    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not out_path:
        out_path = os.path.join(docs, 'database_schema_backup.sql')

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Preferir dump existente del proyecto
    source = os.path.join(docs, 'droptools_db.sql')
    if os.path.isfile(source):
        with open(source, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        # Escribir solo el esquema (opcional: podríamos filtrar solo CREATE)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write("-- DropTools - Copia del esquema de la base de datos\n")
            f.write(f"-- Generado: {datetime.now().isoformat()}\n")
            f.write("-- Origen: docs/droptools_db.sql\n\n")
            f.write(content)
        print(f"Copia del esquema escrita en: {out_path}")
        return 0

    # Si no hay dump, crear placeholder con instrucciones
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("-- DropTools - Esquema de base de datos\n")
        f.write(f"-- Generado: {datetime.now().isoformat()}\n")
        f.write("-- Para generar un dump completo del esquema:\n")
        f.write("--   Docker: docker compose exec db pg_dump -U droptools_admin -d droptools_db --schema-only --no-owner -f /tmp/schema.sql\n")
        f.write("--   Local:  pg_dump -h localhost -U droptools_admin -d droptools_db --schema-only --no-owner -f docs/droptools_db_schema.sql\n")
        f.write("-- Extensiones requeridas: CREATE EXTENSION pg_trgm; CREATE EXTENSION unaccent; CREATE EXTENSION vector;\n")
    print(f"Placeholder escrito en: {out_path} (no existía docs/droptools_db.sql)")
    return 0

if __name__ == '__main__':
    sys.exit(main())
