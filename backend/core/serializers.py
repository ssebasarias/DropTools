# -*- coding: utf-8 -*-
"""
Django REST Framework Serializers
Serialización estandarizada de modelos para respuestas API
"""
from rest_framework import serializers
from .models import (
    Product, 
    Supplier, 
    UniqueProductCluster, 
    Category,
    ProductClusterMembership,
    ProductEmbedding
)


class SupplierSerializer(serializers.ModelSerializer):
    """Serializer para proveedores"""
    class Meta:
        model = Supplier
        fields = ['supplier_id', 'name', 'store_name', 'plan_name', 'is_verified']


class CategorySerializer(serializers.ModelSerializer):
    """Serializer para categorías"""
    class Meta:
        model = Category
        fields = ['id', 'name']


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer para productos
    Incluye información de proveedor embebido
    """
    supplier = SupplierSerializer(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'product_id',
            'sku',
            'title',
            'description',
            'sale_price',
            'suggested_price',
            'product_type',
            'url_image_s3',
            'is_active',
            'supplier',
            'created_at',
            'updated_at'
        ]


class ProductLightSerializer(serializers.ModelSerializer):
    """
    Versión ligera del ProductSerializer
    Para listados donde no se necesitan todos los campos
    """
    class Meta:
        model = Product
        fields = [
            'product_id',
            'title',
            'sale_price',
            'url_image_s3',
            'product_type'
        ]


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
            'id',
            'product',
            'cluster',
            'similarity_score',
            'joined_at'
        ]


class ProductEmbeddingSerializer(serializers.ModelSerializer):
    """
    Serializer para embeddings de productos
    Solo metadatos, no el vector completo (muy pesado)
    """
    class Meta:
        model = ProductEmbedding
        fields = [
            'product_id',
            'has_visual_embedding',
            'has_text_embedding',
            'embedding_model',
            'created_at'
        ]
    
    # Campos calculados para indicar presencia de embeddings
    has_visual_embedding = serializers.SerializerMethodField()
    has_text_embedding = serializers.SerializerMethodField()
    
    def get_has_visual_embedding(self, obj):
        return obj.embedding_visual is not None
    
    def get_has_text_embedding(self, obj):
        return obj.embedding_text is not None


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
