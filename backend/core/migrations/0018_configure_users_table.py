# Generated migration to configure users table

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_create_unified_users'),
    ]

    operations = [
        # La tabla ya fue renombrada manualmente a 'users'
        # Solo necesitamos actualizar el db_table del modelo
        migrations.RunSQL(
            sql="-- Tabla ya renombrada a users",
            reverse_sql="-- No revertir"
        ),
    ]
