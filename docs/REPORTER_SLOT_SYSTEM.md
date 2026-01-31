# Sistema de Reportes por Slot (Reservas por Hora)

## Resumen

El reporter deja de ejecutarse manualmente ("Iniciar a reportar") y pasa a un modelo de **reservas por hora**: cada hora del día es un slot con capacidad máxima de usuarios. A la hora programada, el scheduler (Celery Beat) dispara la ejecución para todos los usuarios con reserva en esa hora.

- **Límite global:** `MAX_ACTIVE_SELENIUM = 6` (configurable). Nunca más de 6 procesos Selenium simultáneos.
- **Procesamiento por rangos:** Las órdenes pendientes de cada usuario se dividen en rangos (ej. 1-100, 101-200). Cada rango es una tarea Celery independiente; los workers toman rangos libres (work stealing).
- **Redis:** Semáforo global (máx. 6 slots) y lock por rango para evitar doble procesamiento.

## Configuración

- **Settings / env:** `MAX_ACTIVE_SELENIUM`, `REPORTER_ESTIMATED_PENDING_FACTOR` (0.08), `REPORTER_RANGE_SIZE` (100), `REPORTER_SELENIUM_SEMAPHORE_TTL` (3300 s).
- **DB:** `ReporterSlotConfig` (singleton), `ReporterHourSlot` (24 filas, hour 0-23, max_users), `ReporterReservation`, `ReporterRun`, `ReporterRange`, `ReporterRunUser`.

## Flujo

1. **Celery Beat** (cada hora en punto): ejecuta `process_slot_task(slot_time)`.
2. **process_slot_task:** Crea `ReporterRun` para esa hora, lista usuarios con `ReporterReservation` en ese slot, crea `ReporterRunUser` por usuario y encola `download_compare_task(user_id, run_id)`.
3. **download_compare_task:** Adquiere slot del semáforo Redis, ejecuta Download + Compare (UnifiedReporter.run_download_compare_only()), libera slot, crea rangos en BD y encola `report_range_task(run_id, user_id, range_start, range_end)` por cada rango.
4. **report_range_task:** Adquiere slot del semáforo, obtiene lock Redis del rango, ejecuta Reporter solo para ese rango (UnifiedReporter.run_report_orders_only()), actualiza ReporterRange y ReporterRunUser.ranges_completed, libera lock y slot.

## Reintentos y TTLs

- **download_compare_task:** `max_retries=5`, `default_retry_delay=120` s. Semáforo: `acquire(timeout_seconds=3300)`.
- **report_range_task:** `max_retries=2`, `default_retry_delay=60` s. Lock por rango: TTL 50 min (`RANGE_LOCK_TTL`).
- Si un worker muere sin liberar el semáforo, el contador Redis puede quedar +1 hasta reinicio o limpieza manual (`selenium_semaphore.reset_for_testing()` solo para pruebas).

## API

- `GET /api/reporter/slots/` — Lista horas con capacidad (max_users, current_users, available).
- `GET /api/reporter/reservations/` — Reserva del usuario actual (o null).
- `POST /api/reporter/reservations/` — Crear reserva (slot_id, monthly_orders_estimate).
- `DELETE /api/reporter/reservations/` — Cancelar reserva.
- `GET /api/reporter/runs/` — Runs recientes del usuario.
- `GET /api/reporter/runs/<run_id>/progress/` — Progreso detallado de una run (por usuario).

## Migraciones

- `0007_reporter_slot_models` — Crea tablas y añade `User.monthly_orders_estimate`.
- `0008_reporter_slot_initial_data` — Inserta `ReporterSlotConfig` (1 fila) y 24 `ReporterHourSlot`.

## Pruebas / Disparo manual

Para ejecutar el slot sin esperar a Celery Beat:

- **Comando de gestión (recomendado):**
  ```bash
  # Hora actual redondeada
  python manage.py trigger_slot_task

  # Hora específica (0-23) de hoy
  python manage.py trigger_slot_task --hour=10
  ```
  Con Docker: `docker compose exec backend python manage.py trigger_slot_task --hour=10`

- **Desde Django shell:**
  ```python
  from core.tasks import process_slot_task
  from django.utils import timezone
  t = timezone.now().replace(minute=0, second=0, microsecond=0)
  process_slot_task.delay(t.isoformat())
  # O para una hora concreta (ej. 10:00 de hoy):
  # t = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
  # process_slot_task.delay(t.isoformat())
  ```

**Monitoreo:** `docker compose logs -f celery_worker`; Flower en `http://localhost:5555`. Script con filtro: `scripts\monitor_reporter_workers.ps1` (opcional: `-Filter "download_compare|report_range|user_id|run_id"`).

## Despliegue

- Ejecutar Celery Beat además del worker: `celery -A dahell_backend beat -l info` (o incluir beat en el mismo proceso según tu setup).
- Asegurar que Redis esté disponible y que `CELERY_BROKER_URL` apunte al mismo Redis usado por el semáforo.
