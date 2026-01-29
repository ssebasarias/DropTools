"""
URL configuration for dahell_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from core.views import (
    DashboardStatsView,
    GoldMineView,
    GoldMineStatsView,
    CategoriesView,
    SystemLogsView,
    ClusterAuditView,
    ClusterOrphansView,
    ClusterFeedbackView,
    ClusterLabStatsView,
    ContainerStatsView,
    ContainerControlView,
    ClusterOrphanActionView,
    ReporterConfigView,
    ReporterStartView,
    ReporterStatusView,
    ReporterListView,
    ClientDashboardAnalyticsView,
    AuthLoginView,
    AuthRegisterView,
    AuthMeView,
    DropiAccountsView,
    DropiAccountSetDefaultView,
    AdminUsersView,
    AdminSetUserSubscriptionView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth
    path('api/auth/login/', AuthLoginView.as_view(), name='auth-login'),
    path('api/auth/register/', AuthRegisterView.as_view(), name='auth-register'),
    path('api/auth/me/', AuthMeView.as_view(), name='auth-me'),
    # Dropi accounts
    path('api/dropi/accounts/', DropiAccountsView.as_view(), name='dropi-accounts'),
    path('api/dropi/accounts/<int:account_id>/default/', DropiAccountSetDefaultView.as_view(), name='dropi-account-default'),
    path('api/dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('api/gold-mine/', GoldMineView.as_view(), name='gold-mine'),
    path('api/gold-mine/stats/', GoldMineStatsView.as_view(), name='gold-mine-stats'),
    path('api/categories/', CategoriesView.as_view(), name='categories'),
    path('api/system-logs/', SystemLogsView.as_view(), name='system-logs'),
    
    # Cluster Lab APIs
    path('api/cluster-lab/stats/', ClusterLabStatsView.as_view(), name='cluster-stats'),
    path('api/cluster-lab/audit-logs/', ClusterAuditView.as_view(), name='cluster-audit'),
    path('api/cluster-lab/orphans/', ClusterOrphansView.as_view(), name='cluster-orphans'),
    path('api/cluster-lab/orphans/action/', ClusterOrphanActionView.as_view(), name='cluster-orphans-action'),
    path('api/cluster-lab/feedback/', ClusterFeedbackView.as_view(), name='cluster-feedback'),
    
    # System Control
    path('api/control/stats/', ContainerStatsView.as_view(), name='container-stats'),
    path('api/control/container/<str:service>/<str:action>/', ContainerControlView.as_view(), name='container-control'),
    
    # Reporter Configuration
    path('api/reporter/config/', ReporterConfigView.as_view(), name='reporter-config'),
    path('api/reporter/start/', ReporterStartView.as_view(), name='reporter-start'),
    path('api/reporter/status/', ReporterStatusView.as_view(), name='reporter-status'),
    path('api/reporter/list/', ReporterListView.as_view(), name='reporter-list'),
    path('api/user/dashboard/analytics/', ClientDashboardAnalyticsView.as_view(), name='client-dashboard-analytics'),

    # Admin (no payments): manage users & subscriptions
    path('api/admin/users/', AdminUsersView.as_view(), name='admin-users'),
    path('api/admin/users/<int:user_id>/subscription/', AdminSetUserSubscriptionView.as_view(), name='admin-user-subscription'),
]
