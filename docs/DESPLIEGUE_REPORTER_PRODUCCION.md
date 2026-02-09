# Despliegue Reporter a Producción — Plan Controlado

Migración a producción de la lógica de **reservas por peso**, **capacidad por slot**, **validación de horas** y **UI rediseñada**, sin alterar Celery, rangos ni semáforos Redis.

---

## Estado de implementación (Fases 1–5)

Las fases 1–5 ya están implementadas en el código:

| Fase | Contenido | Estado |
|------|-----------|--------|
| **1** | Migraciones seguras (calculated_weight, capacity_points, slot_capacity, reporter_hour_start/end) | Hecho — migración `0009_reporter_weight_and_capacity` |
| **2** | Validación por suma de pesos en ReporterReservationsView | Hecho |
| **3** | Endpoints slots: used_points, capacity_points, available, hour_label; filtro por ventana reporter | Hecho |
| **4** | Frontend: formulario sin reserva, grilla horas con candado; paneles con reserva; sin botón manual | Hecho |
| **5** | Mensajes de progreso amigables en unified_reporter | Hecho |

Este documento se centra en **Fase 6 — Activación controlada en producción** y en **rollback**.

---

## Reglas a respetar

- **NO** romper datos existentes.
- **NO** eliminar tablas ni columnas (solo extender modelos).
- Mantener compatibilidad hacia atrás.
- Permitir rollback sencillo (sin revertir migraciones).
- **NO** tocar lógica de workers ni semáforos Redis.
- Desplegar en fases, no todo a la vez.

---

## Fase 6 — Activación controlada en producción

### 6.1 Orden recomendado

1. **Migraciones** (solo esquema y backfill).
2. **Backend** (validación por peso y endpoints de slots ya activos).
3. **Frontend** (opcional: feature flag para pantalla nueva).
4. **Monitoreo** 24h.
5. **Activación completa** del frontend (si se usó flag).

### 6.2 Paso 1 — Base de datos en producción

**Antes:** Backup de la base de datos.

```bash
# Ejemplo PostgreSQL
pg_dump -h <host> -U <user> -d droptools_db > backup_antes_0009_$(date +%Y%m%d).sql
```

**Aplicar migraciones solo de core:**

```bash
# Con venv activado y variables de producción
python backend/manage.py migrate core --noinput
python backend/manage.py check
```

**Verificar:**

- Tablas `reporter_reservations`, `reporter_hour_slots`, `reporter_slot_config` existen.
- Columnas nuevas presentes: `calculated_weight`, `capacity_points`, `slot_capacity`, `reporter_hour_start`, `reporter_hour_end`.
- No se han eliminado columnas (p. ej. `max_users` sigue en `reporter_hour_slots`).

**Rollback de migraciones:** No recomendado. Las migraciones solo añaden columnas y datos por defecto; revertir puede ser más riesgoso que dejar el esquema extendido.

### 6.3 Paso 2 — Backend en producción

- Desplegar código actual (views, serializers, modelos con peso y capacidad).
- Reiniciar **solo** el servicio backend (API). **No** reiniciar workers aún si quieres retrasar el uso de `calculated_weight` en reservas nuevas; en cualquier caso, los workers no cambian de lógica (siguen usando `ReporterReservation.objects.filter(slot=slot)`).

**Comportamiento esperado:**

- `GET /api/reporter/slots/`: devuelve solo horas en ventana (ej. 6–17), con `used_points`, `capacity_points`, `available`.
- `POST /api/reporter/reservations/`: rechaza con 400 y mensaje "Hora llena por capacidad" cuando `used + new_weight > capacity`.

**Verificación rápida:**

```bash
# Tras login, comprobar slots (debe incluir used_points, capacity_points, available)
curl -H "Authorization: Token <token>" https://<api>/api/reporter/slots/
```

### 6.4 Paso 3 — Frontend (con o sin feature flag)

**Opción A — Sin feature flag (recomendado si ya probaste en staging):**

- Desplegar frontend actual.
- La pantalla de Reporter pasa a ser la nueva (formulario sin reserva / paneles con reserva, grilla por puntos, candado en horas llenas).

**Opción B — Con feature flag:**

- Añadir variable de entorno (ej. `VITE_REPORTER_NEW_UI=1` o leer desde API).
- En el frontend, si el flag está desactivado, mostrar la vista antigua (si aún existe) o la misma vista pero sin depender de `used_points`/`capacity_points` hasta activar el flag.
- Para activación gradual: activar flag para un subconjunto de usuarios o tras 24h de monitoreo.

