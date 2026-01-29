"""
Script para crear usuarios de prueba para testing de bots simultáneos
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dahell_backend.settings')
django.setup()

from core.models import User
from django.contrib.auth.hashers import make_password

def create_test_users():
    """Crea usuarios de prueba si no existen"""
    
    users_data = [
        {
            'username': 'alexander2',
            'email': 'alexander2@test.com',
            'password': 'test123',
            'full_name': 'Alexander2',
            'dropi_email': 'sisas0091@gmail.com',
            'dropi_password': 'Guerrero2345.',
            'role': 'CLIENT',
            'subscription_tier': 'BRONZE',
            'subscription_active': True,
        },
        {
            'username': 'sebastian',
            'email': 'sebastian@test.com',
            'password': 'test123',
            'full_name': 'Sebastian',
            'dropi_email': 'guerreroarias20@gmail.com',
            'dropi_password': 'PAgRRquZSmh86_k',
            'role': 'CLIENT',
            'subscription_tier': 'BRONZE',
            'subscription_active': True,
        }
    ]
    
    created_users = []
    
    for user_data in users_data:
        username = user_data['username']
        email = user_data['email']
        
        # Verificar si ya existe por username o email
        existing_user = User.objects.filter(username=username).first() or User.objects.filter(email=email).first()
        
        if existing_user:
            print(f"⚠️  Usuario '{username}' ya existe (ID: {existing_user.id}), actualizando credenciales Dropi...")
            existing_user.dropi_email = user_data['dropi_email']
            existing_user.dropi_password = user_data['dropi_password']
            existing_user.full_name = user_data['full_name']
            existing_user.subscription_active = True
            existing_user.save()
            print(f"✅ Usuario '{username}' actualizado (ID: {existing_user.id})")
            created_users.append(existing_user)
        else:
            # Crear nuevo usuario (Django asignará ID automáticamente)
            try:
                user = User.objects.create(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=make_password(user_data['password']),
                    full_name=user_data['full_name'],
                    dropi_email=user_data['dropi_email'],
                    dropi_password=user_data['dropi_password'],
                    role=user_data['role'],
                    subscription_tier=user_data['subscription_tier'],
                    subscription_active=user_data['subscription_active'],
                )
                print(f"✅ Usuario '{username}' creado (ID: {user.id})")
                created_users.append(user)
            except Exception as e:
                print(f"❌ Error al crear usuario '{username}': {str(e)}")
                continue
    
    print("\n" + "="*60)
    print("📊 RESUMEN DE USUARIOS DE PRUEBA")
    print("="*60)
    
    all_users = User.objects.filter(subscription_active=True).order_by('id')
    for user in all_users:
        print(f"\nID: {user.id}")
        print(f"  Username: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  Dropi Email: {user.dropi_email}")
        print(f"  Dropi Password: {'*' * len(user.dropi_password) if user.dropi_password else 'NO CONFIGURADO'}")
        print(f"  Rol: {user.role}")
        print(f"  Suscripción: {user.subscription_tier} ({'Activa' if user.subscription_active else 'Inactiva'})")
    
    print("\n" + "="*60)
    print(f"✅ Total de usuarios activos: {all_users.count()}")
    print("="*60)
    
    return created_users

if __name__ == '__main__':
    print("🚀 Creando usuarios de prueba...\n")
    create_test_users()
    print("\n✅ Proceso completado!")
