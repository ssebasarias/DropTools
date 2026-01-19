"""
Script directo para ejecutar el bot de reportes sin Django
"""
import sys
from pathlib import Path

# Agregar el path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar el bot directamente
from core.management.commands.reporter import DropiReporterBot

if __name__ == "__main__":
    # Ruta al Excel de prueba
    excel_path = r"C:\Users\guerr\Desktop\Trazabilidad_TEST_10.xlsx"
    
    print("="*80)
    print("EJECUTANDO BOT DE REPORTES DROPI - PRUEBA CON 10 ORDENES")
    print("="*80)
    print(f"\nArchivo Excel: {excel_path}")
    print("Modo: NAVEGADOR VISIBLE (podras ver Chrome trabajando)")
    print("\nPresiona Ctrl+C en cualquier momento para detener el bot")
    print("="*80)
    
    # Crear el bot (headless=False para ver el navegador)
    bot = DropiReporterBot(excel_path=excel_path, headless=False)
    
    try:
        # Ejecutar
        bot.run()
        
        print("\n" + "="*80)
        print("BOT EJECUTADO EXITOSAMENTE")
        print("="*80)
        
    except KeyboardInterrupt:
        print("\n\nEjecucion interrumpida por el usuario")
        
    except Exception as e:
        print("\n" + "="*80)
        print("ERROR AL EJECUTAR EL BOT")
        print("="*80)
        print(f"\nError: {str(e)}")
        
        import traceback
        print("\nDetalles tecnicos:")
        traceback.print_exc()
