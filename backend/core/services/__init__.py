# -*- coding: utf-8 -*-
"""
Services Module
Business logic layer separado de las views
"""

from .gold_mine_service import GoldMineService
from .cluster_service import ClusterService
from .dashboard_service import DashboardService
from .proxy_allocator_service import (
    assign_proxy_to_user,
    get_proxy_config_for_user,
    update_last_used,
)
from .proxy_health_checker import check_proxy_reachable, check_proxy_by_id

__all__ = [
    'GoldMineService',
    'ClusterService',
    'DashboardService',
    'assign_proxy_to_user',
    'get_proxy_config_for_user',
    'update_last_used',
    'check_proxy_reachable',
    'check_proxy_by_id',
]
