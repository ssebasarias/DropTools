# Generated migration to remove old user tables (auth_user, user_profiles, dropi_accounts)

from django.db import migrations


def remove_old_tables_forward(apps, schema_editor):
    """
    Eliminar las tablas antiguas que ya no se usan.
    Los datos ya fueron migrados a la tabla 'users'.
    """
    with schema_editor.connection.cursor() as cursor:
        # Verificar si las tablas existen antes de eliminarlas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('auth_user', 'user_profiles', 'dropi_accounts')
            AND table_name != 'users';
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        for table in existing_tables:
            print(f"[INFO] Eliminando tabla antigua: {table}")
            cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
            print(f"[OK] Tabla {table} eliminada")


def remove_old_tables_reverse(apps, schema_editor):
    """
    Revertir: No podemos recrear las tablas antiguas fácilmente,
    así que esta función no hace nada.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_configure_users_table'),
    ]

    operations = [
        migrations.RunPython(
            remove_old_tables_forward,
            remove_old_tables_reverse,
        ),
    ]
