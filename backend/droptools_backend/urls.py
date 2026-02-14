"""
URL configuration for droptools_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path
from core.views import (
    HealthView,
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
    ReporterEnvView,
    ReporterStopView,
    ReporterListView,
    ReporterSlotsView,
    ReporterReservationsView,
    ReporterRunsView,
    ReporterRunProgressView,
    ClientDashboardAnalyticsView,
    AnalyticsHistoricalView,
    AnalyticsCarrierComparisonView,
    AuthLoginView,
    GoogleAuthView,
    AuthRegisterView,
    AuthMeView,
    VerifyEmailView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    DropiAccountsView,
    DropiAccountSetDefaultView,
    AdminUsersView,
    AdminSetUserSubscriptionView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # Health (Docker / load balancers)
    path('api/health/', HealthView.as_view(), name='api-health'),
    # Auth
    path('api/auth/login/', AuthLoginView.as_view(), name='auth-login'),
    path('api/auth/google/', GoogleAuthView.as_view(), name='google-auth'),
    path('api/auth/register/', AuthRegisterView.as_view(), name='auth-register'),
    path('api/auth/verify-email/', VerifyEmailView.as_view(), name='auth-verify-email'),
    path('api/auth/password-reset/request/', PasswordResetRequestView.as_view(), name='auth-password-reset-request'),
    path('api/auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),
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
    path('api/reporter/env/', ReporterEnvView.as_view(), name='reporter-env'),
    path('api/reporter/stop/', ReporterStopView.as_view(), name='reporter-stop'),
    path('api/reporter/list/', ReporterListView.as_view(), name='reporter-list'),
    path('api/reporter/slots/', ReporterSlotsView.as_view(), name='reporter-slots'),
    path('api/reporter/reservations/', ReporterReservationsView.as_view(), name='reporter-reservations'),
    path('api/reporter/runs/', ReporterRunsView.as_view(), name='reporter-runs'),
    path('api/reporter/runs/<int:run_id>/progress/', ReporterRunProgressView.as_view(), name='reporter-run-progress'),
    path('api/user/dashboard/analytics/', ClientDashboardAnalyticsView.as_view(), name='client-dashboard-analytics'),
    path('api/user/analytics/historical/', AnalyticsHistoricalView.as_view(), name='analytics-historical'),
    path('api/user/analytics/carrier-comparison/', AnalyticsCarrierComparisonView.as_view(), name='analytics-carrier-comparison'),

    # Admin (no payments): manage users & subscriptions
    path('api/admin/users/', AdminUsersView.as_view(), name='admin-users'),
    path('api/admin/users/<int:user_id>/subscription/', AdminSetUserSubscriptionView.as_view(), name='admin-user-subscription'),
]
