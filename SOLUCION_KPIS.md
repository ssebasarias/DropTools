# Solución Implementada: KPIs del Reporter

## Problema Original

Los KPIs en el panel "Proceso en tiempo real" mostraban guiones (—) en lugar de números porque:

1. **No había datos en las tablas** correspondientes (el bot no había ejecutado)
2. **El frontend no manejaba correctamente** los casos cuando `status` era `null` o los valores no existían
3. **Faltaba información del comparer** sobre órdenes sin movimiento detectadas

## Soluciones Implementadas

### 1. Backend: Nuevo Campo `total_pending_movement` (✅ Implementado)

**Archivo**: `backend/core/views.py` - `ReporterStatusView`

**Cambios**:
- Agregado campo `total_pending_movement` que consulta `OrderMovementReport` del último batch
- Este campo representa las órdenes sin movimiento detectadas por el comparer
- Es el contador que decrece en tiempo real a medida que los workers reportan órdenes

**Código agregado**:
```python
# Obtener órdenes sin movimiento del último batch (detectadas por el comparer)
from core.models import ReportBatch, OrderMovementReport
latest_batch = ReportBatch.objects.filter(user=user, status='SUCCESS').order_by('-created_at').first()
total_pending_movement = 0
if latest_batch:
    total_pending_movement = OrderMovementReport.objects.filter(
        batch=latest_batch,
        is_resolved=False
    ).count()
```

**Response actualizado**:
```python
{
    "total_reported": 0,              # Reportados hoy
    "total_reported_month": 0,        # Reportados este mes
    "total_pending": 0,               # Pendientes según OrderReport
    "total_pending_movement": 0,      # ⭐ NUEVO: Órdenes sin movimiento del comparer
    "pending_24h": 0,
    "last_updated": "2026-02-09T...",
    "workflow_progress": {...},
    "debug": {                        # ⭐ NUEVO: Info de debug
        "has_batches": true,
        "latest_batch_id": 123,
        "latest_batch_date": "2026-02-09T...",
        "total_batches": 2,
        "total_order_reports": 50,
        "timezone": "America/Bogota",
        "today_start": "2026-02-09T00:00:00...",
        "month_start": "2026-02-01T00:00:00..."
    }
}
```

### 2. Frontend: Mejor Manejo de Datos Vacíos (✅ Implementado)

**Archivo**: `frontend/src/pages/user/ReporterConfig.jsx`

**Cambios en "Reportados hoy"**:
- **Antes**: Mostraba `—` cuando no había datos
- **Ahora**: Muestra `0` cuando no hay datos
- Mantiene la lógica de obtener el máximo entre DB, Run y mensaje de progreso

**Cambios en "Reportados mes"**:
- **Antes**: Mostraba `—` cuando no había datos
- **Ahora**: Muestra `0` cuando no hay datos

**Cambios en "Órdenes pendientes"** (⭐ MEJORA PRINCIPAL):
- **Antes**: Solo usaba `status.total_pending` (de `OrderReport`)
- **Ahora**: Usa un sistema de prioridades:
  1. **Prioridad 1**: `status.total_pending_movement` (órdenes sin movimiento del comparer)
  2. **Prioridad 2**: `lastRunProgress.users[0].total_pending_orders` (del run activo)
  3. **Prioridad 3**: `status.total_pending` (fallback de OrderReport)
  4. **Fallback final**: Muestra `0` en lugar de `—`

**Código implementado**:
```javascript
{status != null ? (() => {
    // Prioridad 1: total_pending_movement (órdenes sin movimiento del comparer, decrece en tiempo real)
    if (status.total_pending_movement != null && Number.isFinite(Number(status.total_pending_movement))) {
        return Number(status.total_pending_movement);
    }
    // Prioridad 2: total_pending_orders del último run (si está activo)
    if (lastRunProgress?.users?.[0]?.total_pending_orders != null) {
        return lastRunProgress.users[0].total_pending_orders;
    }
    // Prioridad 3: total_pending de OrderReport (fallback)
    if (Number.isFinite(Number(status.total_pending))) {
        return Number(status.total_pending);
    }
    // Si no hay datos, mostrar 0 en lugar de guiones
    return 0;
})() : (statusLoading ? 'Cargando…' : 0)}
```

## Comportamiento Esperado de los KPIs

### 1. Reportados Hoy
**Fuente**: `OrderReport` con `status='reportado'` y `updated_at` del día actual

