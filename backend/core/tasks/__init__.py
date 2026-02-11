"""
Todas las tareas exportadas desde módulos específicos.
Mantiene compatibilidad: from core.tasks import execute_workflow_task, etc.
"""

# Workflow tasks
from .workflow import (
    execute_workflow_task,
    execute_workflow_task_test,
    execute_multiple_workflows,
    test_celery_task,
)

# Reporter slots tasks
from .reporter_slots import (
    process_slot_task,
    process_slot_task_dev,
    download_compare_task,
    report_range_task,
    enqueue_next_pending_for_run,
    enqueue_next_range_priority_aware,
    _run_capacity_aware_key,
    _is_run_capacity_aware,
)

# Analytics tasks
from .analytics import calculate_daily_analytics

__all__ = [
    # Workflow
    'execute_workflow_task',
    'execute_workflow_task_test',
    'execute_multiple_workflows',
    'test_celery_task',
    # Reporter Slots
    'process_slot_task',
    'process_slot_task_dev',
    'download_compare_task',
    'report_range_task',
    'enqueue_next_pending_for_run',
    'enqueue_next_range_priority_aware',
    '_run_capacity_aware_key',
    '_is_run_capacity_aware',
    # Analytics
    'calculate_daily_analytics',
]
