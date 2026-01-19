"""
Script para ejecutar el bot de reportes con el Excel COMPLETO
"""
import sys
from pathlib import Path

# Agregar el path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar el bot directamente
from core.management.commands.reporter import DropiReporterBot

if __name__ == "__main__":
    # Ruta al Excel COMPLETO
    excel_path = r"C:\Users\guerr\Desktop\Trazabilidad_same_2026-01-17.xlsx"
    
    print("="*80)
    print("EJECUTANDO BOT DE REPORTES DROPI - EXCEL COMPLETO")
    print("="*80)
    print(f"\nArchivo Excel: {excel_path}")
    print("Modo: NAVEGADOR VISIBLE (podras ver Chrome trabajando)")
    print("\n⚠️  IMPORTANTE:")
    print("   - El bot procesará TODAS las órdenes con estados válidos")
    print("   - Detectará automáticamente las que ya tienen caso")
    print("   - Creará reportes para las nuevas")
    print("   - Puedes detenerlo en cualquier momento con Ctrl+C")
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
