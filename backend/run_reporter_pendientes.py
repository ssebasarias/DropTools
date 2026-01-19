"""
Script para ejecutar el bot SOLO con las órdenes que NO fueron procesadas anteriormente
"""
import sys
from pathlib import Path
import pandas as pd

# Agregar el path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar el bot directamente
from core.management.commands.reporter import DropiReporterBot

if __name__ == "__main__":
    # Rutas
    excel_completo = r"C:\Users\guerr\Desktop\Trazabilidad_same_2026-01-17.xlsx"
    resultados_anteriores = r"C:\Users\guerr\Documents\AnalisisDeDatos\Dahell\backend\results\dropi_reporter_results_20260116_182459.csv"
    excel_pendientes = r"C:\Users\guerr\Desktop\Trazabilidad_PENDIENTES.xlsx"
    
    print("="*80)
    print("CREANDO EXCEL CON ÓRDENES PENDIENTES")
    print("="*80)
    
    # Leer el Excel completo
    print(f"\n1. Leyendo Excel completo...")
    df_completo = pd.read_excel(excel_completo)
    print(f"   Total de registros: {len(df_completo)}")
    
    # Leer los resultados anteriores
    print(f"\n2. Leyendo resultados anteriores...")
    df_procesados = pd.read_csv(resultados_anteriores)
    telefonos_procesados = set(df_procesados['phone'].astype(str))
    print(f"   Teléfonos ya procesados: {len(telefonos_procesados)}")
    
    # Filtrar solo los que NO fueron procesados
    print(f"\n3. Filtrando órdenes pendientes...")
    df_completo['Teléfono_str'] = df_completo['Teléfono'].astype(str)
    df_pendientes = df_completo[~df_completo['Teléfono_str'].isin(telefonos_procesados)]
    print(f"   Órdenes pendientes: {len(df_pendientes)}")
    
    # Estados válidos (actualizados)
    estados_validos = [
        "BODEGA DESTINO",
        "DESPACHADA",
        "EN BODEGA TRANSPORTADORA",
        "EN CAMINO",
        "EN DESPACHO",
        "EN PROCESAMIENTO",
        "EN PROCESO DE DEVOLUCION",
        "EN REPARTO",
        "EN RUTA",
        "ENTREGADA A CONEXIONES",
        "ENTREGADO A TRANSPORTADORA",
        "NOVEDAD SOLUCIONADA",
        "RECOGIDO POR DROPI",
        "TELEMERCADEO"
    ]
    
    # Filtrar por estados válidos
    df_pendientes_validos = df_pendientes[df_pendientes['Estado Actual'].isin(estados_validos)]
    print(f"   Con estados válidos: {len(df_pendientes_validos)}")
    
    # Eliminar duplicados
    df_pendientes_unicos = df_pendientes_validos.drop_duplicates(subset=['Teléfono'])
    print(f"   Únicos (sin duplicados): {len(df_pendientes_unicos)}")
    
    # Guardar Excel de pendientes
    df_pendientes_unicos.to_excel(excel_pendientes, index=False)
    print(f"\n✅ Excel de pendientes creado: {excel_pendientes}")
    
    print("\n" + "="*80)
    print("EJECUTANDO BOT CON ÓRDENES PENDIENTES")
    print("="*80)
    print(f"\nArchivo Excel: {excel_pendientes}")
    print(f"Órdenes a procesar: {len(df_pendientes_unicos)}")
    print("Modo: NAVEGADOR VISIBLE (podras ver Chrome trabajando)")
    print("\n⚠️  IMPORTANTE:")
    print("   - El bot procesará SOLO las órdenes que NO fueron procesadas antes")
    print("   - Detectará automáticamente las que ya tienen caso")
    print("   - Creará reportes para las nuevas")
    print("   - Puedes detenerlo en cualquier momento con Ctrl+C")
    print("\nPresiona Ctrl+C en cualquier momento para detener el bot")
    print("="*80)
    
    # Crear el bot con el Excel de pendientes
    bot = DropiReporterBot(excel_path=excel_pendientes, headless=False)
    
    try:
        # Ejecutar
        bot.run()
        
        print("\n" + "="*80)
        print("BOT EJECUTADO EXITOSAMENTE")
        print("="*80)
        print("\n📊 Revisa los resultados en:")
        print(f"   - Logs: backend/logs/")
        print(f"   - Resultados: backend/results/")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Ejecución interrumpida por el usuario")
        print("Los resultados parciales se guardaron en backend/results/")
        
    except Exception as e:
        print("\n" + "="*80)
        print("ERROR AL EJECUTAR EL BOT")
        print("="*80)
        print(f"\nError: {str(e)}")
        
        import traceback
        print("\nDetalles tecnicos:")
        traceback.print_exc()