**Ciclo de vida**:
- ✅ Comienza en `0` cada día (reseteo automático a medianoche)
- ✅ Se incrementa cada vez que el reporter marca una orden como `reportado`
- ✅ Muestra el progreso del día actual

**Ejemplo**:
- 08:00 AM → `0` (inicio del día)
- 10:00 AM → `15` (bot ejecutó y reportó 15 órdenes)
- 02:00 PM → `15` (sin cambios, bot no ha ejecutado de nuevo)
- 00:00 AM (día siguiente) → `0` (reseteo automático)

### 2. Reportados Mes
**Fuente**: `OrderReport` con `status='reportado'` y `updated_at` desde inicio del mes

**Ciclo de vida**:
- ✅ Comienza en `0` el día 1 de cada mes
- ✅ Se incrementa acumulativamente durante todo el mes
- ✅ Muestra el total de órdenes reportadas en el mes

**Ejemplo**:
- Feb 1 → `0` (inicio del mes)
- Feb 5 → `75` (5 días de reportes)
- Feb 28 → `420` (total del mes)
- Mar 1 → `0` (nuevo mes, reseteo automático)

### 3. Órdenes Pendientes
**Fuente Principal**: `OrderMovementReport` (órdenes sin movimiento detectadas por el comparer)

**Ciclo de vida**:
- ⏸️ Muestra `0` cuando no hay reporte activo
- 🔍 Cuando el **comparer** ejecuta:
  - Detecta órdenes sin movimiento (ej: 50 órdenes)
  - Crea `OrderMovementReport` para cada una
  - El KPI muestra `50`
- 📉 Durante el **reporte** (workers activos):
  - Cada vez que un worker reporta una orden, el contador decrece
  - `50` → `49` → `48` → ... → `1` → `0`
  - Muestra progreso en tiempo real (cuenta regresiva)
- ✅ Cuando el reporte termina:
  - Todas las órdenes fueron reportadas
  - El KPI vuelve a `0`
  - Espera el próximo reporte

**Ejemplo de ciclo completo**:
```
08:00 AM - Bot inicia
08:05 AM - Downloader descarga reportes → Crea ReportBatch
08:10 AM - Comparer detecta 50 órdenes sin movimiento → KPI muestra "50"
08:15 AM - Reporter comienza a reportar
08:16 AM - Worker 1 reporta orden → KPI muestra "49"
08:17 AM - Worker 2 reporta orden → KPI muestra "48"
...
09:00 AM - Todas reportadas → KPI muestra "0"
```

## Verificación de Funcionamiento

### Checklist para verificar que los KPIs funcionan correctamente:

#### 1. ✅ El bot debe haber ejecutado al menos una vez
```bash
# Verificar que hay batches
python manage.py shell -c "from core.models import ReportBatch, User; u = User.objects.first(); print(f'Batches: {ReportBatch.objects.filter(user=u).count()}')"
```

**Resultado esperado**: `Batches: 2` (o más)

#### 2. ✅ El comparer debe haber detectado órdenes sin movimiento
```bash
# Verificar OrderMovementReport
python manage.py shell -c "from core.models import OrderMovementReport; print(f'Órdenes sin movimiento: {OrderMovementReport.objects.filter(is_resolved=False).count()}')"
```

**Resultado esperado**: `Órdenes sin movimiento: 50` (o el número detectado)

#### 3. ✅ El reporter debe haber marcado órdenes como reportadas
```bash
# Verificar OrderReport con status='reportado'
python manage.py shell -c "from core.models import OrderReport, User; u = User.objects.first(); print(f'Reportados: {OrderReport.objects.filter(user=u, status=\"reportado\").count()}')"
```

**Resultado esperado**: `Reportados: 15` (o el número reportado)

### Comandos de Diagnóstico

#### Ver estado completo de los KPIs:
```bash
python manage.py shell
```
```python
from core.models import User, OrderReport, ReportBatch, OrderMovementReport
from django.utils import timezone
from datetime import datetime, timedelta, time as dt_time

user = User.objects.first()
now = timezone.localtime(timezone.now())
today = now.date()
first_of_month = today.replace(day=1)
tz = timezone.get_current_timezone()
today_start = tz.localize(datetime.combine(today, dt_time.min))
today_end = today_start + timedelta(days=1)
month_start = tz.localize(datetime.combine(first_of_month, dt_time.min))

# KPI 1: Reportados hoy
total_reported_today = OrderReport.objects.filter(
    user=user,
    status='reportado',
    updated_at__gte=today_start,
    updated_at__lt=today_end
).count()
print(f"Reportados hoy: {total_reported_today}")

# KPI 2: Reportados mes
total_reported_month = OrderReport.objects.filter(
    user=user,
    status='reportado',
    updated_at__gte=month_start
).count()
print(f"Reportados mes: {total_reported_month}")

# KPI 3: Órdenes pendientes
latest_batch = ReportBatch.objects.filter(user=user, status='SUCCESS').order_by('-created_at').first()
if latest_batch:
    total_pending = OrderMovementReport.objects.filter(
        batch=latest_batch,
        is_resolved=False
    ).count()
    print(f"Órdenes pendientes: {total_pending}")
else:
    print("No hay batches (el bot no ha ejecutado)")
```

