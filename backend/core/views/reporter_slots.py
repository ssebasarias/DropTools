# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Count, Case, When, IntegerField, Sum
from django.utils import timezone
from datetime import timedelta
from ..models import (
    ReporterSlotConfig,
    ReporterHourSlot,
    ReporterReservation,
    ReporterRun,
    ReporterRunUser,
    assign_best_available_slot,
)
from ..serializers import ReporterSlotSerializer, ReporterReservationSerializer, ReporterRunSerializer
from ..permissions import MinSubscriptionTier


class ReporterSlotsView(APIView):
    """
    GET /api/reporter/slots/ — Lista horas reservables (ventana reporter) con capacidad por peso.
    Muestra conteos de usuarios por peso y disponibilidad según límites independientes.
    """
    permission_classes = [IsAuthenticated, MinSubscriptionTier("BRONZE")]

    def get(self, request):
        try:
            config = ReporterSlotConfig.objects.first()
            hour_start = getattr(config, 'reporter_hour_start', 0) if config else 0
            hour_end = getattr(config, 'reporter_hour_end', 24) if config else 24
            
            # Annotar con conteos por peso y suma total (para compatibilidad)
            slots = (
                ReporterHourSlot.objects.filter(hour__gte=hour_start, hour__lt=hour_end)
                .annotate(
                    used_points=Sum('reservations__calculated_weight'),
                    users_weight_3=Count(
                        Case(
                            When(reservations__calculated_weight=3, then=1),
                            output_field=IntegerField()
                        )
                    ),
                    users_weight_2=Count(
                        Case(
                            When(reservations__calculated_weight=2, then=1),
                            output_field=IntegerField()
                        )
                    ),
                    users_weight_1=Count(
                        Case(
                            When(reservations__calculated_weight=1, then=1),
                            output_field=IntegerField()
                        )
                    )
                )
                .order_by('hour')
            )
            serializer = ReporterSlotSerializer(slots, many=True)
            return Response(serializer.data)
        except Exception as e:
            import logging
            logging.exception("ReporterSlotsView GET failed")
            return Response(
                {"error": f"Error al cargar horarios: {str(e)}", "hint": "Ejecuta: python manage.py migrate"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReporterReservationsView(APIView):
    """
    POST /api/reporter/reservations/ — Crear reserva (slot_id, monthly_orders_estimate).
    GET /api/reporter/reservations/me — Reserva del usuario actual.
    DELETE /api/reporter/reservations/me — Cancelar reserva.
    """
    permission_classes = [IsAuthenticated, MinSubscriptionTier("BRONZE")]

    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
        reservation = ReporterReservation.objects.filter(user=user).select_related('slot').first()
        if not reservation:
            return Response({"reservation": None})
        serializer = ReporterReservationSerializer(reservation)
        return Response(serializer.data)

    def post(self, request):
        """
        Crear o actualizar reserva con asignación automática de slot.
        
        Body: { "monthly_orders_estimate": 500 }
        
        El sistema asigna automáticamente la mejor hora disponible según:
        - Peso del usuario (calculado desde monthly_orders_estimate: 1, 2 o 3)
        - Límites por peso en cada slot (máx 2 usuarios de cada peso por hora)
        - Ventana horaria configurada (6am-6pm por defecto)
        
        El sistema verifica que haya espacio para el peso específico del usuario,
        no la suma total de puntos.
        """
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
        
        monthly_orders_estimate = int(request.data.get('monthly_orders_estimate', 0) or 0)
        
        if monthly_orders_estimate <= 0:
            return Response(
                {"error": "monthly_orders_estimate debe ser mayor a 0"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Asignar automáticamente el mejor slot disponible
                best_slot = assign_best_available_slot(user, monthly_orders_estimate)
                
                # Eliminar reserva anterior si existe
                ReporterReservation.objects.filter(user=user).delete()
                
                # Crear nueva reserva
                reservation = ReporterReservation.objects.create(
                    user=user,
                    slot=best_slot,
                    monthly_orders_estimate=monthly_orders_estimate
                )
                
            serializer = ReporterReservationSerializer(reservation)
            
            return Response({
                **serializer.data,
                "message": f"¡Reserva confirmada! Tus reportes se ejecutarán automáticamente todos los días a las {best_slot.hour:02d}:00"
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            # Error de capacidad (no hay slots disponibles)
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import logging
            logging.exception("Error al crear reserva automática")
            return Response(
                {"error": f"Error al crear reserva: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
        deleted, _ = ReporterReservation.objects.filter(user=user).delete()
        return Response({"deleted": deleted > 0})


class ReporterRunsView(APIView):
    """
    GET /api/reporter/runs/ — Lista runs recientes (por usuario o por slot).
    """
    permission_classes = [IsAuthenticated, MinSubscriptionTier("BRONZE")]

    def get(self, request):
        try:
            user = request.user
            if not user or not user.is_authenticated:
                return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
            days = int(request.query_params.get('days', 7))
            since = timezone.now() - timedelta(days=days)
            runs = ReporterRun.objects.filter(
                run_users__user=user,
                scheduled_at__gte=since
            ).select_related('slot').distinct().order_by('-scheduled_at')[:20]
            serializer = ReporterRunSerializer(runs, many=True)
            return Response(serializer.data)
        except Exception as e:
            import logging
            logging.exception("ReporterRunsView GET failed")
            return Response(
                {"error": f"Error al cargar runs: {str(e)}", "hint": "Ejecuta: python manage.py migrate"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReporterRunProgressView(APIView):
    """
    GET /api/reporter/runs/<run_id>/progress/ — Progreso detallado de una Run (por usuario).
    """
    permission_classes = [IsAuthenticated, MinSubscriptionTier("BRONZE")]

    def get(self, request, run_id):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
        run = ReporterRun.objects.filter(id=run_id).select_related('slot').first()
        if not run:
            return Response({"error": "Run no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        run_users = ReporterRunUser.objects.filter(run=run).select_related('user')
        users_progress = []
        for ru in run_users:
            users_progress.append({
                "user_id": ru.user_id,
                "username": ru.user.username if ru.user_id else None,
                "download_compare_status": ru.download_compare_status,
                "download_compare_completed_at": ru.download_compare_completed_at.isoformat() if ru.download_compare_completed_at else None,
                "total_pending_orders": ru.total_pending_orders,
                "total_ranges": ru.total_ranges,
                "ranges_completed": ru.ranges_completed,
            })
        return Response({
            "run_id": run.id,
            "run_status": run.status,
            "scheduled_at": run.scheduled_at.isoformat(),
            "slot_hour": run.slot.hour if run.slot_id else None,
            "users": users_progress,
        })
