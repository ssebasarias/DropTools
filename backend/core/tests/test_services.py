# -*- coding: utf-8 -*-
"""
Service Tests
Tests básicos para la capa de servicios
"""
from django.test import TestCase
from core.models import Product, UniqueProductCluster
from core.services import GoldMineService, DashboardService


class GoldMineServiceTest(TestCase):
    """Tests para GoldMineService"""
    
    def setUp(self):
        # Crear producto de prueba
        self.product = Product.objects.create(
            product_id=55555,
            title="Service Test Product"
        )
        
        # Crear cluster
        self.cluster = UniqueProductCluster.objects.create(
            representative_product=self.product,
            total_competitors=3,
            average_price=25000
        )
    
    def test_get_distribution_stats(self):
        """Test de estadísticas de distribución"""
        stats = GoldMineService.get_distribution_stats()
        
        self.assertIn('low', stats)
        self.assertIn('medium', stats)
        self.assertIn('high', stats)
        self.assertIsInstance(stats['low'], int)


class DashboardServiceTest(TestCase):
    """Tests para DashboardService"""
    
    def test_get_general_stats(self):
        """Test de estadísticas generales"""
        stats = DashboardService.get_general_stats()
        
        self.assertIn('total_unique_products', stats)
        self.assertIn('competition_distribution', stats)
        self.assertIsInstance(stats['total_unique_products'], int)
