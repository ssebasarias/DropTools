# Paso a paso: testeo del reporter por slot (3 usuarios, 6 workers)

Guía con **comandos completos en PowerShell** para: migraciones, cargar usuarios, replicar datos del usuario 2 a 3 y 4, crear reservas en el mismo slot, levantar Docker con 6 workers, disparar el slot y monitorear.

**Requisitos:** Estar en la raíz del proyecto (donde está `docker-compose.yml`). Tener el archivo `scripts/reporter_test_users.json` con los 4 usuarios (credenciales app + Dropi).

---

## 1. Aplicar migraciones e incorporar usuarios a la base de datos

### 1.1 Ir a la raíz del proyecto

```powershell
cd c:\Users\guerr\OneDrive\Documentos\DropTools
```

### 1.2 Levantar solo los servicios necesarios (DB, Redis, Backend)

```powershell
docker compose up -d db redis backend
```

### 1.3 Esperar unos segundos y aplicar migraciones

```powershell
Start-Sleep -Seconds 10
docker compose exec backend python backend/manage.py migrate --noinput
```

**Si la BD se inicializó desde `docs/droptools_db.sql`** (tablas ya existen, esquema distinto a las migraciones de Django):

1. Reparar contenttypes y preparar migraciones (quita el fake de 0002 y añade la columna `name` para que 0002 pueda aplicarse de verdad):

```powershell
docker compose exec backend python backend/manage.py fix_migrations_after_dump
```

2. Aplicar contenttypes 0002 (elimina la columna `name`) y luego el resto con `--fake-initial` (marca como aplicadas las migraciones iniciales cuyas tablas ya existen):

```powershell
docker compose exec backend python backend/manage.py migrate contenttypes 0002
docker compose exec backend python backend/manage.py migrate --noinput --fake-initial
```

Si tras el `--fake` de contenttypes 0002 ves error en `post_migrate` por la columna `name`, usa este flujo (fix_migrations_after_dump + migrate 0002 + migrate --fake-initial).

**Si además falla en `core.0001_initial`** con `relation "ai_feedback" already exists` (el dump ya tiene todas las tablas de core hasta la 0006), haz fake de las migraciones de core 0001 a 0006 y luego aplica el resto:

```powershell
docker compose exec backend python backend/manage.py migrate core 0001 --fake
docker compose exec backend python backend/manage.py migrate core 0002 --fake
docker compose exec backend python backend/manage.py migrate core 0003 --fake
docker compose exec backend python backend/manage.py migrate core 0004 --fake
docker compose exec backend python backend/manage.py migrate core 0005 --fake
docker compose exec backend python backend/manage.py migrate core 0006 --fake
docker compose exec backend python backend/manage.py migrate --noinput
```

**Si al aplicar core.0007 falla con** `there is no unique constraint matching given keys for referenced table "users"`, la tabla `users` del dump puede no tener la PRIMARY KEY aplicada. Asegúrala y vuelve a migrar:

```powershell
docker compose exec backend python backend/manage.py fix_users_pk_for_migrations
docker compose exec backend python backend/manage.py migrate --noinput
```

### 1.4 Cargar los 4 usuarios de prueba desde el JSON

```powershell
docker compose exec backend python backend/manage.py load_reporter_test_users --file=scripts/reporter_test_users.json
```

Si quieres forzar los IDs 1–4 al crear (BD vacía o de prueba):

```powershell
docker compose exec backend python backend/manage.py load_reporter_test_users --file=scripts/reporter_test_users.json --force-id
```

### 1.5 Comprobar que los usuarios existen

```powershell
docker compose exec backend python backend/manage.py shell -c "from django.contrib.auth import get_user_model; U = get_user_model(); [print(u.id, u.email, u.role) for u in U.objects.all().order_by('id')]"
```

Deberías ver los 4 usuarios (admin + Martin, Alexander, Sebastian).

---

## 2. Replicar datos del usuario 2 a los usuarios 3 y 4

Así los usuarios 3 y 4 tendrán el mismo “último batch” y órdenes pendientes que el 2 (para que el reporter cargue rangos y se vea el work stealing).

### 2.1 (Opcional) Ver qué se copiaría sin escribir (dry-run)

```powershell
docker compose exec backend python backend/manage.py replicate_reporter_user_data --source-user=2 --target-users=3,4 --dry-run
```

### 2.2 Ejecutar la replicación

