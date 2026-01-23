"""
Script de verificación para comprobar las cuentas Dropi del usuario alexcander
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dahell_backend.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import DropiAccount

# Buscar usuario alexcander
user = User.objects.filter(username='alexcander').first()

if not user:
    print("❌ Usuario 'alexcander' no encontrado")
    sys.exit(1)

print(f"✅ Usuario encontrado: {user.username} (ID: {user.id}, Email: {user.email})")
print()

# Buscar cuentas Dropi del usuario
accounts = DropiAccount.objects.filter(user=user)

if not accounts.exists():
    print("❌ El usuario no tiene cuentas Dropi configuradas")
    print()
    print("Para crear una cuenta Dropi, usa el frontend en:")
    print("  http://localhost:5173/user/reporter-setup")
    print()
    print("O ejecuta este comando en la consola de Django:")
    print(f"  from core.models import DropiAccount")
    print(f"  from django.contrib.auth.models import User")
    print(f"  user = User.objects.get(username='alexcander')")
    print(f"  acct = DropiAccount.objects.create(")
    print(f"      user=user,")
    print(f"      label='reporter',")
    print(f"      email='tu_email_dropi@example.com',")
    print(f"      is_default=True")
    print(f"  )")
    print(f"  acct.set_password_plain('tu_password_dropi')")
    print(f"  acct.save()")
    sys.exit(1)

print(f"✅ Cuentas Dropi encontradas: {accounts.count()}")
print()

for i, account in enumerate(accounts, 1):
    print(f"Cuenta #{i}:")
    print(f"  - ID: {account.id}")
    print(f"  - Label: {account.label}")
    print(f"  - Email: {account.email}")
    print(f"  - Is Default: {account.is_default}")
    print(f"  - Created: {account.created_at}")
    
    # Intentar obtener la contraseña desencriptada
    try:
        password = account.get_password_plain()
        print(f"  - Password: {'*' * len(password)} (longitud: {len(password)})")
    except Exception as e:
        print(f"  - Password: ❌ Error al desencriptar: {e}")
    
    print()

# Verificar qué cuenta se usaría para el reporter
print("=" * 60)
print("Cuenta que se usaría para el reporter:")
print("=" * 60)

dropi_label = 'reporter'
selected_account = (
    DropiAccount.objects.filter(user=user, label=dropi_label).first()
    or DropiAccount.objects.filter(user=user, is_default=True).first()
    or DropiAccount.objects.filter(user=user).first()
)

if selected_account:
    print(f"✅ Cuenta seleccionada:")
    print(f"  - Label: {selected_account.label}")
    print(f"  - Email: {selected_account.email}")
    print(f"  - Is Default: {selected_account.is_default}")
else:
    print("❌ No se pudo seleccionar ninguna cuenta")
