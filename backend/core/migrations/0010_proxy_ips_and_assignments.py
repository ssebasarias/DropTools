# Proxy / IP assignment for Selenium reporter

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_reporter_weight_and_capacity'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProxyIP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip', models.CharField(db_index=True, help_text='Host o IP del proxy', max_length=255)),
                ('port', models.PositiveIntegerField(default=8080, help_text='Puerto del proxy')),
                ('username', models.CharField(blank=True, max_length=255, null=True)),
                ('password_encrypted', models.CharField(blank=True, help_text='Contraseña (encriptada si DROPIPASS_ENCRYPTION_KEY está configurado)', max_length=512, null=True)),
                ('max_accounts', models.PositiveSmallIntegerField(default=5, help_text='Máximo de cuentas (usuarios) por este proxy')),
                ('status', models.CharField(choices=[('active', 'Activo'), ('inactive', 'Inactivo')], db_index=True, default='active', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Proxy IP',
                'verbose_name_plural': 'Proxy IPs',
                'db_table': 'proxy_ips',
            },
        ),
        migrations.CreateModel(
            name='UserProxyAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('last_used_at', models.DateTimeField(blank=True, null=True)),
                ('proxy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_assignments', to='core.proxyip')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='proxy_assignment', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Asignación Usuario Proxy',
                'verbose_name_plural': 'Asignaciones Usuario Proxy',
                'db_table': 'user_proxy_assignments',
            },
        ),
        migrations.AddIndex(
            model_name='proxyip',
            index=models.Index(fields=['status'], name='proxy_ips_status_idx'),
        ),
        migrations.AddIndex(
            model_name='userproxyassignment',
            index=models.Index(fields=['proxy'], name='user_proxy_assignments_proxy_idx'),
        ),
    ]
