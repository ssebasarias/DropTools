# -*- coding: utf-8 -*-
"""
Comando para calcular métricas analíticas diarias.
Ejecuta cálculo de métricas del día anterior para todos los usuarios activos.
Puede ejecutarse diariamente vía cron/celery.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import User
from core.services.analytics_service import AnalyticsService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Calcula métricas analíticas diarias para todos los usuarios activos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Fecha objetivo en formato YYYY-MM-DD (default: ayer)',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Calcular solo para un usuario específico (ID)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular ejecución sin guardar datos',
        )

    def handle(self, *args, **options):
        target_date_str = options.get('date')
        user_id = options.get('user_id')
        dry_run = options.get('dry_run', False)
        
        if target_date_str:
            try:
                from datetime import datetime
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR(f'Formato de fecha inválido: {target_date_str}. Use YYYY-MM-DD')
                )
                return
        else:
            # Por defecto, calcular para ayer
            target_date = (timezone.now() - timedelta(days=1)).date()
        
        self.stdout.write(
            self.style.SUCCESS(f'Calculando métricas analíticas para fecha: {target_date}')
        )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se guardarán datos'))
        
        # Obtener usuarios
        if user_id:
            users = User.objects.filter(id=user_id, is_active=True)
            if not users.exists():
                self.stdout.write(
                    self.style.ERROR(f'Usuario ID {user_id} no encontrado o inactivo')
                )
                return
        else:
            # Todos los usuarios activos
            users = User.objects.filter(is_active=True)
        
        total_users = users.count()
        self.stdout.write(f'Procesando {total_users} usuario(s)...')
        
        success_count = 0
        error_count = 0
        
        for user in users:
            try:
                self.stdout.write(f'  Procesando usuario: {user.username} (ID: {user.id})...')
                
                if dry_run:
                    # Simular sin guardar
                    service = AnalyticsService(user)
                    results = service.calculate_all_metrics(target_date)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'    ✓ Simulado: snapshot, {len(results["carriers"])} transportadoras, '
                            f'{len(results["products"])} productos'
                        )
                    )
                else:
                    # Calcular y guardar
                    service = AnalyticsService(user)
                    results = service.calculate_all_metrics(target_date)
                    
                    snapshot = results.get('snapshot')
                    if snapshot:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'    ✓ Completado: {snapshot.total_orders} órdenes, '
                                f'{len(results["carriers"])} transportadoras, '
                                f'{len(results["products"])} productos'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f'    ⚠ Sin datos para fecha {target_date}'
                            )
                        )
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                logger.exception(f'Error calculando métricas para usuario {user.id}: {e}')
                self.stdout.write(
                    self.style.ERROR(f'    ✗ Error: {str(e)}')
                )
                # Continuar con el siguiente usuario sin afectar otros
                continue
        
        # Resumen
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'Resumen:'))
        self.stdout.write(f'  Fecha procesada: {target_date}')
        self.stdout.write(f'  Usuarios procesados: {success_count}')
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'  Errores: {error_count}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
