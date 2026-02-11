# Reporter: límites por peso (max_users_weight_3, max_users_weight_2, max_users_weight_1)

from django.db import migrations, models


def set_default_weight_limits(apps, schema_editor):
    """Establece límites por defecto para todos los slots existentes."""
    ReporterHourSlot = apps.get_model('core', 'ReporterHourSlot')
    ReporterHourSlot.objects.all().update(
        max_users_weight_3=2,
        max_users_weight_2=2,
        max_users_weight_1=2
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_proxy_ips_and_assignments'),
    ]

    operations = [
        migrations.AddField(
            model_name='reporterhourslot',
            name='max_users_weight_3',
            field=models.PositiveSmallIntegerField(
                default=2,
                help_text='Máximo número de usuarios de peso 3 (grandes) permitidos en esta hora'
            ),
        ),
        migrations.AddField(
            model_name='reporterhourslot',
            name='max_users_weight_2',
            field=models.PositiveSmallIntegerField(
                default=2,
                help_text='Máximo número de usuarios de peso 2 (medianos) permitidos en esta hora'
            ),
        ),
        migrations.AddField(
            model_name='reporterhourslot',
            name='max_users_weight_1',
            field=models.PositiveSmallIntegerField(
                default=2,
                help_text='Máximo número de usuarios de peso 1 (pequeños) permitidos en esta hora'
            ),
        ),
        migrations.RunPython(set_default_weight_limits, noop),
    ]