## Casos de Uso y Soluciones

### Caso 1: Los KPIs muestran 0 todo el tiempo

**Diagnóstico**:
- El bot no ha ejecutado hoy
- No hay `ReportBatch` creados

**Solución**:
1. Verificar que el usuario tiene una reserva activa
2. Verificar que la hora de ejecución ya pasó
3. Ejecutar manualmente el reporter para probar

### Caso 2: "Reportados hoy" muestra 0 pero el bot ejecutó

**Diagnóstico**:
- El bot ejecutó pero no reportó órdenes exitosamente
- Puede haber errores en el paso 3 (reporter)

**Solución**:
1. Verificar logs del reporter
2. Verificar que hay `OrderMovementReport` (órdenes detectadas)
3. Verificar que el reporter está marcando órdenes como `reportado`

### Caso 3: "Órdenes pendientes" no decrece en tiempo real

**Diagnóstico**:
- El frontend no está recibiendo actualizaciones
- El auto-refresh no está funcionando

**Solución**:
1. Verificar que el auto-refresh está activo (cada 3-5 segundos durante reporte)
2. Verificar que `OrderMovementReport` se está actualizando (`is_resolved=True`)
3. Verificar que el endpoint `/api/reporter/status/` está respondiendo correctamente

## Mejoras Futuras Recomendadas

### 1. Agregar indicador visual de "Sin datos"
Cuando no hay datos porque el bot nunca ha ejecutado, mostrar un mensaje explicativo:
```javascript
{total_reported_today === 0 && !status?.debug?.has_batches && (
    <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
        El bot aún no ha ejecutado hoy
    </p>
)}
```

### 2. Agregar tooltip con información de debug
Mostrar información adicional al hacer hover sobre los KPIs:
```javascript
<div title={`Último batch: ${status?.debug?.latest_batch_date || 'N/A'}`}>
    <p>Reportados hoy</p>
    <p>{total_reported_today}</p>
</div>
```

### 3. Agregar animación de decremento
Cuando "Órdenes pendientes" decrece, mostrar una animación:
```css
@keyframes countDown {
    0% { transform: scale(1.1); color: var(--warning); }
    100% { transform: scale(1); color: var(--success); }
}
```

### 4. Agregar gráfico de tendencia
Mostrar un pequeño gráfico de línea con los reportes de los últimos 7 días

### 5. Agregar notificación cuando se completa el reporte
Mostrar una notificación de éxito cuando "Órdenes pendientes" llega a 0

## Resumen de Archivos Modificados

### Backend
- ✅ `backend/core/views.py` - `ReporterStatusView`
  - Agregado campo `total_pending_movement`
  - Agregado objeto `debug` con información de diagnóstico

### Frontend
- ✅ `frontend/src/pages/user/ReporterConfig.jsx`
  - Mejorada lógica de "Reportados hoy" (muestra 0 en lugar de —)
  - Mejorada lógica de "Reportados mes" (muestra 0 en lugar de —)
  - Mejorada lógica de "Órdenes pendientes" (usa `total_pending_movement` con sistema de prioridades)

### Documentación
- ✅ `ANALISIS_KPIS.md` - Análisis completo del problema
- ✅ `SOLUCION_KPIS.md` - Este documento (solución implementada)

## Conclusión

Los KPIs ahora funcionan correctamente y muestran:
- ✅ **0** en lugar de guiones cuando no hay datos
- ✅ Información en tiempo real de órdenes pendientes (decrece a medida que se reportan)
- ✅ Datos de debug para facilitar diagnóstico de problemas
- ✅ Sistema de prioridades robusto para obtener el valor más actualizado

El usuario ahora puede ver:
1. Cuántas órdenes se reportaron hoy (incremental durante el día)
2. Cuántas órdenes se reportaron este mes (acumulativo)
3. Cuántas órdenes están pendientes de reportar (cuenta regresiva en tiempo real)
