# Generated manually for RawOrderSnapshot analysis fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_alter_orderreport_days_since_order_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='rawordersnapshot',
            name='customer_email',
            field=models.CharField(blank=True, help_text='Columna: EMAIL', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='product_id',
            field=models.CharField(blank=True, help_text='Columna: PRODUCTO ID', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='sku',
            field=models.CharField(blank=True, db_index=True, help_text='Columna: SKU', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='variation',
            field=models.CharField(blank=True, help_text='Columna: VARIACION', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='profit',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Columna: GANANCIA', max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='shipping_price',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Columna: PRECIO FLETE', max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='supplier_price',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Columna: PRECIO PROVEEDOR', max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='commission',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Columna: COMISION', max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='shipping_type',
            field=models.CharField(blank=True, help_text='Columna: TIPO DE ENVIO', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='notes',
            field=models.TextField(blank=True, help_text='Columna: NOTAS', null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='novelty',
            field=models.CharField(blank=True, help_text='Columna: NOVEDAD', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='novelty_resolved',
            field=models.CharField(blank=True, help_text='Columna: FUE SOLUCIONADA LA NOVEDAD', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='last_movement',
            field=models.CharField(blank=True, help_text='Columna: ÚLTIMO MOVIMIENTO', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='last_movement_date',
            field=models.DateField(blank=True, help_text='Columna: FECHA DE ÚLTIMO MOVIMIENTO', null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='store_type',
            field=models.CharField(blank=True, help_text='Columna: TIPO DE TIENDA', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='store_name',
            field=models.CharField(blank=True, help_text='Columna: TIENDA', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='tags',
            field=models.TextField(blank=True, help_text='Columna: TAGS', null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='order_time',
            field=models.CharField(blank=True, help_text='Columna: HORA', max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='rawordersnapshot',
            name='report_date',
            field=models.DateField(blank=True, help_text='Columna: FECHA DE REPORTE', null=True),
        ),
    ]
