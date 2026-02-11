import os
import sys
import django
from datetime import datetime, time as dt_time, timedelta
from django.utils import timezone

# Configuración de Django
sys.path.insert(0, r'C:\Users\guerr\OneDrive\Documentos\Dahell\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'droptools_backend.settings')
django.setup()

from core.models import User, OrderReport

def run_test():
    print("\n" + "="*80)
    print("VERIFICACIÓN DE KPIs - USUARIO 2")
    print("="*80)

    try:
        user = User.objects.get(id=2)
        print(f"✅ Usuario encontrado: {user.username} (ID: {user.id})")
    except User.DoesNotExist:
        print("❌ Error: Usuario con ID 2 no existe.")
        return

    # 1. Verificar estado actual
    now = timezone.localtime(timezone.now())
    today_start = timezone.make_aware(datetime.combine(now.date(), dt_time.min))
    today_end = today_start + timedelta(days=1)
    
    current_count = OrderReport.objects.filter(
        user=user, 
        status='reportado', 
        updated_at__gte=today_start, 
        updated_at__lt=today_end
    ).count()
    
    print(f"📊 Reportados HOY (antes de insertar): {current_count}")

    # 2. Insertar reporte de prueba
    test_phone = "3001234567"
    print(f"\n📝 Insertando reporte de prueba para {test_phone}...")
    
    obj, created = OrderReport.objects.update_or_create(
        user=user,
        order_phone=test_phone,
        defaults={
            'status': 'reportado',
            'report_generated': True,
            'customer_name': 'Test User',
            'product_name': 'Test Product',
            'updated_at': now  # Forzar update time
        }
    )
    # Forzar save para asegurar updated_at si no se actualizó
    obj.updated_at = now
    obj.save()
    
    print(f"✅ Reporte guardado. ID: {obj.id} | Status: {obj.status} | Updated: {obj.updated_at}")

    # 3. Verificar nuevamente
    new_count = OrderReport.objects.filter(
        user=user, 
        status='reportado', 
        updated_at__gte=today_start, 
        updated_at__lt=today_end
    ).count()
    
    print(f"📊 Reportados HOY (después de insertar): {new_count}")
    
    if new_count > current_count:
        print("\n✅ ÉXITO: El contador incrementó. La lógica de base de datos funciona.")
        print("👉 Si el frontend sigue mostrando 0, el problema está en la conexión Frontend-Backend o el usuario logueado.")
    else:
        print("\n❌ ERROR: El contador NO incrementó. Revisa los filtros de fecha/timezone.")
        print(f"   Debug: Today Start: {today_start}")
        print(f"   Debug: Report Updated: {obj.updated_at}")

if __name__ == "__main__":
    run_test()
