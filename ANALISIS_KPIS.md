# Análisis y Solución: KPIs del Reporter no muestran información

## Problema Identificado

Los KPIs en el panel "Proceso en tiempo real" están mostrando guiones (—) en lugar de números porque no hay datos en las tablas correspondientes.

## Arquitectura del Sistema

### Flujo de Datos del Reporter

1. **Downloader** → Descarga reportes de Dropi y crea:
   - `ReportBatch` (lote de descarga)
   - `RawOrderSnapshot` (snapshot de cada orden)

2. **Comparer** → Compara 2 batches y detecta órdenes sin movimiento:
   - Requiere al menos 2 `ReportBatch` (hoy y ayer)
   - Crea `OrderMovementReport` para órdenes sin movimiento

3. **Reporter** → Reporta órdenes en Dropi y actualiza:
   - `OrderReport` con `status='reportado'` cuando se reporta exitosamente

### Fuentes de Datos de los KPIs

#### 1. Reportados Hoy
**Fuente**: `OrderReport` tabla
```python
OrderReport.objects.filter(
    user=user,
    status='reportado',
    updated_at__gte=today_start,
    updated_at__lt=today_end
).count()
```

**Cuándo se incrementa**: 
- Cuando el worker del reporter marca una orden como `status='reportado'`
- Se resetea a cero cada día (filtro por `updated_at` del día actual)

#### 2. Reportados Mes
**Fuente**: `OrderReport` tabla
```python
OrderReport.objects.filter(
    user=user,
    status='reportado',
    updated_at__gte=month_start
).count()
```

**Cuándo se incrementa**:
- Acumulativo durante todo el mes
- Se resetea a cero cada inicio de mes

#### 3. Órdenes Pendientes
**Fuente Principal**: `OrderReport` tabla
```python
OrderReport.objects.filter(user=user).exclude(status='reportado').count()
```

**Fuente Alternativa** (frontend también consulta): `OrderMovementReport`
```python
OrderMovementReport.objects.filter(
    batch=latest_batch,
    is_resolved=False
).count()
```

**Cuándo se actualiza**:
- **Durante el reporte**: Comienza con el total detectado por el comparer
- **Decrece en tiempo real**: Cada vez que un worker reporta una orden, se reduce en 1
- **Llega a cero**: Cuando todas las órdenes pendientes han sido reportadas

## Causas Posibles de KPIs Vacíos

### 1. El bot no ha ejecutado hoy
- No hay `ReportBatch` creados hoy
- No hay `OrderMovementReport` detectados
- No hay `OrderReport` con `status='reportado'`

### 2. El comparer no detectó órdenes sin movimiento
- Requiere al menos 2 batches (hoy y ayer)
- Si solo hay 1 batch, no puede comparar
- Si todas las órdenes tienen movimiento, no hay nada que reportar

### 3. El reporter no ha marcado órdenes como reportadas
- Puede haber `OrderMovementReport` pero no `OrderReport` con `status='reportado'`
- Esto indica que el paso 3 (reporter) no se ejecutó o falló

### 4. Problema de timezone
- Los filtros de fecha usan `timezone.localtime()` y `timezone.get_current_timezone()`
- Si hay desfase entre el timezone de la BD y el servidor, los conteos pueden ser incorrectos

## Solución Propuesta

### Paso 1: Verificar que el bot ejecutó hoy
```bash
python manage.py shell
```
```python
from core.models import ReportBatch, User
from django.utils import timezone

user = User.objects.first()
today = timezone.now().date()

# Verificar batches de hoy
batches_today = ReportBatch.objects.filter(
    user=user,
    created_at__date=today
)
print(f"Batches creados hoy: {batches_today.count()}")
for batch in batches_today:
    print(f"  - Batch {batch.id}: {batch.status}, {batch.created_at}")
```

### Paso 2: Verificar que el comparer detectó órdenes
```python
from core.models import OrderMovementReport

latest_batch = ReportBatch.objects.filter(user=user, status='SUCCESS').order_by('-created_at').first()
if latest_batch:
    pending = OrderMovementReport.objects.filter(
        batch=latest_batch,
        is_resolved=False
    ).count()
    print(f"Órdenes sin movimiento detectadas: {pending}")
```

### Paso 3: Verificar que el reporter marcó órdenes como reportadas
```python
from core.models import OrderReport
from datetime import datetime, time as dt_time, timedelta

now = timezone.localtime(timezone.now())
today = now.date()
tz = timezone.get_current_timezone()
today_start = tz.localize(datetime.combine(today, dt_time.min))
today_end = today_start + timedelta(days=1)

reported_today = OrderReport.objects.filter(
    user=user,
    status='reportado',
    updated_at__gte=today_start,
    updated_at__lt=today_end
).count()

print(f"Reportados hoy: {reported_today}")

# Ver todos los status
from django.db.models import Count
status_dist = OrderReport.objects.filter(user=user).values('status').annotate(count=Count('id'))
for item in status_dist:
    print(f"  - {item['status']}: {item['count']}")
```

