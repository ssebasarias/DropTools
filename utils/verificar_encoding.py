"""
Script para verificar el encoding de archivos JSONL existentes
"""
import json
import pathlib

raw_dir = pathlib.Path('raw_data')
jsonl_files = list(raw_dir.glob('*.jsonl'))

print(f"Archivos JSONL encontrados: {len(jsonl_files)}\n")

for jsonl_file in jsonl_files:
    print(f"Verificando: {jsonl_file.name}")
    
    # Intentar leer con UTF-8
    try:
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            line = f.readline()
            data = json.loads(line)
            titulo = data.get('name', 'N/A')[:100]
            print(f"  ✅ UTF-8 OK: {titulo}")
    except UnicodeDecodeError as e:
        print(f"  ❌ UTF-8 FALLA: {e}")
        
        # Intentar con latin-1
        try:
            with open(jsonl_file, 'r', encoding='latin-1') as f:
                line = f.readline()
                data = json.loads(line)
                titulo = data.get('name', 'N/A')[:100]
                print(f"  ⚠️ latin-1 funciona: {titulo}")
        except Exception as e2:
            print(f"  ❌ latin-1 también falla: {e2}")
    
    print()
