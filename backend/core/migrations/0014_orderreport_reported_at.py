# Generated manually for control de reportes por fecha/hora

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_analytics_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderreport',
            name='reported_at',
            field=models.DateTimeField(blank=True, db_index=True, help_text='Fecha y hora en que se generó el reporte exitosamente (status=reportado). Para control y KPIs.', null=True),
        ),
    ]
