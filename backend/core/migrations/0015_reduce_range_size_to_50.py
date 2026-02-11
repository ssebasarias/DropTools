# Reducir range_size de 100 a 50 para mejor paralelismo entre workers

from django.db import migrations


def update_range_size_to_50(apps, schema_editor):
    ReporterSlotConfig = apps.get_model('core', 'ReporterSlotConfig')
    config = ReporterSlotConfig.objects.first()
    if config and config.range_size == 100:
        config.range_size = 50
        config.save(update_fields=['range_size'])


def reverse_range_size_to_100(apps, schema_editor):
    ReporterSlotConfig = apps.get_model('core', 'ReporterSlotConfig')
    config = ReporterSlotConfig.objects.first()
    if config and config.range_size == 50:
        config.range_size = 100
        config.save(update_fields=['range_size'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_orderreport_reported_at'),
    ]

    operations = [
        migrations.RunPython(update_range_size_to_50, reverse_range_size_to_100),
    ]
