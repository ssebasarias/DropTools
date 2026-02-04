# Comandos Docker – Testing Reporter (DEV)

Desde la **raíz del proyecto** (donde está `docker-compose.yml`).

---

## 1. Levantar el stack

```bash
docker compose up -d db redis backend celery_worker flower
```

Con override (6 workers Celery, más recursos):

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d db redis backend celery_worker flower
```

Comprobar que todo esté en marcha:

```bash
docker compose ps
```

---

## 2. Crear reservas para la hora de prueba (obligatorio)

Si **no** hay reservas para la hora que uses (ej. 10), la tarea crea la run y la marca completada con 0 usuarios y el monitor no mostrará nada (solo muestra runs en estado RUNNING).

Crea reservas para los usuarios 2, 3, 4 en la hora 10 con **peso 3** cada uno (para probar “solo caben 2”, capacidad 6):

```bash
docker compose exec backend python backend/manage.py ensure_reporter_reservations --user-ids=2,3,4 --hour=10 --monthly-orders=6000
```

(`monthly_orders_estimate` ≥ 5001 da peso 3; 6000 es un valor típico para “pez gordo”.)

Comprueba en Django Admin o en la API que los tres usuarios tienen reserva en el slot de las 10:00.

---

## 3. Configurar proxy (DEV)

El archivo `backend/proxy_dev_config.json` ya debe existir con tu proxy (198.143.22.45:12323) y `user_ids: [2, 3, 4]`. Está montado en el contenedor vía `./backend:/app/backend`.

Si no existe, cópialo desde el ejemplo:

```bash
copy backend\proxy_dev_config.example.json backend\proxy_dev_config.json
```

Luego edita `backend/proxy_dev_config.json` y rellena host, port, username, password.

---

## 4. Ver la IP usada por el proxy

Ejecutar dentro del contenedor **backend** (abre Selenium con proxy y visita api.ipify.org):

```bash
docker compose exec backend python backend/manage.py verify_proxy_ip
```

Deberías ver algo como: `IP detectada (con proxy): 198.143.22.45` (o la IP que devuelva el proxy).

---

## 5. Lanzar slot manual (con capacidad por peso, DEV)

Encolar la tarea para la hora 10 (los workers Celery la ejecutan):

```bash
docker compose exec backend python backend/manage.py trigger_slot_task --hour=10 --dev
```

Para otra hora (0–23):

```bash
docker compose exec backend python backend/manage.py trigger_slot_task --hour=14 --dev
```

**Ejecutar en el mismo proceso (síncrono, sin Celery):**

```bash
docker compose exec backend python backend/manage.py trigger_slot_task --hour=10 --dev --sync
```

Solo encolar (sin `--dev`, comportamiento normal de producción):

```bash
docker compose exec backend python backend/manage.py trigger_slot_task --hour=10
```

---

## 6. Monitor en tiempo real de workers

Vista tipo dashboard en texto (actualiza cada 5 s):

```bash
docker compose exec backend python backend/manage.py monitor_workers
```

Una sola salida y salir:

```bash
docker compose exec backend python backend/manage.py monitor_workers --once
```

Cada 10 segundos:

```bash
docker compose exec backend python backend/manage.py monitor_workers --interval 10
```

(Ctrl+C para salir del loop.)

---

## 7. Ver logs de Celery (workers)

Todos los logs del worker:

```bash
docker compose logs -f celery_worker
```

Solo líneas relacionadas con reporter/slot (script existente):

```bash
.\scripts\monitor_reporter_workers.ps1
```

---

## 8. Flower (dashboard Celery)

Abrir en el navegador: **http://localhost:5555**

Ahí ves tareas encoladas, en ejecución y terminadas.

---

## Orden típico de prueba

1. **Levantar stack** (paso 1).
2. **Crear reservas** (paso 2): `docker compose exec backend python backend/manage.py ensure_reporter_reservations --user-ids=2,3,4 --hour=10 --monthly-orders=6000`
3. **Ver IP proxy** (paso 4): `docker compose exec backend python backend/manage.py verify_proxy_ip`
4. **En otra terminal, arrancar el monitor** (paso 6): `docker compose exec backend python backend/manage.py monitor_workers`
5. **En otra terminal, lanzar slot con capacidad** (paso 5): `docker compose exec backend python backend/manage.py trigger_slot_task --hour=10 --dev`
6. Esperar unos segundos: el worker Celery ejecuta la tarea, crea la run y encola download_compare. En el monitor deberías ver: semáforo, run, user_id activos, “pendiente (capacidad)” para el tercero si caben solo 2, y cuando uno termina que entra el tercero.
7. Opcional: **Flower** http://localhost:5555 para ver tareas Celery.

---

## Por qué el monitor muestra “No hay runs en ejecución”

- **Sin reservas para esa hora:** Si los usuarios 2, 3, 4 no tienen `ReporterReservation` en el slot de las 10:00, la tarea crea la run y la marca **COMPLETED** con 0 usuarios. El monitor solo muestra runs en estado **RUNNING**, por eso no ves nada. Solución: paso 2 (crear reservas).
- **La tarea aún no se ejecutó:** Si acabas de encolar con `trigger_slot_task --dev`, el worker tarda unos segundos en coger la tarea y crear la run. Espera 5–10 s y vuelve a mirar el monitor (o usa `monitor_workers` en loop).

## Login fallido (TimeoutException en campo email)

Si en los logs ves **LOGIN FALLIDO** y **TimeoutException** en `auth_manager.py` (campo de email no encontrado), la página de Dropi cargó pero el formulario no apareció a tiempo. Posibles causas:

- **Proxy lento o bloqueado:** Dropi puede ralentizar o mostrar captcha cuando la petición viene de una IP de proxy. El tiempo de espera del login se aumentó a 30 s para dar margen.
- **Varios logins desde la misma IP:** Tres workers entrando a la vez por el mismo proxy pueden disparar anti-bot. Prueba encolar **un solo usuario** (reserva solo user 2 en hora 10) y volver a lanzar el slot.
- **Cambio en la web de Dropi:** Si Dropi cambió el HTML (atributo `name="email"`), habría que actualizar los selectores en `auth_manager.py`.

Para aislar: ejecutar **sin proxy** (quitar o vaciar `proxy_dev_config.json` o no incluir tu user_id en `user_ids`) y volver a lanzar; si sin proxy el login pasa, el problema es el proxy o el uso simultáneo desde esa IP.

**Captura de pantalla:** Cuando el login falla, el bot guarda automáticamente una captura en `backend/results/screenshots/login_fail_YYYYMMDD_HHMMSS_user{N}.png`. Así puedes ver si Dropi mostró captcha, “demasiados intentos” o otro contenido. En Docker la ruta dentro del contenedor es `/app/backend/results/screenshots/`; para verla en tu máquina asegúrate de tener montado `./backend:/app/backend` (el directorio `results/` está en `.gitignore`).

## Requisitos previos

- **Reservas creadas** para la hora de prueba: `ensure_reporter_reservations --user-ids=2,3,4 --hour=10 --monthly-orders=6000` (peso 3 cada uno).
- Slot con **capacity_points = 6** (por defecto 6).
- **proxy_dev_config.json** con `user_ids: [2, 3, 4]` y el proxy 198.143.22.45:12323.
- **DAHELL_ENV=development** en backend y celery_worker (ya está en tu `docker-compose` y override).

---

## Resumen de comandos

| Acción              | Comando |
|---------------------|--------|
| Levantar stack      | `docker compose up -d db redis backend celery_worker flower` |
| **Crear reservas (hora 10, peso 3)** | `docker compose exec backend python backend/manage.py ensure_reporter_reservations --user-ids=2,3,4 --hour=10 --monthly-orders=6000` |
| Ver IP proxy        | `docker compose exec backend python backend/manage.py verify_proxy_ip` |
| Slot manual (dev)   | `docker compose exec backend python backend/manage.py trigger_slot_task --hour=10 --dev` |
| Slot síncrono (dev) | `docker compose exec backend python backend/manage.py trigger_slot_task --hour=10 --dev --sync` |
| Monitor workers     | `docker compose exec backend python backend/manage.py monitor_workers` |
| Monitor una vez     | `docker compose exec backend python backend/manage.py monitor_workers --once` |
| Logs Celery         | `docker compose logs -f celery_worker` |
| Flower              | http://localhost:5555 |
