# -*- coding: utf-8 -*-
"""
Views Module - Dahell Backend
Imports centralizados de todas las vistas
"""

# Importar todas las views desde el archivo views.py
from ..views import (
    DashboardStatsView,
    GoldMineView,
    GoldMineStatsView,
    ClusterLabStatsView,
    ClusterAuditView,
    ClusterOrphansView,
    CategoriesView,
    SystemLogsView,
    ClusterFeedbackView,
    ContainerStatsView,
    ContainerControlView,
)

__all__ = [
    'DashboardStatsView',
    'GoldMineView',
    'GoldMineStatsView',
    'ClusterLabStatsView',
    'ClusterAuditView',
    'ClusterOrphansView',
    'CategoriesView',
    'SystemLogsView',
    'ClusterFeedbackView',
    'ContainerStatsView',
    'ContainerControlView',
]
