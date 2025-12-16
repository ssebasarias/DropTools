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
    ContainerStatsView,
    ContainerControlView
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('api/gold-mine/', GoldMineView.as_view(), name='gold-mine'),
    path('api/gold-mine/stats/', GoldMineStatsView.as_view(), name='gold-mine-stats'),
    path('api/categories/', CategoriesView.as_view(), name='categories'),
    path('api/system-logs/', SystemLogsView.as_view(), name='system-logs'),
    
    # Cluster Lab APIs
    path('api/cluster-lab/audit-logs/', ClusterAuditView.as_view(), name='cluster-audit'),
    path('api/cluster-lab/orphans/', ClusterOrphansView.as_view(), name='cluster-orphans'),
    path('api/cluster-lab/feedback/', ClusterFeedbackView.as_view(), name='cluster-feedback'),
    
    # System Control
    path('api/control/stats/', ContainerStatsView.as_view(), name='container-stats'),
    path('api/control/container/<str:service>/<str:action>/', ContainerControlView.as_view(), name='container-control'),
]