En el código actual **no hay** feature flag; si se desea, se puede añadir un endpoint tipo `GET /api/reporter/config/` que devuelva `{ "use_weight_ui": true }` y leerlo en ReporterConfig.

### 6.5 Paso 4 — Monitoreo 24h

- **Logs backend:** errores 4xx/5xx en `POST /api/reporter/reservations/` y en `GET /api/reporter/slots/`.
- **Logs Celery:** mismos mensajes que antes; no debe haber más fallos por el cambio de reservas.
- **Base de datos:** reservas nuevas con `calculated_weight` coherente (1, 2 o 3) según `monthly_orders_estimate`.
- **Negocio:** ninguna hora con suma de pesos > 6 por slot; usuarios sin doble reserva.

### 6.6 Paso 5 — Activación completa

- Si usaste feature flag, ponerlo en “activado” para todos.
- Considerar eliminación futura de la vista antigua o del flag cuando todo esté estable.

---

## Fallback / Rollback

### Si algo falla en backend (validación o slots)

1. **No revertir migraciones.** Las columnas nuevas no rompen la lógica antigua si se dejan de usar.
2. **Rollback de código:** volver al commit anterior del backend que aún usaba `max_users` para validación y slots sin `used_points`.
3. En ese commit anterior:
   - ReporterReservationsView volvería a comparar `slot.reservations.count() >= slot.max_users`.
   - ReporterSlotsView volvería a devolver todos los slots sin filtrar por `reporter_hour_start`/`reporter_hour_end` y sin anotar `used_points`.
4. Desplegar ese commit y reiniciar backend.

### Si algo falla en frontend

1. Desplegar versión anterior del frontend (pantalla Reporter anterior).
2. Si usabas feature flag, desactivarlo para volver a la UI antigua.

### Si algo falla en base de datos

- Las migraciones aplicadas **solo añaden** columnas y datos por defecto; no eliminan nada.
- En caso de fallo grave de migración, restaurar desde el backup de la BD y no volver a ejecutar la migración hasta corregir el problema (p. ej. permisos, espacio).

### No tocar

- Workers Celery, tareas (process_slot_task, download_compare_task, report_range_task).
- Semáforos Redis.
- Lógica de rangos.

---

## Métricas de éxito

El sistema en producción debe:

- Mantener workers estables (sin nuevos errores atribuibles al cambio).
- No generar reportes duplicados (idempotencia igual que antes).
- No saturar horas (validación `used_weight + new_weight <= capacity`).
- Mostrar progreso claro al usuario (mensajes amigables en UI).
- Completar reportes dentro de la hora asignada (comportamiento de Celery sin cambios).

---

## Checklist pre-despliegue

- [ ] Backup de base de datos tomado.
- [ ] Migración `0009_reporter_weight_and_capacity` probada en staging/copia de producción.
- [ ] `python manage.py check` sin errores.
- [ ] Variables de entorno de producción correctas (DB, Redis, etc.).
- [ ] Plan de rollback de código (commit o tag conocido) definido.

---

## Checklist post-despliegue

- [ ] `GET /api/reporter/slots/` devuelve horas 6–17 (o la ventana configurada) con `used_points`, `capacity_points`, `available`.
- [ ] Nueva reserva con peso que llenaría el slot devuelve 400 "Hora llena por capacidad".
- [ ] Usuario con reserva ve paneles (cuenta, KPIs, progreso, tabla); usuario sin reserva ve formulario y grilla de horas.
- [ ] No aparece botón manual de ejecución del reporter.
- [ ] Logs de Celery sin errores nuevos en las tareas del reporter.

---

## Resumen de archivos tocados (para rollback de código)

- **Backend:** `core/models.py`, `core/views.py`, `core/serializers.py`, `core/reporter_bot/unified_reporter.py`, migración `core/migrations/0009_reporter_weight_and_capacity.py`.
- **Frontend:** `src/pages/user/ReporterConfig.jsx`, `src/services/api.js` (sin cambios de contrato que impidan usar backend antiguo).

Revertir esos archivos (o el commit que los contiene) y volver a desplegar restaura el comportamiento anterior de reservas y slots, sin necesidad de revertir migraciones.
