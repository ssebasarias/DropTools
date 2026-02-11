# -*- coding: utf-8 -*-
"""
Serializers para clusters y productos relacionados
"""
from rest_framework import serializers
from ..models import UniqueProductCluster, ProductClusterMembership, ProductEmbedding
from .product import ProductLightSerializer, SupplierSerializer


class ClusterSerializer(serializers.ModelSerializer):
    """
    Serializer para clusters de productos únicos
    Incluye producto representante embebido
    """
    representative = ProductLightSerializer(source='representative_product', read_only=True)
    representative_supplier = serializers.SerializerMethodField()
    
    class Meta:
        model = UniqueProductCluster
        fields = [
            'cluster_id',
            'representative',
            'representative_supplier',
            'total_competitors',
            'average_price',
            'saturation_score',
            'created_at',
            'updated_at'
        ]
    
    def get_representative_supplier(self, obj):
        """Obtener información del proveedor del representante"""
        if obj.representative_product and obj.representative_product.supplier:
            return SupplierSerializer(obj.representative_product.supplier).data
        return None


class ClusterMembershipSerializer(serializers.ModelSerializer):
    """Serializer para membresías de productos en clusters"""
    product = ProductLightSerializer(read_only=True)
    cluster = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = ProductClusterMembership
        fields = [
            'product',
            'cluster',
            'match_confidence',
            'match_method'
        ]


class ProductEmbeddingSerializer(serializers.ModelSerializer):
    """
    Serializer para embeddings de productos
    Solo metadatos, no el vector completo (muy pesado).
    El modelo solo tiene embedding_visual y processed_at.
    """
    has_visual_embedding = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductEmbedding
        fields = [
            'product_id',
            'has_visual_embedding',
            'processed_at'
        ]
    
    def get_has_visual_embedding(self, obj):
        return obj.embedding_visual is not None


# Serializers especializados para diferentes views

class GoldMineProductSerializer(serializers.Serializer):
    """
    Serializer especializado para Gold Mine
    No vinculado a modelo (Serializer genérico)
    """
    id = serializers.IntegerField()
    title = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    image = serializers.URLField(allow_null=True)
    competitors = serializers.IntegerField()
    profit_margin = serializers.FloatField(allow_null=True)
    supplier = serializers.CharField()
    cluster_id = serializers.IntegerField(allow_null=True)
    badge = serializers.CharField(allow_null=True)


class DashboardTacticalOpportunitySerializer(serializers.Serializer):
    """Serializer para oportunidades tácticas del dashboard"""
    id = serializers.IntegerField()
    title = serializers.CharField()
    image = serializers.URLField(allow_null=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    margin = serializers.FloatField(allow_null=True)
    competitors = serializers.IntegerField()
    supplier = serializers.CharField()
    badge = serializers.CharField()
