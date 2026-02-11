"""
Todos los serializers exportados desde módulos específicos.
Mantiene compatibilidad: from core.serializers import ProductSerializer, etc.
"""

# Product serializers
from .product import (
    ProductSerializer,
    ProductLightSerializer,
    SupplierSerializer,
    CategorySerializer,
)

# Cluster serializers
from .cluster import (
    ClusterSerializer,
    ClusterMembershipSerializer,
    ProductEmbeddingSerializer,
    GoldMineProductSerializer,
    DashboardTacticalOpportunitySerializer,
)

# Auth serializers
from .auth import GoogleAuthSerializer

# Reporter serializers
from .reporter import (
    ReporterSlotSerializer,
    ReporterReservationSerializer,
    ReporterRunSerializer,
    ReporterRunProgressSerializer,
)

# Analytics serializers
from .analytics import (
    AnalyticsDailySnapshotSerializer,
    AnalyticsCarrierDailySerializer,
    AnalyticsProductDailySerializer,
    AnalyticsCarrierReportsSerializer,
    AnalyticsStatusBreakdownSerializer,
    AnalyticsHistoricalSerializer,
    AnalyticsCarrierComparisonSerializer,
)

__all__ = [
    # Product
    'ProductSerializer',
    'ProductLightSerializer',
    'SupplierSerializer',
    'CategorySerializer',
    # Cluster
    'ClusterSerializer',
    'ClusterMembershipSerializer',
    'ProductEmbeddingSerializer',
    'GoldMineProductSerializer',
    'DashboardTacticalOpportunitySerializer',
    # Auth
    'GoogleAuthSerializer',
    # Reporter
    'ReporterSlotSerializer',
    'ReporterReservationSerializer',
    'ReporterRunSerializer',
    'ReporterRunProgressSerializer',
    # Analytics
    'AnalyticsDailySnapshotSerializer',
    'AnalyticsCarrierDailySerializer',
    'AnalyticsProductDailySerializer',
    'AnalyticsCarrierReportsSerializer',
    'AnalyticsStatusBreakdownSerializer',
    'AnalyticsHistoricalSerializer',
    'AnalyticsCarrierComparisonSerializer',
]
