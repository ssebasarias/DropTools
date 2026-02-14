from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_user_email_verification_and_auth_tokens'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordermovementreport',
            name='inactivity_days_real',
            field=models.IntegerField(
                blank=True,
                help_text='Dias reales de inactividad calculados desde last_movement_date.',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='ordermovementreport',
            name='last_movement_date',
            field=models.DateField(
                blank=True,
                db_index=True,
                help_text='Fecha del ultimo movimiento informada por Dropi durante el intento de reporte.',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='ordermovementreport',
            name='last_movement_status',
            field=models.CharField(
                blank=True,
                help_text='Estado de la orden mostrado por Dropi junto a la fecha de ultimo movimiento.',
                max_length=150,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='orderreport',
            name='inactivity_days_real',
            field=models.IntegerField(
                blank=True,
                help_text='Dias reales de inactividad calculados desde la fecha de ultimo movimiento.',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='orderreport',
            name='last_movement_date',
            field=models.DateField(
                blank=True,
                db_index=True,
                help_text='Fecha del ultimo movimiento informada por Dropi en el formulario de nueva consulta.',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='orderreport',
            name='last_movement_status',
            field=models.CharField(
                blank=True,
                help_text='Estado de la orden reportado junto con la fecha del ultimo movimiento.',
                max_length=150,
                null=True
            ),
        ),
    ]
