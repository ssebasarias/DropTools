"""
Script de prueba para el teléfono 3044235942 que tiene múltiples órdenes
"""
import sys
from pathlib import Path
import pandas as pd

# Agregar el path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar el bot directamente
from core.management.commands.reporter import DropiReporterBot

if __name__ == "__main__":
    # Crear un Excel temporal con solo este teléfono
    excel_test = r"C:\Users\guerr\Desktop\Trazabilidad_TEST_3044235942.xlsx"
    
    # Datos de prueba
    data = {
        'Teléfono': [3044235942],
        'Estado Actual': ['BODEGA DESTINO']  # El estado correcto según la imagen
    }
    
    df = pd.DataFrame(data)
    df.to_excel(excel_test, index=False)
    
    print("="*80)
    print("TEST: TELÉFONO CON MÚLTIPLES ÓRDENES")
    print("="*80)
    print(f"\nTeléfono: 3044235942")
    print(f"Estado esperado: BODEGA DESTINO")
    print(f"\nEste teléfono tiene 5 órdenes en Dropi:")
    print("  1. #61363600 - ENTREGADO")
    print("  2. #62438267 - BODEGA DESTINO ← Esta es la correcta")
    print("  3. #45164565 - ENTREGADO")
    print("  4. #44446645 - ENTREGADO")
    print("  5. #23543733 - ENTREGADO")
    print(f"\nEl bot debe ITERAR por todas y seleccionar la #2")
    print("="*80)
    
    # Crear el bot
    bot = DropiReporterBot(excel_path=excel_test, headless=False)
    
    try:
        # Ejecutar
        bot.run()
        
        print("\n" + "="*80)
        print("TEST COMPLETADO")
        print("="*80)
        
    except KeyboardInterrupt:
        print("\n\nTest interrumpido")
        
    except Exception as e:
        print("\n" + "="*80)
        print("ERROR EN EL TEST")
        print("="*80)
        print(f"\nError: {str(e)}")
        
        import traceback
        traceback.print_exc()
