# Analytics models for historical data storage

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_proxy_blocked_status_and_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnalyticsDailySnapshot',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('date', models.DateField(db_index=True, help_text='Fecha del snapshot')),
                ('total_orders', models.IntegerField(default=0, help_text='Total de pedidos')),
                ('total_guides', models.IntegerField(default=0, help_text='Total de guías')),
                ('products_sold', models.IntegerField(default=0, help_text='Total de productos vendidos')),
                ('total_revenue', models.DecimalField(decimal_places=2, default=0, help_text='Ingresos totales', max_digits=12)),
                ('total_profit', models.DecimalField(decimal_places=2, default=0, help_text='Ganancia total', max_digits=12)),
                ('confirmation_pct', models.DecimalField(decimal_places=2, default=0, help_text='% de confirmación', max_digits=5)),
                ('cancellation_pct', models.DecimalField(decimal_places=2, default=0, help_text='% de cancelación', max_digits=5)),
                ('delivered_count', models.IntegerField(default=0, help_text='Órdenes entregadas')),
                ('returns_count', models.IntegerField(default=0, help_text='Órdenes devueltas')),
                ('cancelled_count', models.IntegerField(default=0, help_text='Órdenes canceladas')),
                ('in_transit_count', models.IntegerField(default=0, help_text='Órdenes en tránsito')),
                ('in_warehouse_count', models.IntegerField(default=0, help_text='Órdenes en bodega')),
                ('recollections_count', models.IntegerField(default=0, help_text='Órdenes en recaudo')),
                ('projected_revenue', models.DecimalField(decimal_places=2, default=0, help_text='Ingresos proyectados (confirmados)', max_digits=12)),
                ('recovered_valuation', models.DecimalField(decimal_places=2, default=0, help_text='Valoración recuperada de cancelados', max_digits=12)),
                ('projected_profit_bps', models.DecimalField(decimal_places=2, default=0, help_text='Utilidad proyectada (BPS)', max_digits=12)),
                ('net_profit_real', models.DecimalField(decimal_places=2, default=0, help_text='Ganancia neta real (entregados)', max_digits=12)),
                ('delivery_effectiveness_pct', models.DecimalField(decimal_places=2, default=0, help_text='% Efectividad de entrega', max_digits=5)),
                ('global_returns_pct', models.DecimalField(decimal_places=2, default=0, help_text='% Devoluciones global', max_digits=5)),
                ('annulation_pct', models.DecimalField(decimal_places=2, default=0, help_text='% Anulación', max_digits=5)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='analytics_daily_snapshots', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Snapshot Diario Analytics',
                'verbose_name_plural': 'Snapshots Diarios Analytics',
                'db_table': 'analytics_daily_snapshots',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='AnalyticsCarrierDaily',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('date', models.DateField(db_index=True, help_text='Fecha del snapshot')),
                ('carrier', models.CharField(db_index=True, help_text='Nombre de la transportadora', max_length=100)),
                ('approved_count', models.IntegerField(default=0, help_text='Total aprobados')),
                ('delivered_count', models.IntegerField(default=0, help_text='Entregados')),
                ('returns_count', models.IntegerField(default=0, help_text='Devoluciones')),
                ('cancelled_count', models.IntegerField(default=0, help_text='Cancelados')),
                ('recollections_count', models.IntegerField(default=0, help_text='Recaudos')),
                ('in_transit_count', models.IntegerField(default=0, help_text='En tránsito')),
                ('times_count', models.IntegerField(default=0, help_text='Con tiempos (retrasos)')),
                ('times_pct', models.DecimalField(decimal_places=2, default=0, help_text='% Tiempos', max_digits=5)),
                ('sales_amount', models.DecimalField(decimal_places=2, default=0, help_text='Monto de ventas', max_digits=12)),
                ('sales_pct', models.DecimalField(decimal_places=2, default=0, help_text='% Ventas del total', max_digits=5)),
                ('effectiveness_pct', models.DecimalField(decimal_places=2, default=0, help_text='% Efectividad', max_digits=5)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='analytics_carrier_daily', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Analytics Transportadora Diario',
                'verbose_name_plural': 'Analytics Transportadoras Diarios',
                'db_table': 'analytics_carrier_daily',
                'ordering': ['-date', '-sales_amount'],
            },
        ),
        migrations.CreateModel(
            name='AnalyticsProductDaily',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('date', models.DateField(db_index=True, help_text='Fecha del snapshot')),
                ('product_name', models.TextField(db_index=True, help_text='Nombre del producto')),
                ('sales_count', models.IntegerField(default=0, help_text='Cantidad de ventas')),
                ('profit_total', models.DecimalField(decimal_places=2, default=0, help_text='Utilidad total', max_digits=12)),
                ('margin_pct', models.DecimalField(decimal_places=2, default=0, help_text='% Margen', max_digits=5)),
                ('discount_pct', models.DecimalField(decimal_places=2, default=0, help_text='% Descuento', max_digits=5)),
                ('sale_value', models.DecimalField(decimal_places=2, default=0, help_text='Valor de venta', max_digits=12)),
                ('gross_profit', models.DecimalField(decimal_places=2, default=0, help_text='Utilidad bruta', max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='analytics_product_daily', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Analytics Producto Diario',
                'verbose_name_plural': 'Analytics Productos Diarios',
                'db_table': 'analytics_product_daily',
                'ordering': ['-date', '-gross_profit'],
            },
        ),
        migrations.CreateModel(
            name='AnalyticsCarrierReports',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('carrier', models.CharField(db_index=True, help_text='Nombre de la transportadora', max_length=100)),
                ('report_date', models.DateField(db_index=True, help_text='Fecha del reporte')),
                ('reports_count', models.IntegerField(default=0, help_text='Cantidad de reportes generados')),
                ('last_reported_at', models.DateTimeField(blank=True, help_text='Última vez que se reportó', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='analytics_carrier_reports', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Analytics Reportes Transportadora',
                'verbose_name_plural': 'Analytics Reportes Transportadoras',
                'db_table': 'analytics_carrier_reports',
                'ordering': ['-report_date', '-reports_count'],
            },
        ),
        migrations.CreateModel(
            name='AnalyticsStatusBreakdown',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('date', models.DateField(db_index=True, help_text='Fecha del snapshot')),
                ('status', models.CharField(db_index=True, help_text='Estado de la orden', max_length=100)),
                ('orders_count', models.IntegerField(default=0, help_text='Cantidad de órdenes')),
                ('total_value', models.DecimalField(decimal_places=2, default=0, help_text='Valor total', max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='analytics_status_breakdown', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Analytics Desglose Estado',
                'verbose_name_plural': 'Analytics Desglose Estados',
                'db_table': 'analytics_status_breakdown',
                'ordering': ['-date', '-orders_count'],
            },
        ),
        migrations.AddIndex(
            model_name='analyticsdailysnapshot',
            index=models.Index(fields=['user', 'date'], name='analytics_d_user_id_date_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticsdailysnapshot',
            index=models.Index(fields=['date'], name='analytics_d_date_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticsdailysnapshot',
            index=models.Index(fields=['user', '-date'], name='analytics_d_user_id_date_desc_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticscarrierdaily',
            index=models.Index(fields=['user', 'date', 'carrier'], name='analytics_c_user_id_date_carrier_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticscarrierdaily',
            index=models.Index(fields=['user', 'carrier'], name='analytics_c_user_id_carrier_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticscarrierdaily',
            index=models.Index(fields=['user', '-date'], name='analytics_c_user_id_date_desc_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticsproductdaily',
            index=models.Index(fields=['user', 'date', 'product_name'], name='analytics_p_user_id_date_product_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticsproductdaily',
            index=models.Index(fields=['user', 'product_name'], name='analytics_p_user_id_product_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticsproductdaily',
            index=models.Index(fields=['user', '-date'], name='analytics_p_user_id_date_desc_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticscarrierreports',
            index=models.Index(fields=['user', 'carrier', 'report_date'], name='analytics_cr_user_id_carrier_report_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticscarrierreports',
            index=models.Index(fields=['user', 'carrier'], name='analytics_cr_user_id_carrier_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticscarrierreports',
            index=models.Index(fields=['user', '-report_date'], name='analytics_cr_user_id_report_date_desc_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticsstatusbreakdown',
            index=models.Index(fields=['user', 'date', 'status'], name='analytics_s_user_id_date_status_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticsstatusbreakdown',
            index=models.Index(fields=['user', 'status'], name='analytics_s_user_id_status_idx'),
        ),
        migrations.AddIndex(
            model_name='analyticsstatusbreakdown',
            index=models.Index(fields=['user', '-date'], name='analytics_s_user_id_date_desc_idx'),
        ),
        migrations.AddConstraint(
            model_name='analyticsdailysnapshot',
            constraint=models.UniqueConstraint(fields=('user', 'date'), name='analytics_daily_snapshot_user_date_unique'),
        ),
        migrations.AddConstraint(
            model_name='analyticscarrierdaily',
            constraint=models.UniqueConstraint(fields=('user', 'date', 'carrier'), name='analytics_carrier_daily_user_date_carrier_unique'),
        ),
        migrations.AddConstraint(
            model_name='analyticsproductdaily',
            constraint=models.UniqueConstraint(fields=('user', 'date', 'product_name'), name='analytics_product_daily_user_date_product_unique'),
        ),
        migrations.AddConstraint(
            model_name='analyticscarrierreports',
            constraint=models.UniqueConstraint(fields=('user', 'carrier', 'report_date'), name='analytics_carrier_reports_user_carrier_date_unique'),
        ),
        migrations.AddConstraint(
            model_name='analyticsstatusbreakdown',
            constraint=models.UniqueConstraint(fields=('user', 'date', 'status'), name='analytics_status_breakdown_user_date_status_unique'),
        ),
    ]
