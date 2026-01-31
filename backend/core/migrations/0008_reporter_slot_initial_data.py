# Datos iniciales: ReporterSlotConfig (1 fila) y ReporterHourSlot (24 horas).

from django.db import migrations


def create_initial_slots_and_config(apps, schema_editor):
    ReporterSlotConfig = apps.get_model('core', 'ReporterSlotConfig')
    ReporterHourSlot = apps.get_model('core', 'ReporterHourSlot')

    if not ReporterSlotConfig.objects.exists():
        ReporterSlotConfig.objects.create(
            max_active_selenium=6,
            estimated_pending_factor=0.08,
            range_size=100,
        )

    if ReporterHourSlot.objects.count() < 24:
        for hour in range(24):
            ReporterHourSlot.objects.get_or_create(
                hour=hour,
                defaults={'max_users': 10},
            )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_reporter_slot_models'),
    ]

    operations = [
        migrations.RunPython(create_initial_slots_and_config, noop),
    ]
