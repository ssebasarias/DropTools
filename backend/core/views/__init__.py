"""
Todas las vistas exportadas desde módulos específicos.
Mantiene compatibilidad: from core.views import DashboardStatsView, etc.
"""

# Auth views
from .auth import (
    AuthLoginView,
    GoogleAuthView,
    AuthRegisterView,
    AuthMeView,
)

# Admin views
from .admin import (
    AdminUsersView,
    AdminSetUserSubscriptionView,
)

# Dashboard views
from .dashboard import DashboardStatsView

# Gold Mine views
from .gold_mine import (
    GoldMineView,
    GoldMineStatsView,
)

# Cluster Lab views
from .cluster_lab import (
    ClusterLabStatsView,
    ClusterAuditView,
    ClusterOrphansView,
    ClusterOrphanActionView,
    ClusterFeedbackView,
)

# Categories views
from .categories import CategoriesView

# System views
from .system import (
    SystemLogsView,
    ContainerStatsView,
    ContainerControlView,
)

# Reporter views
from .reporter import (
    ReporterConfigView,
    ReporterStartView,
    ReporterEnvView,
    ReporterStopView,
    ReporterStatusView,
    ReporterListView,
)

# Reporter Slots views
from .reporter_slots import (
    ReporterSlotsView,
    ReporterReservationsView,
    ReporterRunsView,
    ReporterRunProgressView,
)

# Analytics views
from .analytics import (
    ClientDashboardAnalyticsView,
    AnalyticsHistoricalView,
    AnalyticsCarrierComparisonView,
)

# Dropi Accounts views
from .dropi_accounts import (
    DropiAccountsView,
    DropiAccountSetDefaultView,
)

__all__ = [
    # Auth
    'AuthLoginView',
    'GoogleAuthView',
    'AuthRegisterView',
    'AuthMeView',
    # Admin
    'AdminUsersView',
    'AdminSetUserSubscriptionView',
    # Dashboard
    'DashboardStatsView',
    # Gold Mine
    'GoldMineView',
    'GoldMineStatsView',
    # Cluster Lab
    'ClusterLabStatsView',
    'ClusterAuditView',
    'ClusterOrphansView',
    'ClusterOrphanActionView',
    'ClusterFeedbackView',
    # Categories
    'CategoriesView',
    # System
    'SystemLogsView',
    'ContainerStatsView',
    'ContainerControlView',
    # Reporter
    'ReporterConfigView',
    'ReporterStartView',
    'ReporterEnvView',
    'ReporterStopView',
    'ReporterStatusView',
    'ReporterListView',
    # Reporter Slots
    'ReporterSlotsView',
    'ReporterReservationsView',
    'ReporterRunsView',
    'ReporterRunProgressView',
    # Analytics
    'ClientDashboardAnalyticsView',
    'AnalyticsHistoricalView',
    'AnalyticsCarrierComparisonView',
    # Dropi Accounts
    'DropiAccountsView',
    'DropiAccountSetDefaultView',
]
