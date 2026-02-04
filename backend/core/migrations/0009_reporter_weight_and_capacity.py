# Reporter: capacidad por peso (calculated_weight, capacity_points, slot_capacity, reporter_hour_start/end)

from django.db import migrations, models


def weight_from_orders(n):
    if n is None or n < 0:
        return 1
    n = min(int(n), 10000)
    if n <= 2000:
        return 1
    if n <= 5000:
        return 2
    return 3


def backfill_weight_and_capacity(apps, schema_editor):
    ReporterReservation = apps.get_model('core', 'ReporterReservation')
    for res in ReporterReservation.objects.all():
        w = weight_from_orders(res.monthly_orders_estimate)
        ReporterReservation.objects.filter(pk=res.pk).update(calculated_weight=w)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_reporter_slot_initial_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='reporterslotconfig',
            name='slot_capacity',
            field=models.PositiveSmallIntegerField(default=6, help_text='Puntos de capacidad máximos por hora (suma de pesos de reservas)'),
        ),
        migrations.AddField(
            model_name='reporterslotconfig',
            name='reporter_hour_start',
            field=models.PositiveSmallIntegerField(default=6, help_text='Hora inicio ventana reporter (0-23). Ej: 6 = 6:00'),
        ),
        migrations.AddField(
            model_name='reporterslotconfig',
            name='reporter_hour_end',
            field=models.PositiveSmallIntegerField(default=18, help_text='Hora fin ventana reporter (0-23). Ej: 18 = horas 6-17 reservables'),
        ),
        migrations.AddField(
            model_name='reporterhourslot',
            name='capacity_points',
            field=models.PositiveSmallIntegerField(default=6, help_text='Puntos de capacidad máximos en esta hora (suma de calculated_weight)'),
        ),
        migrations.AddField(
            model_name='reporterreservation',
            name='calculated_weight',
            field=models.PositiveSmallIntegerField(default=1, help_text='Peso por volumen: 1 pequeño, 2 mediano, 3 grande (calculado al guardar)'),
        ),
        migrations.RunPython(backfill_weight_and_capacity, noop),
    ]