### Paso 4: Verificar el progreso del último run
```python
from core.models import ReporterRun, ReporterRunUser

latest_run = ReporterRun.objects.filter(
    run_users__user=user
).order_by('-scheduled_at').first()

if latest_run:
    print(f"Último run: {latest_run.id}, status: {latest_run.status}")
    run_user = ReporterRunUser.objects.filter(run=latest_run, user=user).first()
    if run_user:
        print(f"  - Ranges completados: {run_user.ranges_completed}/{run_user.total_ranges}")
        print(f"  - Órdenes pendientes: {run_user.total_pending_orders}")
```

## Mejoras Recomendadas al Código

### 1. Agregar fallback en el frontend para mostrar "0" en lugar de "—"

En `ReporterConfig.jsx`, líneas 466-476, cambiar:
```javascript
{status != null ? (() => {
    const safeNum = (x) => (typeof x === 'number' && Number.isFinite(x) ? x : 0);
    const fromDb = safeNum(Number(status.total_reported));
    const fromRun = (lastRunProgress?.users?.length)
        ? (lastRunProgress.users || []).reduce((s, u) => s + safeNum(u.ranges_completed), 0)
        : 0;
    const msg = workflowProgress?.current_message || '';
    const reportandoMatch = msg.match(/Reportando\s+(\d+)\s*\/\s*\d+/);
    const fromMessage = reportandoMatch ? safeNum(parseInt(reportandoMatch[1], 10)) : 0;
    return Math.max(0, fromDb, fromRun, fromMessage);
})() : 0}  {/* Cambiar de (statusLoading ? 'Cargando…' : '—') a 0 */}
```

### 2. Mejorar el endpoint de status para incluir más información de debug

En `views.py`, agregar al response de `ReporterStatusView`:
```python
return Response({
    "total_reported": total_reported,
    "total_reported_month": total_reported_month,
    "pending_24h": pending_24h,
    "total_pending": total_pending,
    "last_updated": last_updated,
    "workflow_progress": workflow_status,
    # Debug info
    "debug": {
        "has_batches": ReportBatch.objects.filter(user=user, status='SUCCESS').exists(),
        "latest_batch_date": ReportBatch.objects.filter(user=user, status='SUCCESS').order_by('-created_at').first().created_at.isoformat() if ReportBatch.objects.filter(user=user, status='SUCCESS').exists() else None,
        "total_order_reports": OrderReport.objects.filter(user=user).count(),
        "timezone": str(tz),
        "today_start": today_start.isoformat(),
    }
})
```

### 3. Agregar validación en el comparer para asegurar que crea OrderMovementReport

En `comparer.py`, después de `_save_findings`, verificar:
```python
if len(reports_to_create) > 0:
    OrderMovementReport.objects.bulk_create(reports_to_create)
    self.logger.info(f"      💾 Guardados {len(reports_to_create)} reportes en OrderMovementReport.")
    self.stats['total_detected'] = len(reports_to_create)
else:
    self.logger.warning("      ⚠️ No se crearon OrderMovementReport (no hay órdenes sin movimiento)")
```

## Checklist de Verificación

- [ ] ¿El bot ejecutó hoy? (verificar `ReportBatch` con fecha de hoy)
- [ ] ¿Hay al menos 2 batches? (necesario para comparar)
- [ ] ¿El comparer detectó órdenes sin movimiento? (verificar `OrderMovementReport`)
- [ ] ¿El reporter marcó órdenes como reportadas? (verificar `OrderReport` con `status='reportado'`)
- [ ] ¿El timezone está configurado correctamente? (verificar `settings.TIME_ZONE`)
- [ ] ¿Hay un run activo o reciente? (verificar `ReporterRun` y `ReporterRunUser`)

## Comandos Útiles para Debugging

```bash
# Ver conteo de tablas
python manage.py shell -c "from core.models import *; print(f'Users: {User.objects.count()}'); print(f'ReportBatch: {ReportBatch.objects.count()}'); print(f'OrderReport: {OrderReport.objects.count()}'); print(f'OrderMovementReport: {OrderMovementReport.objects.count()}')"

# Ver último batch
python manage.py shell -c "from core.models import *; b = ReportBatch.objects.order_by('-created_at').first(); print(f'Último batch: {b.id if b else None}, {b.created_at if b else None}, {b.status if b else None}')"

# Ver distribución de status en OrderReport
python manage.py shell -c "from core.models import *; from django.db.models import Count; for item in OrderReport.objects.values('status').annotate(count=Count('id')): print(f'{item[\"status\"]}: {item[\"count\"]}')"
```
