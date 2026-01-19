"""
Script para crear un Excel de prueba con solo 5 ordenes
"""
import pandas as pd
from pathlib import Path

# Leer el Excel completo
excel_path = r"C:\Users\guerr\Desktop\Trazabilidad_same_2026-01-16.xlsx"
output_path = r"C:\Users\guerr\Desktop\Trazabilidad_TEST_5.xlsx"

print("Leyendo Excel completo...")
df = pd.read_excel(excel_path)

print(f"   Total de registros: {len(df)}")

# Estados validos
VALID_STATES = [
    "BODEGA DESTNO",
    "DESPACHADA",
    "EN BODEGA ORIGEN",
    "EN BODEGA TRANSPORTADORA",
    "EN DESPACHO",
    "EN CAMINO",
    "EN PROCESAMIENTO",
    "EN PROCESO DE DEVOLUCION",
    "EN REPARTO",
    "EN RUTA",
    "ENTREGADO A CONEXIONES",
    "ENTREGADO A TRANSPORTADORA",
    "INTENTO DE ENTREGA",
    "NOVEDAD SOLUCIONADA",
    "ENTREGA POR DROPI",
    "TELEMERCADEO"
]

# Filtrar por estados validos
df_filtered = df[df['Estado Actual'].isin(VALID_STATES)]
print(f"   Registros con estados validos: {len(df_filtered)}")

# Tomar los primeros 10
df_test = df_filtered.head(10)

print(f"\nPrimeros 10 registros para prueba:")
print("="*80)
for idx, row in df_test.iterrows():
    print(f"{idx+1}. Telefono: {row['Teléfono']} | Estado: {row['Estado Actual']}")
print("="*80)

# Guardar Excel de prueba
output_path = r"C:\Users\guerr\Desktop\Trazabilidad_TEST_10.xlsx"
df_test.to_excel(output_path, index=False)
print(f"\nExcel de prueba creado: {output_path}")
print(f"   Contiene {len(df_test)} ordenes")
