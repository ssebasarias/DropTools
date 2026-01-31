# Reporter slot system: ReporterSlotConfig, ReporterHourSlot, ReporterReservation,
# ReporterRun, ReporterRange, ReporterRunUser; User.monthly_orders_estimate

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_add_rawordersnapshot_customer_email_if_missing'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='monthly_orders_estimate',
            field=models.PositiveIntegerField(blank=True, help_text='Órdenes mensuales aproximadas', null=True),
        ),
        migrations.CreateModel(
            name='ReporterSlotConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_active_selenium', models.PositiveIntegerField(default=6, help_text='Máximo de procesos Selenium simultáneos')),
                ('estimated_pending_factor', models.DecimalField(decimal_places=4, default=0.08, help_text='Factor para estimar órdenes pendientes: monthly_orders * factor', max_digits=5)),
                ('range_size', models.PositiveIntegerField(default=100, help_text='Tamaño de cada rango de órdenes a reportar')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Configuración Reporter Slots',
                'verbose_name_plural': 'Configuraciones Reporter Slots',
                'db_table': 'reporter_slot_config',
            },
        ),
        migrations.CreateModel(
            name='ReporterHourSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hour', models.PositiveSmallIntegerField(help_text='Hora del día (0-23)', unique=True)),
                ('max_users', models.PositiveIntegerField(default=10, help_text='Máximo de usuarios que pueden reservar esta hora')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Slot horario Reporter',
                'verbose_name_plural': 'Slots horarios Reporter',
                'db_table': 'reporter_hour_slots',
                'ordering': ['hour'],
            },
        ),
        migrations.CreateModel(
            name='ReporterRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheduled_at', models.DateTimeField(help_text='Fecha/hora programada (ej. 2025-01-31 10:00:00)')),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pendiente'), ('running', 'En ejecución'), ('completed', 'Completado'), ('failed', 'Fallido')], db_index=True, default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('slot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='runs', to='core.reporterhourslot')),
            ],
            options={
                'verbose_name': 'Run Reporter',
                'verbose_name_plural': 'Runs Reporter',
                'db_table': 'reporter_runs',
                'ordering': ['-scheduled_at'],
            },
        ),
        migrations.CreateModel(
            name='ReporterReservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('monthly_orders_estimate', models.PositiveIntegerField(default=0, help_text='Órdenes mensuales aproximadas del usuario')),
                ('estimated_pending_orders', models.DecimalField(decimal_places=2, default=0, help_text='monthly_orders_estimate * factor (calculado al guardar)', max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservations', to='core.reporterhourslot')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='reporter_reservation', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Reserva Reporter',
                'verbose_name_plural': 'Reservas Reporter',
                'db_table': 'reporter_reservations',
            },
        ),
        migrations.CreateModel(
            name='ReporterRunUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('download_compare_status', models.CharField(choices=[('pending', 'Pendiente'), ('running', 'Ejecutando'), ('completed', 'Completado'), ('failed', 'Fallido')], db_index=True, default='pending', max_length=20)),
                ('download_compare_completed_at', models.DateTimeField(blank=True, null=True)),
                ('total_pending_orders', models.PositiveIntegerField(default=0)),
                ('total_ranges', models.PositiveIntegerField(default=0)),
                ('ranges_completed', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='run_users', to='core.reporterrun')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reporter_run_users', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Run Usuario Reporter',
                'verbose_name_plural': 'Run Usuarios Reporter',
                'db_table': 'reporter_run_users',
            },
        ),
        migrations.CreateModel(
            name='ReporterRange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('range_start', models.PositiveIntegerField(help_text='Índice inicio (1-based)')),
                ('range_end', models.PositiveIntegerField(help_text='Índice fin (inclusive)')),
                ('status', models.CharField(choices=[('pending', 'Pendiente'), ('locked', 'Bloqueado'), ('processing', 'Procesando'), ('completed', 'Completado'), ('failed', 'Fallido')], db_index=True, default='pending', max_length=20)),
                ('locked_at', models.DateTimeField(blank=True, null=True)),
                ('locked_by', models.CharField(blank=True, help_text='task_id del worker', max_length=255, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ranges', to='core.reporterrun')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reporter_ranges', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Rango Reporter',
                'verbose_name_plural': 'Rangos Reporter',
                'db_table': 'reporter_ranges',
            },
        ),
        migrations.AddIndex(
            model_name='reporterreservation',
            index=models.Index(fields=['slot'], name='reporter_re_slot_id_7a8b0a_idx'),
        ),
        migrations.AddIndex(
            model_name='reporterreservation',
            index=models.Index(fields=['user'], name='reporter_re_user_id_2c3d4e_idx'),
        ),
        migrations.AddIndex(
            model_name='reporterrun',
            index=models.Index(fields=['slot', 'scheduled_at'], name='reporter_ru_slot_id_5e6f7g_idx'),
        ),
        migrations.AddIndex(
            model_name='reporterrun',
            index=models.Index(fields=['status'], name='reporter_ru_status_8h9i0j_idx'),
        ),
        migrations.AddIndex(
            model_name='reporterrange',
            index=models.Index(fields=['run', 'user', 'range_start'], name='reporter_ra_run_id_1k2l3m_idx'),
        ),
        migrations.AddIndex(
            model_name='reporterrange',
            index=models.Index(fields=['run', 'status'], name='reporter_ra_run_id_4n5o6p_idx'),
        ),
        migrations.AddIndex(
            model_name='reporterrunuser',
            index=models.Index(fields=['run', 'user'], name='reporter_ru_run_id_7q8r9s_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='reporterrunuser',
            unique_together={('run', 'user')},
        ),
    ]
