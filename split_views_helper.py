"""
Script para dividir views.py en módulos separados por dominio
"""

# Lectura del archivo views.py
with open('backend/core/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Definir los rangos de líneas para cada módulo (basado en el outline)
modules = {
    'dashboard.py': {
        'imports': "from rest_framework.views import APIView\nfrom rest_framework.response import Response\nfrom django.db.models import Avg, Count, Q\nfrom ..models import Product, UniqueProductCluster, ProductEmbedding, Warehouse, Category, ProductClusterMembership\nfrom datetime import datetime, timedelta\n\n",
        'classes': ['DashboardStatsView']
    },
    'gold_mine.py': {
        'imports': "from rest_framework.views import APIView\nfrom rest_framework.response import Response\nfrom django.db.models import Q\nfrom django.db import connection\nfrom ..models import UniqueProductCluster, ProductEmbedding\nfrom ..ai_utils import get_image_embedding\n\n",
        'classes': ['GoldMineView', 'GoldMineStatsView']  
    },
    'cluster_lab.py': {
        'imports': "from rest_framework.views import APIView\nfrom rest_framework.response import Response\nfrom django.db.models import Count\nfrom django.utils import timezone\nfrom ..models import UniqueProductCluster, ProductClusterMembership, AIFeedback, ClusterDecisionLog, Product, Category\nimport json\n\n",
        'classes': ['ClusterLabStatsView', 'ClusterAuditView', 'ClusterOrphansView', 'ClusterFeedbackView', 'CategoriesView']
    },
    'system.py': {
        'imports': "from rest_framework.views import APIView\nfrom rest_framework.response import Response\nfrom ..docker_utils import get_container_stats, control_container\nimport pathlib\n\n",
        'classes': ['SystemLogsView', 'ContainerStatsView', 'ContainerControlView']
    }
}

print("Dividiendo views.py en módulos...")
print(f"Total clases a migrar: {sum(len(m['classes']) for m in modules.values())}")
