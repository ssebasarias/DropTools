"""
Script de prueba para el bot de reportes Dropi
Este script te ayuda a probar el bot con un conjunto pequeño de datos
"""

import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from core.management.commands.reporter import DropiReporterBot


def test_bot_with_sample_data():
    """
    Prueba el bot con datos de ejemplo
    """
    
    # Ruta al archivo Excel
    # CAMBIA ESTA RUTA A LA UBICACIÓN DE TU ARCHIVO
    excel_path = r"C:\Users\guerr\Desktop\Trazabilidad_same_2026-01-16.xlsx"
    
    # Verificar que el archivo existe
    if not os.path.exists(excel_path):
        print(f"❌ Error: El archivo no existe: {excel_path}")
        print("\n📝 Por favor, actualiza la variable 'excel_path' con la ruta correcta.")
        return
    
    print("="*80)
    print("🤖 PRUEBA DEL BOT DE REPORTES DROPI")
    print("="*80)
    print(f"\n📁 Archivo Excel: {excel_path}")
    
    # Preguntar si quiere ejecutar en modo headless
    print("\n¿Deseas ejecutar el bot en modo headless (sin ver el navegador)?")
    print("1. No - Ver el navegador (recomendado para primera vez)")
    print("2. Sí - Modo headless")
    
    choice = input("\nSelecciona una opción (1 o 2): ").strip()
    headless = choice == "2"
    
    if headless:
        print("\n🔇 Ejecutando en modo headless...")
    else:
        print("\n👀 Ejecutando con navegador visible...")
    
    # Crear el bot
    print("\n🚀 Iniciando bot...")
    bot = DropiReporterBot(excel_path=excel_path, headless=headless)
    
    try:
        # Ejecutar
        bot.run()
        
        print("\n" + "="*80)
        print("✅ BOT EJECUTADO EXITOSAMENTE")
        print("="*80)
        print("\n📊 Revisa los resultados en:")
        print(f"   - Logs: backend/logs/")
        print(f"   - Resultados: backend/results/")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Ejecución interrumpida por el usuario")
        
    except Exception as e:
        print("\n" + "="*80)
        print("❌ ERROR AL EJECUTAR EL BOT")
        print("="*80)
        print(f"\nError: {str(e)}")
        print("\n💡 Sugerencias:")
        print("   1. Verifica que las credenciales sean correctas")
        print("   2. Asegúrate de tener Chrome instalado")
        print("   3. Revisa el archivo de log para más detalles")
        print("   4. Intenta ejecutar sin modo headless para ver qué pasa")
        
        import traceback
        print("\n📋 Detalles técnicos:")
        traceback.print_exc()


if __name__ == "__main__":
    test_bot_with_sample_data()
