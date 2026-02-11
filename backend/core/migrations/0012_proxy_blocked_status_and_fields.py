# Proxy blocked status and tracking fields

from django.db import migrations, models


def update_max_accounts_default(apps, schema_editor):
    """Actualiza max_accounts de proxies existentes a 4 si tienen el valor por defecto de 5."""
    ProxyIP = apps.get_model('core', 'ProxyIP')
    # Solo actualizar proxies que tienen exactamente 5 (el valor anterior por defecto)
    ProxyIP.objects.filter(max_accounts=5).update(max_accounts=4)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_reporter_weight_limits'),
    ]

    operations = [
        # Agregar campos blocked_at y block_reason
        migrations.AddField(
            model_name='proxyip',
            name='blocked_at',
            field=models.DateTimeField(blank=True, help_text='Fecha cuando se bloqueó el proxy', null=True),
        ),
        migrations.AddField(
            model_name='proxyip',
            name='block_reason',
            field=models.TextField(blank=True, help_text='Razón del bloqueo del proxy', null=True),
        ),
        # Modificar campo status para incluir STATUS_BLOCKED
        migrations.AlterField(
            model_name='proxyip',
            name='status',
            field=models.CharField(
                choices=[('active', 'Activo'), ('inactive', 'Inactivo'), ('blocked', 'Bloqueado')],
                db_index=True,
                default='active',
                max_length=20
            ),
        ),
        # Cambiar default de max_accounts de 5 a 4
        migrations.AlterField(
            model_name='proxyip',
            name='max_accounts',
            field=models.PositiveSmallIntegerField(
                default=4,
                help_text='Máximo de cuentas (usuarios) por este proxy'
            ),
        ),
        # Actualizar proxies existentes
        migrations.RunPython(update_max_accounts_default, noop),
    ]
