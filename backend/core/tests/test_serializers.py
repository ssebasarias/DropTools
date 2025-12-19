# -*- coding: utf-8 -*-
"""
Serializer Tests
Tests básicos para los serializers
"""
from django.test import TestCase
from core.models import Product, Supplier
from core.serializers import ProductSerializer, SupplierSerializer


class SupplierSerializerTest(TestCase):
    """Tests para SupplierSerializer"""
    
    def test_serialization(self):
        """Test de serialización de supplier"""
        supplier = Supplier.objects.create(
            supplier_id=888,
            name="Test Supplier"
        )
        
        serializer = SupplierSerializer(supplier)
        data = serializer.data
        
        self.assertEqual(data['supplier_id'], 888)
        self.assertEqual(data['name'], "Test Supplier")


class ProductSerializerTest(TestCase):
    """Tests para ProductSerializer"""
    
    def test_serialization(self):
        """Test de serialización de producto"""
        product = Product.objects.create(
            product_id=77777,
            title="Serializer Test Product",
            sale_price=30000
        )
        
        serializer = ProductSerializer(product)
        data = serializer.data
        
        self.assertEqual(data['product_id'], 77777)
        self.assertEqual(data['title'], "Serializer Test Product")
        self.assertEqual(float(data['sale_price']), 30000)
