# -*- coding: utf-8 -*-
"""
Serializers para analytics y métricas
"""
from rest_framework import serializers
from ..models import (
    AnalyticsDailySnapshot,
    AnalyticsCarrierDaily,
    AnalyticsProductDaily,
    AnalyticsCarrierReports,
    AnalyticsStatusBreakdown,
)


class AnalyticsDailySnapshotSerializer(serializers.ModelSerializer):
    """Serializer para snapshot diario de analytics."""
    class Meta:
        model = AnalyticsDailySnapshot
        fields = [
            'id', 'date', 'total_orders', 'total_guides', 'products_sold',
            'total_revenue', 'total_profit', 'confirmation_pct', 'cancellation_pct',
            'delivered_count', 'returns_count', 'cancelled_count',
            'in_transit_count', 'in_warehouse_count', 'recollections_count',
            'projected_revenue', 'recovered_valuation', 'projected_profit_bps',
            'net_profit_real', 'delivery_effectiveness_pct', 'global_returns_pct',
            'annulation_pct', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnalyticsCarrierDailySerializer(serializers.ModelSerializer):
    """Serializer para métricas diarias por transportadora."""
    class Meta:
        model = AnalyticsCarrierDaily
        fields = [
            'id', 'date', 'carrier', 'approved_count', 'delivered_count',
            'returns_count', 'cancelled_count', 'recollections_count',
            'in_transit_count', 'times_count', 'times_pct', 'sales_amount',
            'sales_pct', 'effectiveness_pct', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnalyticsProductDailySerializer(serializers.ModelSerializer):
    """Serializer para métricas diarias por producto."""
    class Meta:
        model = AnalyticsProductDaily
        fields = [
            'id', 'date', 'product_name', 'sales_count', 'profit_total',
            'margin_pct', 'discount_pct', 'sale_value', 'gross_profit',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnalyticsCarrierReportsSerializer(serializers.ModelSerializer):
    """Serializer para reportes por transportadora."""
    class Meta:
        model = AnalyticsCarrierReports
        fields = [
            'id', 'carrier', 'report_date', 'reports_count',
            'last_reported_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnalyticsStatusBreakdownSerializer(serializers.ModelSerializer):
    """Serializer para desglose por estado."""
    class Meta:
        model = AnalyticsStatusBreakdown
        fields = [
            'id', 'date', 'status', 'orders_count', 'total_value',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnalyticsHistoricalSerializer(serializers.Serializer):
    """Serializer para series temporales históricas."""
    date = serializers.DateField()
    total_orders = serializers.IntegerField()
    total_guides = serializers.IntegerField()
    products_sold = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    delivered_count = serializers.IntegerField()
    returns_count = serializers.IntegerField()
    cancelled_count = serializers.IntegerField()
    delivery_effectiveness_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    global_returns_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    net_profit_real = serializers.DecimalField(max_digits=12, decimal_places=2)


class AnalyticsCarrierComparisonSerializer(serializers.Serializer):
    """Serializer para comparativa de transportadoras."""
    carrier = serializers.CharField()
    approved = serializers.IntegerField()
    delivered = serializers.IntegerField()
    returns = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    sales_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    effectiveness_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
