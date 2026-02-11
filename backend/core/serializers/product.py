# -*- coding: utf-8 -*-
"""
Serializers para productos, proveedores y categorías
"""
from rest_framework import serializers
from ..models import Product, Supplier, Category


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