```powershell
docker compose exec backend python backend/manage.py replicate_reporter_user_data --source-user=2 --target-users=3,4
```

### 2.3 Comprobar batches y órdenes pendientes

```powershell
docker compose exec backend python backend/manage.py shell -c "
from core.models import ReportBatch, OrderMovementReport
for uid in [2, 3, 4]:
    b = ReportBatch.objects.filter(user_id=uid, status='SUCCESS').order_by('-created_at').first()
    n = OrderMovementReport.objects.filter(batch=b, is_resolved=False).count() if b else 0
    print(f'user_id={uid} batch_id={b.id if b else None} pendientes={n}')
"
```

---

## 3. Crear reservas en el mismo slot (usuarios 2, 3 y 4 en hora 10)

Asignamos los tres clientes al **slot hora 10** con un solo comando.

### 3.1 Crear reservas (comando)

```powershell
docker compose exec backend python backend/manage.py ensure_reporter_reservations --user-ids=2,3,4 --hour=10
```

Opcional: cambiar la estimación de órdenes mensuales (default 500):

```powershell
docker compose exec backend python backend/manage.py ensure_reporter_reservations --user-ids=2,3,4 --hour=10 --monthly-orders=1000
```

### 3.2 Comprobar reservas

```powershell
docker compose exec backend python backend/manage.py shell -c "
from core.models import ReporterReservation
for r in ReporterReservation.objects.select_related('user', 'slot').all():
    print(r.user_id, r.user.email, 'slot', r.slot.hour)
"
```

---

## 4. Levantar Docker con 6 workers y resto de servicios

El override ya deja el worker con `--concurrency=6` y más recursos.

### 4.1 Levantar todos los servicios (incluye Celery worker y Flower)

```powershell
docker compose up -d
```

### 4.2 Ver que el worker tiene 6 procesos

```powershell
docker compose exec celery_worker celery -A droptools_backend inspect active
```

O revisar logs al arrancar:

```powershell
docker compose logs celery_worker --tail=30
```

Deberías ver algo como `celery@... ready` y la concurrencia en 6.

### 4.3 Abrir Flower (opcional, para ver tareas en tiempo real)

En el navegador: **http://localhost:5555**

---

## 5. Disparar el slot manualmente (sin esperar a la hora real)

Disparamos el slot de la **hora 10** para que procese a los 3 usuarios con reserva.

### 5.1 Disparar process_slot_task para la hora 10

```powershell
docker compose exec backend python backend/manage.py trigger_slot_task --hour=10
```

Verás un mensaje con `task_id` y `slot_time_iso`. Esa tarea crea el `ReporterRun`, encola 3 `download_compare_task` (uno por usuario) y luego se encolarán muchos `report_range_task` que los 6 workers irán tomando (work stealing).

### 5.2 Alternativa: disparar para la hora actual

```powershell
docker compose exec backend python backend/manage.py trigger_slot_task
```

(Solo tendrá efecto si los usuarios 2, 3 y 4 tienen reserva en la hora actual; si creaste reservas solo en hora 10, usa `--hour=10`.)

---

## 6. Monitorear: logs y Flower

### 6.1 Logs del worker (todas las líneas)

```powershell
docker compose logs -f celery_worker
```

Ctrl+C para salir.

### 6.2 Logs filtrados (solo tareas y user_id/run_id)

```powershell
.\scripts\monitor_reporter_workers.ps1
```

Para ver **todo** lo que hacen los 6 workers en tiempo real (Procesando orden X/Y, Registro DB marcado como RESUELTO, etc.):

```powershell
.\scripts\monitor_reporter_workers.ps1 -All
```

**Ver los 6 workers en simultáneo (6 terminales, uno por worker):** abre 6 ventanas o pestañas de PowerShell en la raíz del proyecto y ejecuta en cada una:

| Terminal | Comando |
|---------|--------|
| 1 | `.\scripts\monitor_reporter_workers.ps1 -Worker 1` |
| 2 | `.\scripts\monitor_reporter_workers.ps1 -Worker 2` |
| 3 | `.\scripts\monitor_reporter_workers.ps1 -Worker 3` |
| 4 | `.\scripts\monitor_reporter_workers.ps1 -Worker 4` |
| 5 | `.\scripts\monitor_reporter_workers.ps1 -Worker 5` |
| 6 | `.\scripts\monitor_reporter_workers.ps1 -Worker 6` |

