# -*- coding: utf-8 -*-
"""
Serializers para el sistema de reporter slots
"""
from rest_framework import serializers
from ..models import ReporterHourSlot, ReporterReservation, ReporterRun, ReporterRunUser


class ReporterSlotSerializer(serializers.ModelSerializer):
    """Slot horario con capacidad por peso (límites independientes por peso)."""
    used_points = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()
    hour_label = serializers.SerializerMethodField()
    users_weight_3 = serializers.SerializerMethodField()
    users_weight_2 = serializers.SerializerMethodField()
    users_weight_1 = serializers.SerializerMethodField()
    max_users_weight_3 = serializers.IntegerField(read_only=True)
    max_users_weight_2 = serializers.IntegerField(read_only=True)
    max_users_weight_1 = serializers.IntegerField(read_only=True)
    available_weight_3 = serializers.SerializerMethodField()
    available_weight_2 = serializers.SerializerMethodField()
    available_weight_1 = serializers.SerializerMethodField()

    class Meta:
        model = ReporterHourSlot
        fields = [
            'id', 'hour', 'hour_label',
            'capacity_points', 'used_points', 'available',  # Deprecated, mantener por compatibilidad
            'users_weight_3', 'users_weight_2', 'users_weight_1',
            'max_users_weight_3', 'max_users_weight_2', 'max_users_weight_1',
            'available_weight_3', 'available_weight_2', 'available_weight_1'
        ]

    def get_used_points(self, obj):
        """Suma total de puntos (deprecated, mantener por compatibilidad)."""
        return getattr(obj, 'used_points', None) or 0

    def get_available(self, obj):
        """Disponibilidad general (deprecated, mantener por compatibilidad)."""
        used = getattr(obj, 'used_points', None) or 0
        cap = getattr(obj, 'capacity_points', None) or 6
        return used < cap

    def get_hour_label(self, obj):
        return f"{obj.hour:02d}:00"

    def get_users_weight_3(self, obj):
        """Número actual de usuarios de peso 3."""
        return getattr(obj, 'users_weight_3', None) or 0

    def get_users_weight_2(self, obj):
        """Número actual de usuarios de peso 2."""
        return getattr(obj, 'users_weight_2', None) or 0

    def get_users_weight_1(self, obj):
        """Número actual de usuarios de peso 1."""
        return getattr(obj, 'users_weight_1', None) or 0

    def get_available_weight_3(self, obj):
        """True si hay espacio para más usuarios de peso 3."""
        current = getattr(obj, 'users_weight_3', None) or 0
        max_allowed = getattr(obj, 'max_users_weight_3', None) or 2
        return current < max_allowed

    def get_available_weight_2(self, obj):
        """True si hay espacio para más usuarios de peso 2."""
        current = getattr(obj, 'users_weight_2', None) or 0
        max_allowed = getattr(obj, 'max_users_weight_2', None) or 2
        return current < max_allowed

    def get_available_weight_1(self, obj):
        """True si hay espacio para más usuarios de peso 1."""
        current = getattr(obj, 'users_weight_1', None) or 0
        max_allowed = getattr(obj, 'max_users_weight_1', None) or 2
        return current < max_allowed


class ReporterReservationSerializer(serializers.ModelSerializer):
    slot = ReporterSlotSerializer(read_only=True)
    slot_id = serializers.PrimaryKeyRelatedField(
        queryset=ReporterHourSlot.objects.all(),
        source='slot',
        write_only=True
    )

    class Meta:
        model = ReporterReservation
        fields = [
            'id', 'slot', 'slot_id', 'monthly_orders_estimate', 'calculated_weight',
            'estimated_pending_orders', 'created_at', 'updated_at'
        ]
        read_only_fields = ['calculated_weight', 'estimated_pending_orders', 'created_at', 'updated_at']


class ReporterRunSerializer(serializers.ModelSerializer):
    slot_hour = serializers.SerializerMethodField()

    class Meta:
        model = ReporterRun
        fields = [
            'id', 'slot', 'slot_hour', 'scheduled_at', 'started_at', 'finished_at',
            'status', 'created_at'
        ]

    def get_slot_hour(self, obj):
        return obj.slot.hour if obj.slot_id else None


class ReporterRunProgressSerializer(serializers.Serializer):
    """Progreso de una Run por usuario (para GET /api/reporter/runs/<id>/progress/)."""
    run_id = serializers.IntegerField()
    run_status = serializers.CharField()
    scheduled_at = serializers.DateTimeField()
    users = serializers.ListField(child=serializers.DictField())
