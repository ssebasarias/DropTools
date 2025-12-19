# -*- coding: utf-8 -*-
"""
Model Tests
Tests básicos para los modelos principales
"""
from django.test import TestCase
from core.models import Product, Supplier, UniqueProductCluster, Category


class SupplierModelTest(TestCase):
    """Tests para el modelo Supplier"""
    
    def setUp(self):
        self.supplier = Supplier.objects.create(
            supplier_id=999,
            name="Test Supplier",
            store_name="Test Store",
            is_verified=True
        )
    
    def test_supplier_creation(self):
        """Test de creación de proveedor"""
        self.assertEqual(self.supplier.name, "Test Supplier")
        self.assertTrue(self.supplier.is_verified)


class ProductModelTest(TestCase):
    """Tests para el modelo Product"""
    
    def setUp(self):
        self.product = Product.objects.create(
            product_id=12345,
            title="Test Product",
            sale_price=50000,
            is_active=True
        )
    
    def test_product_creation(self):
        """Test de creación de producto"""
        self.assertEqual(self.product.title, "Test Product")
        self.assertTrue(self.product.is_active)
