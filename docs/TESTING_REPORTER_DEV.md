# Testing Reporter en DEV (proxy, balance pesos, monitor)

Resumen del plan de testing avanzado en entorno de desarrollo. Todo aislado para DEV; no modifica el reporter ni el scheduler en producción.

## Configuración de proxy (DEV)

- **Archivo:** `backend/proxy_dev_config.json` (no subir a Git; está en `.gitignore`).
- **Ejemplo:** Copiar `backend/proxy_dev_config.example.json` a `proxy_dev_config.json` y rellenar.

Configuración actual (ejemplo para tu entorno):

- **Host:** 198.143.22.45  
- **Port:** 12323  
- **Username:** (definido en el JSON, no loguear)  
- **Password:** (definido en el JSON, no loguear)  
- **user_ids:** [2, 3, 4] — usuarios que usan este proxy en DEV  

Solo se usa cuando `DROPTOOLS_ENV=development` y el archivo existe. En producción se ignora.

## Comandos y scripts

| Acción | Comando |
|--------|--------|
| Ver IP real usada por Selenium con proxy | `python manage.py verify_proxy_ip` (desde `backend/`) |
| Disparar slot manual (encolar) | `python manage.py trigger_slot_task --hour=10` |
| Disparar slot **síncrono** (en este proceso) | `python manage.py trigger_slot_task --hour=10 --sync` |
| Disparar slot **con capacidad por peso** (DEV) | `python manage.py trigger_slot_task --hour=10 --dev` |
| Monitor en tiempo real | `python manage.py monitor_workers` (opción `--interval 5`, `--once` para una sola salida) |

## Balance de pesos (DEV)

- **Tarea:** `process_slot_task_dev` (solo se usa con `trigger_slot_task --dev`).
- Respeta `slot.capacity_points`: solo encola `download_compare_task` para usuarios que caben (suma de `calculated_weight` ≤ capacidad).
- Los que no caben quedan `DC_PENDING`; al liberarse peso (al terminar Download+Compare o al completar todos los rangos de un usuario), se encola el siguiente que quepa (`enqueue_next_pending_for_run`).
- Runs creadas por `process_slot_task_dev` se marcan en Redis (`reporter:run:capacity_aware:{run_id}`) para que `download_compare_task` y `report_range_task` llamen a `enqueue_next_pending_for_run` al terminar.

## Monitor

- Muestra: runs en ejecución (últimas 24 h), por run: user_id, peso, acción (descargando/comparando, reportando rangos X/Y, pendiente por capacidad), proxy (host:port), estado del semáforo Selenium (ocupados / máx).

## Seguridad

- No se loguean contraseñas (proxy ni Dropi).
- Credenciales de proxy solo en `proxy_dev_config.json` (gitignored) o variables de entorno.
- No hardcodear credenciales en código.
