
import pandas as pd
import os
import sys

# Redirigir stdout a un archivo
sys.stdout = open('excel_analysis_output.txt', 'w', encoding='utf-8')

file_path = r"c:\Users\guerr\Documents\AnalisisDeDatos\Dahell\backend\results\downloads\enero_2026\reporte_20260123.xlsx"

try:
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        exit(1)

    print(f"Reading file: {file_path}")
    df = pd.read_excel(file_path)
    
    print("\n--- Columns, Types, and Sample Data ---")
    print(f"{'Column Name':<40} | {'Type':<10} | {'Sample Value'}")
    print("-" * 80)
    
    for col in df.columns:
        dtype = str(df[col].dtype)
        # Handle nan
        if df[col].empty:
             sample = "Empty"
        else:
             val = df[col].iloc[0]
             sample = str(val)
        
        # Truncate long samples
        if len(sample) > 30:
            sample = sample[:27] + "..."
        print(f"{col:<40} | {dtype:<10} | {sample}")

    print("\n--- Total Rows ---")
    print(len(df))

except Exception as e:
    print(f"Error reading excel: {e}")
