# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.db.models import Count, Q
from datetime import datetime, timedelta, time as dt_time
from django.utils import timezone
import logging
import traceback
from ..models import (
    User,
    WorkflowProgress,
    OrderReport,
    ReportBatch,
    OrderMovementReport,
)
from ..permissions import MinSubscriptionTier

logger = logging.getLogger(__name__)


def _error_payload(message, exc=None, **extra):
    payload = {"error": message}
    payload.update(extra)
    if settings.DEBUG and exc is not None:
        payload["traceback"] = traceback.format_exc()
    return payload


class ReporterConfigView(APIView):
    """
    Gestiona la configuración del Reporter (Credenciales de Dropi).
    """
    
    permission_classes = [IsAuthenticated, MinSubscriptionTier("BRONZE")]
    
    def get(self, request):
        # Require authentication (no insecure fallbacks)
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

        # Usar User directamente (ahora todo está en la tabla users)
        exec_time = user.execution_time
        # Proxy asignado (solo lectura; no se expone contraseña)
        proxy_display = None
        try:
            from ..models import UserProxyAssignment
            assignment = UserProxyAssignment.objects.select_related('proxy').filter(user=user).first()
            if assignment and assignment.proxy:
                proxy_display = f"{assignment.proxy.ip}:{assignment.proxy.port}"
        except Exception:
            pass
        return Response(
            {
                # Usar credenciales Dropi directamente del User
                "email": user.dropi_email or "",
                # No devolver password por seguridad
                "password": "",
                # Persisted schedule time (HH:MM). Default 08:00 if not set.
                "executionTime": exec_time.strftime("%H:%M") if exec_time else "08:00",
                # Proxy asignado (solo lectura; el usuario no puede cambiarlo)
                "proxy_assigned": proxy_display,
            }
        )

    def post(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
             
        try:
            # Actualizar credenciales Dropi directamente en User
            if "email" in request.data or "password" in request.data:
                email = request.data.get("email", "").strip()
                password = request.data.get("password", "").strip()
                
                if email:
                    user.dropi_email = email
                if password:
                    user.set_dropi_password_plain(password)

            # Actualizar schedule time HH:MM
            exec_time_str = request.data.get("executionTime") or request.data.get("execution_time")
            if exec_time_str is not None:
                exec_time_str = str(exec_time_str).strip()
                if exec_time_str == "":
                    user.execution_time = None
                else:
                    try:
                        hh, mm = exec_time_str.split(":")
                        user.execution_time = dt_time(hour=int(hh), minute=int(mm))
                    except Exception:
                        return Response(
                            {"error": "executionTime inválido. Usa formato HH:MM"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

            user.save()
            
            return Response(
                {
                    "status": "success",
                    "message": "Configuración actualizada",
                    "executionTime": user.execution_time.strftime("%H:%M") if user.execution_time else None,
                }
            )
        except Exception as e:
            logger.exception("Error actualizando configuración reporter: user_id=%s", user.id if user else None)
            return Response(
                _error_payload("No se pudo actualizar la configuración del reporter.", exc=e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReporterStartView(APIView):
    """
    Inicia el workflow de reportes manualmente.
    - DROPTOOLS_ENV=development: ejecuta el reporter en proceso (Windows/local, Edge, sin Celery).
    - DROPTOOLS_ENV=production: encola la tarea en Celery (Docker/Linux).
    """
    
    permission_classes = [IsAuthenticated, MinSubscriptionTier("BRONZE")]
    
    def post(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            if not user.dropi_email:
                return Response(
                    {"error": "No Dropi account configured. Please configure dropi_email in user settings."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from django.conf import settings

            # Reset previous running progress
            WorkflowProgress.objects.filter(
                user=user,
                status__in=['pending', 'step1_running', 'step2_running', 'step3_running']
            ).update(status='failed', current_message='Reiniciado por nueva solicitud')

            workflow_progress = WorkflowProgress.objects.create(
                user=user,
                status='step1_running',
                current_message='Iniciando...',
                messages=['Iniciando...'],
                started_at=timezone.now(),
            )

            # Desarrollo: ejecutar reporter en proceso (mismo Python, Edge, sin Celery)
            if not getattr(settings, 'REPORTER_USE_CELERY', True):
                return self._run_reporter_in_process(user, workflow_progress)

            # Producción: encolar en Celery
            return self._enqueue_reporter_celery(user, workflow_progress)

        except Exception as e:
            logger.exception("Error iniciando workflow reporter: user_id=%s", user.id if user else None)
            return Response(
                _error_payload("Error al iniciar workflow.", exc=e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _run_reporter_in_process(self, user, workflow_progress):
        """Ejecuta el reporter en el mismo proceso (desarrollo: Windows, Edge, navegador visible)."""
        from django.conf import settings
        from ..reporter_bot.docker_config import get_download_dir
        from ..reporter_bot.unified_reporter import UnifiedReporter
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[DESARROLLO] Ejecutando reporter en proceso para user_id={user.id} (navegador visible)")
        workflow_progress.current_message = 'Ejecutando en desarrollo (en proceso)...'
        workflow_progress.save(update_fields=['current_message'])
        try:
            download_dir = get_download_dir()
            unified = UnifiedReporter(
                user_id=user.id,
                headless=False,  # desarrollo: navegador visible
                download_dir=str(download_dir),
                browser_priority=None,  # usa get_reporter_browser_order() -> Edge primero en local
            )
            stats = unified.run()
            success = stats.get('downloader', {}).get('success', False) if stats else False
            if success:
                workflow_progress.status = 'completed'
                workflow_progress.current_message = 'Completado (desarrollo)'
            else:
                workflow_progress.status = 'failed'
                workflow_progress.current_message = 'Falló descarga o comparación (desarrollo)'
            workflow_progress.save(update_fields=['status', 'current_message'])
            return Response({
                "status": "completed" if success else "completed_with_errors",
                "message": "Workflow ejecutado en desarrollo (en proceso)",
                "environment": "development",
                "workflow_progress_id": workflow_progress.id,
                "success": success,
                "stats": stats,
            })
        except Exception as e:
            workflow_progress.status = 'failed'
            workflow_progress.current_message = str(e)[:200]
            workflow_progress.save(update_fields=['status', 'current_message'])
            logger.exception("[DESARROLLO] Error en reporter en proceso")
            return Response({
                **_error_payload("Error ejecutando reporter en desarrollo.", exc=e),
                "environment": "development",
                "workflow_progress_id": workflow_progress.id,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _enqueue_reporter_celery(self, user, workflow_progress):
        """Encola el reporter en Celery (producción o desarrollo Docker)."""
        from django.conf import settings
        from ..tasks import execute_workflow_task
        run_mode = getattr(settings, 'REPORTER_RUN_MODE', 'production')
        workflow_progress.current_message = 'Encolando en Celery...'
        workflow_progress.save(update_fields=['current_message'])
        try:
            task_result = execute_workflow_task.delay(user.id)
            return Response({
                "status": "enqueued",
                "message": "Workflow encolado para ejecución asíncrona",
                "task_id": task_result.id,
                "environment": "production" if run_mode == "production" else "development_docker",
                "run_mode": run_mode,
                "workflow_progress_id": workflow_progress.id
            })
        except Exception as celery_error:
            workflow_progress.status = 'failed'
            workflow_progress.current_message = f'Error al encolar: {str(celery_error)}'
            workflow_progress.save(update_fields=['status', 'current_message'])
            return Response({
                **_error_payload("No se pudo encolar la tarea.", exc=celery_error)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReporterEnvView(APIView):
    """
    Devuelve el modo activo para que el frontend muestre certeza.
    run_mode: development | development_docker | production
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.conf import settings
        env_name = getattr(settings, 'DROPTOOLS_ENV', getattr(settings, 'DAHELL_ENV', 'production'))
        use_celery = getattr(settings, 'REPORTER_USE_CELERY', True)
        run_mode = getattr(settings, 'REPORTER_RUN_MODE', 'production')
        if run_mode == 'development_docker':
            message = "desarrollo (Docker/Celery)"
        elif run_mode == 'development':
            message = "desarrollo (reporter en proceso)"
        else:
            message = "producción (Celery)"
        return Response({
            "droptools_env": env_name,
            "reporter_use_celery": use_celery,
            "run_mode": run_mode,
            "message": message,
        })


class ReporterStopView(APIView):
    """
    Detiene todos los procesos del reporter en segundo plano (tareas Celery activas y cola).
    Solo disponible en modo desarrollo (development o development_docker) para evitar zombies
    y colisiones al volver a pulsar "Iniciar a Reportar".
    """
    
    permission_classes = [IsAuthenticated, MinSubscriptionTier("BRONZE")]
    
    def post(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

        from django.conf import settings
        run_mode = getattr(settings, 'REPORTER_RUN_MODE', 'production')
        if run_mode not in ('development', 'development_docker'):
            return Response(
                {"error": "Detener procesos solo está disponible en modo desarrollo."},
                status=status.HTTP_403_FORBIDDEN
            )

        revoked_ids = []
        purged = False
        try:
            from droptools_backend.celery import app
            # Tareas del reporter que queremos revocar
            reporter_task_names = (
                'core.tasks.execute_workflow_task',
                'core.tasks.execute_workflow_task_test',
            )
            inspect = app.control.inspect()
            active = inspect.active() or {}
            for _worker, tasks in active.items():
                for t in tasks:
                    name = t.get('name') or t.get('task')
                    if name in reporter_task_names:
                        tid = t.get('id')
                        if tid:
                            app.control.revoke(tid, terminate=True)
                            revoked_ids.append(tid)
            # Purgar la cola para quitar tareas pendientes (evitar que se ejecuten después)
            try:
                app.control.purge()
                purged = True
            except Exception:
                pass
            # Marcar progreso del usuario como detenido para que el panel muestre "Detenido"
            WorkflowProgress.objects.filter(
                user=user,
                status__in=['pending', 'step1_running', 'step2_running', 'step3_running']
            ).update(
                status='failed',
                current_message='Procesos detenidos por el usuario. No hay tareas en ejecución.'
            )
            msg = f"Procesos detenidos: {len(revoked_ids)} tarea(s) revocada(s). Cola purgada: {purged}."
            return Response({
                "stopped": len(revoked_ids),
                "revoked_ids": revoked_ids,
                "purged": purged,
                "message": msg,
            })
        except Exception as e:
            logger.exception("Error deteniendo reporter: user_id=%s", user.id if user else None)
            return Response(
                _error_payload(
                    "No se pudieron detener los procesos del reporter.",
                    exc=e,
                    revoked_ids=revoked_ids,
                    purged=purged,
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReporterStatusView(APIView):
    """
    Obtiene el estado actual de los reportes (contadores y estadísticas) y progreso del workflow
    """
    
    permission_classes = [IsAuthenticated, MinSubscriptionTier("BRONZE")]
    
    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            logger.info("[ReporterStatusView] user_id=%s solicitó estado", user.id)

            # Hoy y mes en timezone configurado (America/Bogota)
            tz = timezone.get_current_timezone()
            now = timezone.localtime(timezone.now())
            today = now.date()
            first_of_month = today.replace(day=1)
            
            # CORRECCIÓN: Usar make_aware en lugar de localize para compatibilidad con ZoneInfo
            naive_today_start = datetime.combine(today, dt_time.min)
            today_start = timezone.make_aware(naive_today_start, timezone.get_current_timezone())
            today_end = today_start + timedelta(days=1)
            
            naive_month_start = datetime.combine(first_of_month, dt_time.min)
            month_start = timezone.make_aware(naive_month_start, timezone.get_current_timezone())

            # Lógica ROBUSTA de KPIs
            
            # 1. Reportados en las últimas 24 horas (ventana deslizante para evitar problemas de timezone)
            last_24h = timezone.now() - timedelta(hours=24)
            total_reported = OrderReport.objects.filter(
                user=user,
                updated_at__gte=last_24h
            ).filter(
                # Criterio doble: status es 'reportado' O report_generated es True
                Q(status='reportado') | Q(report_generated=True)
            ).count()
            
            logger.info(f"[ReporterStatusView] total_reported (24h sliding): {total_reported}")

            # 2. Reportados en el mes actual
            total_reported_month = OrderReport.objects.filter(
                user=user,
                updated_at__gte=month_start
            ).filter(
                Q(status='reportado') | Q(report_generated=True)
            ).count()
            
            logger.info(f"[ReporterStatusView] total_reported_month: {total_reported_month}")

            # 3. Pendientes (Próximos a reportar)
            pending_24h = OrderReport.objects.filter(
                user=user,
                status='cannot_generate_yet',
                next_attempt_time__gt=timezone.now()
            ).count()

            total_pending = OrderReport.objects.filter(
                user=user
            ).exclude(status='reportado').count()
            logger.info(f"[ReporterStatusView] total_pending: {total_pending}")
            
            # 4. Total histórico (para debug)
            total_historical = OrderReport.objects.filter(user=user).count()
            logger.info(f"[ReporterStatusView] total_historical: {total_historical}")
            
            # Obtener órdenes sin movimiento del último batch (detectadas por el comparer)
            # Esto es lo que el frontend usa para mostrar "Órdenes pendientes" durante el reporte
            latest_batch = ReportBatch.objects.filter(user=user, status='SUCCESS').order_by('-created_at').first()
            total_pending_movement = 0
            if latest_batch:
                total_pending_movement = OrderMovementReport.objects.filter(
                    batch=latest_batch,
                    is_resolved=False
                ).count()
                logger.info(f"[ReporterStatusView] latest_batch: {latest_batch.id}, total_pending_movement: {total_pending_movement}")
            else:
                logger.warning("[ReporterStatusView] No hay batches SUCCESS para user_id=%s", user.id)
            
            # Obtener última actualización
            last_report = OrderReport.objects.filter(user=user).order_by('-updated_at').first()
            last_updated = last_report.updated_at.isoformat() if last_report else None
            
            # Obtener progreso del workflow más reciente
            workflow_progress = WorkflowProgress.objects.filter(user=user).order_by('-started_at').first()
            workflow_status = None
            if workflow_progress:
                workflow_status = {
                    "status": workflow_progress.status,
                    "current_message": workflow_progress.current_message,
                    "messages": workflow_progress.messages,
                    "started_at": workflow_progress.started_at.isoformat(),
                    "step1_completed_at": workflow_progress.step1_completed_at.isoformat() if workflow_progress.step1_completed_at else None,
                    "step2_completed_at": workflow_progress.step2_completed_at.isoformat() if workflow_progress.step2_completed_at else None,
                    "step3_completed_at": workflow_progress.step3_completed_at.isoformat() if workflow_progress.step3_completed_at else None,
                    "completed_at": workflow_progress.completed_at.isoformat() if workflow_progress.completed_at else None,
                }
            
            # Información de debug para diagnosticar problemas
            # Información de debug ampliada - Breakdown por status hoy
            status_breakdown = OrderReport.objects.filter(
                user=user,
                updated_at__gte=today_start,
                updated_at__lt=today_end
            ).values('status').annotate(count=Count('id'))
            
            breakdown_dict = {item['status']: item['count'] for item in status_breakdown}

            last_5_reports = OrderReport.objects.filter(user=user).order_by('-updated_at')[:5]
            reports_debug = []
            for r in last_5_reports:
                reports_debug.append({
                    "id": r.id,
                    "phone": r.order_phone,
                    "status": r.status,
                    "updated_at": r.updated_at.isoformat(),
                    "user_id": r.user_id
                })

            debug_info = None
            if settings.DEBUG:
                debug_info = {
                    "has_batches": latest_batch is not None,
                    "latest_batch_id": latest_batch.id if latest_batch else None,
                    "latest_batch_date": latest_batch.created_at.isoformat() if latest_batch else None,
                    "total_batches": ReportBatch.objects.filter(user=user, status='SUCCESS').count(),
                    "total_order_reports": OrderReport.objects.filter(user=user).count(),
                    "timezone": str(tz),
                    "today_start": today_start.isoformat(),
                    "month_start": month_start.isoformat(),
                    "recent_reports": reports_debug,
                    "status_breakdown_today": breakdown_dict,
                    "server_time": timezone.now().isoformat(),
                    "total_historical": total_historical,
                    "global_reports_today_count": OrderReport.objects.filter(updated_at__gte=last_24h).count(),
                    "global_reports_all_time": OrderReport.objects.count()
                }
            
            logger.info(f"[ReporterStatusView] Enviando response - reported:{total_reported}, month:{total_reported_month}, pending:{total_pending}, movement:{total_pending_movement}")
            
            payload = {
                "total_reported": total_reported,
                "total_reported_month": total_reported_month,
                "pending_24h": pending_24h,
                "total_pending": total_pending,
                "total_pending_movement": total_pending_movement,  # Órdenes sin movimiento del comparer
                "last_updated": last_updated,
                "workflow_progress": workflow_status,
            }
            if debug_info is not None:
                payload["debug"] = debug_info
            return Response(payload)
            
        except Exception as e:
            logger.exception("Error obteniendo estado reporter: user_id=%s", user.id if user else None)
            return Response(
                _error_payload("Error al obtener estado del reporter.", exc=e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReporterListView(APIView):
    """
    Obtiene la lista de órdenes reportadas con información detallada
    """
    
    permission_classes = [IsAuthenticated, MinSubscriptionTier("BRONZE")]
    
    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            # Obtener parámetros de paginación
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 50))
            status_filter = request.query_params.get('status', 'reportado')
            
            # Todas las órdenes reportadas del usuario (hoy, mes e histórico), no solo del día
            queryset = OrderReport.objects.filter(user=user)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            # Ordenar por fecha de actualización (más recientes primero)
            queryset = queryset.order_by('-updated_at')
            
            # Paginación
            start = (page - 1) * page_size
            end = start + page_size
            
            reports = queryset[start:end]
            
            # Función helper para corregir encoding (ó -> ó)
            def fix_encoding(text):
                if not text:
                    return text
                try:
                    # Intenta revertir el Mojibake: Bytes UTF-8 interpretados como CP1252
                    return text.encode('cp1252').decode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    # Si falla, el texto estaba bien o es otro error
                    return text
            
            results = []
            now = timezone.now()
            for report in reports:
                # Preferir cálculo real desde último movimiento capturado en Dropi.
                days_without_movement = report.inactivity_days_real
                if days_without_movement is None and report.last_movement_date:
                    days_without_movement = (now.date() - report.last_movement_date).days
                if days_without_movement is None and report.created_at:
                    created_at = report.created_at
                    if timezone.is_naive(created_at):
                        created_at = timezone.make_aware(created_at, timezone.get_current_timezone())
                    delta = now - created_at
                    days_without_movement = delta.days
                
                results.append({
                    "id": report.id,
                    "order_phone": report.order_phone,
                    "order_id": fix_encoding(report.order_id or ""),
                    "customer_name": fix_encoding(report.customer_name or ""),
                    "product_name": fix_encoding(report.product_name or ""),
                    "status": report.status,
                    "report_generated": report.report_generated,
                    "order_state": fix_encoding(report.order_state or ""),
                    "last_movement_status": fix_encoding(report.last_movement_status or ""),
                    "last_movement_date": report.last_movement_date.isoformat() if report.last_movement_date else None,
                    "created_at": report.created_at.isoformat(),
                    "updated_at": report.updated_at.isoformat(),
                    "next_attempt_time": report.next_attempt_time.isoformat() if report.next_attempt_time else None,
                    "days_without_movement": days_without_movement,
                    "days_stuck": days_without_movement  # Alias para compatibilidad
                })
            
            # Contar total
            total = queryset.count()
            
            return Response({
                "results": results,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            })
            
        except Exception as e:
            return Response(
                {"error": f"Error al obtener lista: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