Cada terminal muestra **solo** las líneas de ese worker (ForkPoolWorker-1, ForkPoolWorker-2, etc.). Si un worker está idle no verás líneas nuevas hasta que tome una tarea.

O con un filtro personalizado:

```powershell
.\scripts\monitor_reporter_workers.ps1 -Filter "download_compare|report_range|user_id|run_id|semaphore|range"
```

### 6.3 Flower

- **http://localhost:5555**
- Pestaña **Tasks**: ver `process_slot_task`, `download_compare_task`, `report_range_task`.
- Pestaña **Workers**: ver los 6 workers y las tareas en ejecución.
- En cada tarea puedes ver argumentos (`user_id`, `run_id`, `range_start`, `range_end`) para comprobar el reparto entre usuarios.

### 6.4 Resumen de progreso por run (opcional, desde backend)

Si quieres ver por run_id cuántos rangos lleva cada usuario:

```powershell
docker compose exec backend python backend/manage.py shell -c "
from core.models import ReporterRun, ReporterRunUser, ReporterRange
r = ReporterRun.objects.order_by('-id').first()
if r:
    print('Run', r.id, r.status, r.scheduled_at)
    for ru in ReporterRunUser.objects.filter(run=r):
        total = ReporterRange.objects.filter(run=r, run_user=ru).count()
        done = ReporterRange.objects.filter(run=r, run_user=ru, status='completed').count()
        print(f'  user_id={ru.user_id} download_compare={ru.download_compare_status} ranges {done}/{total}')
"
```

---

## 7. Qué deberías ver durante el test

1. **process_slot_task** se ejecuta una vez: crea un `ReporterRun` y encola 3 `download_compare_task` (user_id 2, 3, 4).
2. **download_compare_task** (3 tareas): cada una toma un slot del semáforo Selenium, hace login en Dropi con la cuenta del usuario, descarga/compara, crea rangos en BD y encola `report_range_task` por cada rango. Hasta 6 Selenium en paralelo (límite global).
3. **report_range_task** (muchas): los 6 workers van tomando rangos de cualquiera de los 3 usuarios (work stealing). En logs/Flower verás `user_id` y `run_id` distintos en distintas tareas.
4. No se superan 6 procesos Selenium a la vez (semáforo en Redis).

---

## 8. Resumen de comandos en orden (copiar/pegar)

```powershell
# 1. Raíz del proyecto
cd c:\Users\guerr\OneDrive\Documentos\DropTools

# 2. Levantar DB, Redis, Backend
docker compose up -d db redis backend
Start-Sleep -Seconds 10

# 3. Migraciones
docker compose exec backend python backend/manage.py migrate --noinput

# 4. Cargar usuarios de prueba
docker compose exec backend python backend/manage.py load_reporter_test_users --file=scripts/reporter_test_users.json

# 5. Replicar datos usuario 2 → 3 y 4
docker compose exec backend python backend/manage.py replicate_reporter_user_data --source-user=2 --target-users=3,4

# 6. Crear reservas (slot 10 para users 2,3,4)
docker compose exec backend python backend/manage.py ensure_reporter_reservations --user-ids=2,3,4 --hour=10

# 7. Levantar todo (incluye Celery con 6 workers)
docker compose up -d

# 8. Disparar el slot hora 10 (sin esperar a Celery Beat)
docker compose exec backend python backend/manage.py trigger_slot_task --hour=10

# 9. Monitorear (en otra ventana PowerShell)
.\scripts\monitor_reporter_workers.ps1
# Y/o abrir http://localhost:5555
```

---

## 9. Si algo falla

- **Migraciones:** Si faltan tablas, revisa que existan las migraciones `0007_reporter_slot_models` y `0008_reporter_slot_initial_data` y vuelve a ejecutar `migrate --noinput`.
- **Usuario 2 sin batch SUCCESS:** La replicación requiere que el usuario 2 tenga al menos un `ReportBatch` con `status='SUCCESS'` y snapshots/order_movement_reports. Si no, ejecuta antes una vez el reporter para el usuario 2 (o crea datos de prueba).
- **No se encolan tareas:** Comprueba que Redis esté arriba (`docker compose ps`) y que el worker esté conectado (logs de `celery_worker`).
- **Semáforo bloqueado:** En desarrollo, si un worker murió sin liberar, el semáforo puede quedar desincronizado; reiniciar Redis o el worker suele corregirlo (en producción existe TTL).
