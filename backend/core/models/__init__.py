"""
Todos los modelos exportados desde módulos específicos.
Mantiene compatibilidad: from core.models import User, Product, etc.
"""

# Base constants
from .base import EMBED_DIM, EMBED_NORMALIZE

# Warehouse & Supplier
from .warehouse import Warehouse, Supplier

# Products
from .product import (
    Product,
    ProductCategory,
    ProductStockLog,
    ProductEmbedding,
)

# Categories
from .category import (
    Category,
    MarketplaceFeedback,
    FutureEvent,
)

# Clustering
from .clustering import (
    UniqueProductCluster,
    ProductClusterMembership,
    ConceptWeights,
    ClusterConfig,
    ClusterDecisionLog,
    AIFeedback,
)

# Market Intelligence
from .market_intelligence import (
    MarketIntelligenceLog,
    DomainReputation,
    MarketAnalysisReport,
    CompetitorFinding,
)

# User
from .user import User
from .auth_token import AuthToken

# Orders
from .orders import (
    OrderReport,
    WorkflowProgress,
    ReportBatch,
    RawOrderSnapshot,
    OrderMovementReport,
)

# Reporter Slots
from .reporter_slots import (
    ReporterSlotConfig,
    ReporterHourSlot,
    ReporterReservation,
    ReporterRun,
    ReporterRange,
    ReporterRunUser,
    reporter_reservation_weight_from_orders,
    assign_best_available_slot,
)

# Proxy
from .proxy import (
    ProxyIP,
    UserProxyAssignment,
)

# Analytics
from .analytics import (
    AnalyticsDailySnapshot,
    AnalyticsCarrierDaily,
    AnalyticsProductDaily,
    AnalyticsCarrierReports,
    AnalyticsStatusBreakdown,
)

__all__ = [
    # Constants
    'EMBED_DIM',
    'EMBED_NORMALIZE',
    # Warehouse
    'Warehouse',
    'Supplier',
    # Products
    'Product',
    'ProductCategory',
    'ProductStockLog',
    'ProductEmbedding',
    # Categories
    'Category',
    'MarketplaceFeedback',
    'FutureEvent',
    # Clustering
    'UniqueProductCluster',
    'ProductClusterMembership',
    'ConceptWeights',
    'ClusterConfig',
    'ClusterDecisionLog',
    'AIFeedback',
    # Market Intelligence
    'MarketIntelligenceLog',
    'DomainReputation',
    'MarketAnalysisReport',
    'CompetitorFinding',
    # User
    'User',
    'AuthToken',
    # Orders
    'OrderReport',
    'WorkflowProgress',
    'ReportBatch',
    'RawOrderSnapshot',
    'OrderMovementReport',
    # Reporter Slots
    'ReporterSlotConfig',
    'ReporterHourSlot',
    'ReporterReservation',
    'ReporterRun',
    'ReporterRange',
    'ReporterRunUser',
    'reporter_reservation_weight_from_orders',
    'assign_best_available_slot',
    # Proxy
    'ProxyIP',
    'UserProxyAssignment',
    # Analytics
    'AnalyticsDailySnapshot',
    'AnalyticsCarrierDaily',
    'AnalyticsProductDaily',
    'AnalyticsCarrierReports',
    'AnalyticsStatusBreakdown',
]
