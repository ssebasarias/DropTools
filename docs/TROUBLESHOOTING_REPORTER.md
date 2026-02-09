# Diagnóstico: botón "Iniciar a Reportar" no funciona

## Modo desarrollo vs producción (cómo diferenciarlos)

| | **Desarrollo (local)** | **Desarrollo (Docker)** | **Producción (Docker)** |
|---|------------------------|-------------------------|--------------------------|
| **Variable** | `DROPTOOLS_ENV=development` en `.env`, backend **fuera** de Docker | `DROPTOOLS_ENV=development` en override, backend **en** Docker | `DAHELL_ENV=production` o sin definir |
| **Qué hace el botón** | Reporter **en proceso** (Edge visible en tu PC) | Reporter **vía Celery** (worker en Docker, mismo flujo que producción) | Reporter **vía Celery** (servidor) |
| **Requisitos** | Backend en local, BD accesible | Docker Compose (backend + celery_worker + redis + db) | Igual que desarrollo Docker |
| **Badge en UI** | "Modo desarrollo" (verde) | "Modo desarrollo (Docker)" (naranja) | "Modo producción" (azul) |

### Desarrollo local (sin Docker)

En la raíz del proyecto, en tu `.env`, pon `DROPTOOLS_ENV=development`. Arranca solo el backend (`venv\Scripts\python.exe backend\manage.py runserver`) y el frontend. Verás **"Modo desarrollo"** y el reporter se ejecuta en proceso (navegador visible).

### Desarrollo con Docker (Windows + WSL, pruebas antes de subir al servidor)

Para probar el flujo **igual que en producción** (Celery, Chromium/Firefox en contenedor) pero en tu PC:

1. El archivo **`docker-compose.override.yml`** ya define `DROPTOOLS_ENV=development` para `backend` y `celery_worker`.
2. Levanta todo: `docker compose up -d` (o `docker compose up -d --build`).
3. En Reporter Configuration verás el badge **"Modo desarrollo (Docker)"** (naranja). Al pulsar "Iniciar a Reportar" se encola en Celery y el worker ejecuta el reporter en el contenedor (timeouts y config de desarrollo).
4. En consola del backend al arrancar: `[DropTools] DROPTOOLS_ENV=development | Reporter: Celery (desarrollo Docker)`.

Así puedes hacer cambios en tu PC, probar con Docker + Celery, y cuando funcione subir al servidor sin que el servidor sufra cada cambio.

**Logs del reporter en Celery:** La tarea pasa su logger a `UnifiedReporter`, así que todos los mensajes de los módulos del reporter (credenciales, login, clics, descarga, comparación, formulario Siguiente, etc.) salen en `docker compose logs -f celery_worker`. Deberías ver los comentarios de cada paso (PASO 1 driver, PASO 2 login, PASO 3 descarga, etc.) para monitorear y localizar fallos.

**Verificación automática:** Desde la raíz del proyecto (con Docker y backend levantados):

```powershell
.\scripts\verify_reporter_development_docker.ps1
```

El script comprueba contenedores, modo activo (GET /api/reporter/env/), obtiene token del usuario 2, hace POST /api/reporter/start/ y te indica que revises los logs del worker con `docker compose logs -f celery_worker`.

### Ejecutar el reporter manualmente dentro del contenedor (usuario 2)

Para probar el reporter **sin pasar por la UI** (por ejemplo usuario 2, headless):

```powershell
docker compose exec backend python manage.py unified_reporter --user-id 2 --headless
```

El backend debe estar levantado (`docker compose up -d`). El reporter se ejecuta dentro del contenedor con Chromium/Firefox. Los logs salen en esa terminal.

**Certeza:** El badge en la UI y el mensaje en consola indican el modo. En desarrollo local la petición puede tardar 1–2 min; en desarrollo Docker o producción responde enseguida con "enqueued".

---

El botón **Iniciar a Reportar** en Reporter Configuration hace lo siguiente:

1. **Frontend** → `POST /api/reporter/start/` con tu token de sesión.
2. **Backend** → Comprueba que estés logueado y que tengas `dropi_email`/`dropi_password` en tu usuario. Crea un registro de progreso y **encola una tarea en Celery** (`execute_workflow_task`).
3. **Celery worker** → Ejecuta el comando unificado (UnifiedReporter: login Dropi, descarga reportes, comparación, reportar).

Si el botón “no hace nada” o ves un mensaje de error, sigue estos pasos.

---

## Monitorear la ejecución en vivo

Para ver la evolución **en la UI** y **por dentro** (worker) a la vez:

1. **En el navegador (http://localhost:5173)**  
   Entra a **Reporter Configuration**. Verás:
   - Badge **"Modo desarrollo (Docker)"** (naranja).
   - Tras pulsar **"Iniciar a Reportar"**: el botón queda ocupado unos segundos, luego la página hace polling cada pocos segundos y muestra el **estado del workflow** (mensaje tipo "Encolando...", "Iniciando...", "Descarga completada...", etc.). Si hay error, aparece en rojo arriba.

2. **En otra terminal (lo que hace el worker por dentro)**  
   Ejecuta:
   ```powershell
   docker compose logs -f celery_worker
   ```
   Verás una secuencia parecida a esta (orden aproximado):

   | Fase | Qué verás en los logs del worker |
   |------|-----------------------------------|
   | Encolado | `Task core.tasks.execute_workflow_task[...] received` |
   | Inicio | `Iniciando workflow para usuario 2`, `Orden de navegadores: ['chrome', 'firefox']` |
   | Navegador | `Intentando navegador: CHROME`, `Chrome/Chromium iniciado...`, `Navegador listo` |
   | Login | `PASO 2: AUTENTICACIÓN`, `Credenciales cargadas`, `LOGIN EXITOSO` |
   | Descarga | `PASO 3: DESCARGA DE REPORTES`, `Navegando a Mis Pedidos`, `Proceso descarga AYER/HOY`, `Archivo descargado`, `Lote guardado` |
   | Comparación | `PASO 4: COMPARACIÓN`, `total_detected` |
   | Reporter | `PASO 5: REPORTE`, órdenes reportadas |
   | Fin | `Workflow completado exitosamente` o `Workflow falló` |

   Si algo falla, el mensaje de error y el traceback salen ahí; el frontend puede seguir mostrando "En ejecución" hasta que el polling actualice el estado a "failed" y el mensaje de error.

---

## 1. Qué error ves en pantalla

Tras los últimos cambios, si algo falla deberías ver un **mensaje en rojo** en la página (arriba del formulario). Ese texto suele ser el `error` que devuelve el backend.

- **"No se pudo encolar la tarea"** o **"Connection refused"** → Problema de **Redis/Celery** (ver sección 2).
- **"No Dropi account configured"** → Tu usuario en la BD no tiene `dropi_email`/`dropi_password` (ver sección 3).
- **"Credenciales inválidas"** / **401** → Sesión caducada; vuelve a hacer login.
- Si aparece un **traceback** (líneas de Python), es un fallo del backend o del worker; el mensaje y el traceback indican la causa.

---

## 2. Redis y Celery (encolar la tarea)

El backend **encola** el trabajo en Redis; el worker de Celery lo ejecuta. Si Redis o Celery fallan, el botón devuelve error al instante.

**Comprobar que los contenedores estén arriba:**

```powershell
docker compose ps
```

Deben estar **Up**: `droptools_redis`, `droptools_backend`, `droptools_celery_worker`.

**Logs del backend** (al hacer clic en "Iniciar a Reportar"):

```powershell
docker compose logs -f backend
```

Si ves algo como `Connection refused` a `redis:6379`, el backend no llega a Redis (red Docker, Redis caído, etc.).

**Logs del worker** (aquí se ejecuta realmente el reporter):

```powershell
docker compose logs -f celery_worker
```

- Si la tarea **ni siquiera aparece** en el worker → el fallo está en **encolar** (Redis/red/Celery config).
- Si la tarea **aparece y luego falla** → el fallo está en el **proceso de reporte** (navegador, internet, Dropi, permisos; ver sección 4).

**Reiniciar Redis y Celery:**

```powershell
docker compose restart redis celery_worker
```

---

## 3. Usuario sin cuenta Dropi

El backend exige que tu usuario tenga **dropi_email** y **dropi_password** en la base de datos (tabla `users`). Si no, responde 400 y verás algo como "No Dropi account configured".

**Comprobar en la BD** (por ejemplo desde el contenedor del backend):

```powershell
docker compose exec backend python backend/manage.py shell -c "
from core.models import User
u = User.objects.get(email='TU_EMAIL@ejemplo.com')
print('dropi_email:', u.dropi_email)
print('dropi_password:', '***' if u.dropi_password else None)
"
```

Si están vacíos, configura la cuenta Dropi desde la UI (Reporter Configuration / cuentas) o actualiza el usuario en la BD y vuelve a intentar.

---

## 4. Fallo durante el proceso de reporte (Celery ya ejecutando)

Si la tarea **sí se encola** y ves en los logs del worker que arranca el reporter pero luego falla, las causas típicas son:

| Causa | Síntoma / qué revisar |
|-------|------------------------|
| **Internet / red** | El worker no puede abrir Dropi (timeouts, DNS). Comprobar conectividad desde el contenedor: `docker compose exec celery_worker curl -sI https://app.dropi.co` (o similar). |
| **Navegador en el contenedor** | En Linux/Docker solo **Chromium** y **Firefox** (estables). Orden por defecto: `chrome` → `firefox`. Variable `BROWSER_ORDER` (ej. `chrome,firefox`). Si ambos fallan, verás en logs "Ningún navegador funcionó". |
| **Credenciales Dropi incorrectas** | Login a Dropi falla; en logs del worker suele aparecer error de login o de página. Verificar usuario/contraseña en la BD. |
| **Permisos en disco** | El worker escribe descargas en `results/downloads` (o la ruta configurada). Si no puede escribir, verás `PermissionError` o similar en los logs del worker. |
| **Error click descarga / Falló descarga de AYER** | En Docker el worker usa **Chromium** (no Edge) y **clicks por JavaScript** para evitar crashes del driver en headless. Si sigue fallando: cambio en la web de Dropi, selector desactualizado o anti-bot. Revisar `downloader.py`; probar en local con `headless=False`. Tras cambios en código, **recrear el worker**: `docker compose up -d --build celery_worker`. |

**Ver el error concreto del worker:**

```powershell
docker compose logs celery_worker --tail 200
```

Ahí debería aparecer el traceback de la excepción que rompe el reporter (navegador, red, Dropi, permisos, etc.).

---

## 5. Probar el endpoint a mano

Para aislar si el fallo es frontend, backend o Celery:

```powershell
# Sustituye TOKEN por tu token (lo puedes ver en DevTools → Application → Session Storage → auth_token)
$headers = @{
  "Authorization" = "Token TOKEN"
  "Content-Type"  = "application/json"
}
Invoke-WebRequest -Uri "http://localhost:8000/api/reporter/start/" -Method POST -Headers $headers -UseBasicParsing
```

- **200** y cuerpo con `"status": "enqueued"`, `"task_id": "..."` → Backend y encolado OK; el problema está en el worker o en el proceso de reporte.
- **400** → Revisar mensaje (ej. "No Dropi account configured").
- **401** → Token inválido o expirado; volver a hacer login.
- **500** → Revisar cuerpo (error y traceback) y logs del backend; suele ser Redis/Celery o excepción en la vista.

---

## Resumen rápido

1. **Mira el mensaje de error en rojo** en la página (y el traceback si aparece).
2. **Revisa** `docker compose ps` (redis, backend, celery_worker Up).
3. **Revisa** `docker compose logs backend` y `docker compose logs celery_worker` al pulsar el botón.
4. **Comprueba** que tu usuario tenga `dropi_email` y `dropi_password` en la BD.
5. Si la tarea se encola pero falla dentro del worker, **lee el traceback en los logs del celery_worker** (internet, navegador, Dropi, permisos).

Con eso se puede saber si el problema es de **internet**, **permisos**, **fallo en el proceso de reporte** o **otro error** (Redis, Celery, configuración, etc.).

---

## 6. Orden de navegadores (fallback en Linux)

En **Linux/Docker** el reporter solo usa navegadores estables y compatibles:

- **Por defecto en Docker:** `chrome` (Chromium) → `firefox` (solo estos dos; Edge no se instala en la imagen)
- **Por defecto en local (Windows):** `edge` → `chrome` → `firefox`

Puedes cambiar el orden con la variable de entorno **`BROWSER_ORDER`**, por ejemplo en `docker-compose.yml` para el servicio `celery_worker`:

```yaml
environment:
  - BROWSER_ORDER=firefox,chrome
```

En la imagen Docker están instalados **Chromium** y **Firefox ESR**. GeckoDriver (Firefox) lo descarga Selenium 4 automáticamente si no está. Edge no se incluye en Linux para evitar inestabilidad y uso extra de recursos.

---

## 7. Separación local vs Docker (una sola fuente de verdad)

No hay conflicto ni superposición entre el script “local” y el worker en Docker: **la misma base de código** se ejecuta en ambos; lo que cambia es el **entorno** (Windows vs Linux) y la **configuración** según ese entorno.

| | **Local (Windows)** | **Docker (Linux)** |
|---|---------------------|---------------------|
| **Cómo se ejecuta** | `manage.py unified_reporter --user-id N` | Celery: `execute_workflow_task` |
| **Navegadores por defecto** | Edge → Chrome → Firefox | Chrome (Chromium) → Firefox |
| **Headless** | No (visible) salvo `--headless` | Sí |
| **Timeout espera elementos** | 30 s | 120 s (headless tarda más en renderizar) |

Toda esta lógica está centralizada en **`backend/core/reporter_bot/docker_config.py`**:

- `IS_DOCKER`: detecta si se corre dentro del contenedor.
- `get_reporter_browser_order()`: orden de navegadores (o env `BROWSER_ORDER`).
- `get_downloader_wait_timeout()`: tiempo de espera para el dropdown "Acciones" y similares (120 s en Docker, 30 s en local).

Si el reporter funciona en local pero falla en Docker con *TimeoutException* en el click de descarga:

1. **Timeout y espera**: En Docker hay 120 s de espera y una espera extra de 5 s tras aplicar filtros antes de buscar "Acciones".
2. **Reintentos**: El downloader prueba hasta 4 selectores alternativos para el dropdown "Acciones"; si el primero agota el timeout, prueba los siguientes (25 s cada uno).
3. **Screenshot en fallo**: Si no se encuentra el dropdown o falla el click, se guarda una captura en `backend/results/screenshots/` (p. ej. `fail_acciones_dropdown_YYYYMMDD_HHMMSS.png` o `fail_click_download_...`). Revisar esa imagen ayuda a ver el estado real de la página en headless.

---

## Logs en Celery: qué esperar

Al ejecutar `docker compose logs -f celery_worker` deberías ver, **en este orden**:

1. **📥 PASO 3: DESCARGA - Iniciando...** → El flujo entró al paso de descarga (Mis Pedidos → Acciones → Orders with Products).
2. **📥 Intentando click en Acciones → Órdenes con Productos...** → El downloader va a buscar el dropdown.
3. **Uno de dos**:
   - **✅ PASO 3: DESCARGA OK - N archivos. Iniciando comparación.** → Descarga funcionó; luego verás PASO 4 y PASO 5.
   - **🛑 PASO 3: DESCARGA FALLIDA - Abortando.** → No se descargó nada; **no** se ejecutan Comparer ni Reporter.

Si ves **PASO 4** o **PASO 5** (o "No se encontraron batches anteriores", "Timeout Siguiente") **sin** haber visto antes "PASO 3: DESCARGA OK", entonces esa ejecución usó datos de una run anterior (o hay un bug). Cuando la descarga falla, el flujo termina y no llega a comparar ni reportar.

---

## Qué se guarda en la base de datos (datos de valor)

### Downloader

- **Filtros de fechas obligatorios**: En Mis Pedidos el bot debe **abrir el panel de filtros** (botón "Mostrar Filtros" / "Show Filters") y **configurar rango Desde/Hasta** (un mes hasta la fecha del reporte). Si no se aplican esos filtros, Dropi devuelve datos por defecto (~1k filas) en lugar del rango completo. El downloader ahora:
  - Prueba varios selectores para el botón de filtros y valida que los inputs de fecha queden visibles.
  - Siempre setea **Desde** y **Hasta** (no solo Desde) y verifica que los valores queden escritos antes de dar Ok.
  - Valida que los filtros quedaron aplicados antes de hacer clic en Acciones → Órdenes con Productos.
  - Si falla abrir filtros o setear fechas, **aborta** esa descarga (no continúa con Acciones). Revisa logs: `❌ No se pudo abrir el panel de filtros` o `❌ No se pudo configurar rango de fechas`. Screenshots en `backend/results/screenshots/` (p. ej. `fail_open_filters_...`, `fail_set_desde_...`).
- **No actualiza datos**: cada ejecución crea un **nuevo** `ReportBatch` (un batch por día; si ya existe batch de hoy o de ayer, no se vuelve a descargar).
- Cada fila del Excel se guarda como **`RawOrderSnapshot`** vinculada a ese batch (ID orden, teléfono, estado, producto, cliente, precios, SKU, tienda, fechas, etc.).
- La misma orden puede aparecer en **varios batches** (ayer y hoy); eso permite comparar estados.

### Comparador

- Compara el **batch más reciente (hoy)** con el **batch del día anterior (ayer)**.
- Marca como **sin movimiento** solo cuando: **mismo `dropi_order_id`** y **mismo `current_status`** en ambos días (no se consideran IDs sintéticos `NO-ID-*`).
- Guarda cada hallazgo en **`OrderMovementReport`**:
  - `batch` = batch de hoy
  - `snapshot` = foto de la orden de hoy (todos los campos del snapshot: teléfono, cliente, producto, estado, etc.)
  - `days_since_order` = días desde la fecha de la orden
  - `is_resolved` / `resolved_at` / `resolution_note` cuando se reporta o se resuelve

### Reporter y Result Manager

- Al reportar una orden en Dropi se **actualiza** `OrderMovementReport` (marca `is_resolved=True`, `resolved_at`, `resolution_note`).
- Se guarda o actualiza **`OrderReport`** con datos de valor para historial y análisis:
  - `order_phone`, `order_id`, `customer_name`, `product_name`, `order_state` (estado en Dropi), `days_since_order`
  - `status` = `reportado` / `error` / `cannot_generate_yet` / etc.
  - `next_attempt_time` cuando aplica (ej. “esperar un día sin movimiento”).

Con esto tienes historial de reportes, órdenes sin movimiento y datos útiles para análisis (por estado, por producto, por días, etc.).

---

## Zona horaria (BD y Docker)

La base de datos (Django con `USE_TZ=True`) guarda las fechas en **UTC**. Por eso en consultas directas puedes ver horas como 20:28 cuando en tu país son las 15:28 (ej. Colombia UTC-5).

Para ver fechas en **hora local** del servidor:

```powershell
docker compose exec backend python backend/check_reporter_db.py
```

El script muestra `ReportBatch`, `WorkflowProgress` y `OrderMovementReport` convirtiendo a hora local cuando el valor tiene timezone. Así puedes comprobar si los batches son de la ejecución reciente o de una anterior.

---

## Detener procesos y evitar zombies

En **modo desarrollo** (local o Docker) aparece junto a "Iniciar a Reportar" un botón **"Detener procesos"**. Sirve para:

- Revocar todas las tareas del reporter que estén **ejecutándose** en Celery (terminar el proceso).
- **Purgar la cola** de Celery para quitar tareas pendientes.

Así evitas procesos zombie o que un nuevo "Iniciar a Reportar" colisione con uno ya en marcha. El endpoint solo está permitido en desarrollo (`development` o `development_docker`).

### Comandos manuales (por si necesitas comprobar o detener desde terminal)

Desde la raíz del proyecto (donde está `docker-compose.yml`):

**1. Ver tareas activas del reporter (qué está ejecutándose ahora):**

```powershell
cd "c:\Users\guerr\OneDrive\Documentos\DropTools"
docker compose exec celery_worker celery -A droptools_backend inspect active
```

Verás por worker la lista de tareas con `id`, `name` (p. ej. `core.tasks.execute_workflow_task`), etc.

**2. Vaciar la cola (solo tareas pendientes, no las que ya están corriendo):**

```powershell
docker compose exec celery_worker celery -A droptools_backend purge
```

Responde `y` si pregunta confirmación. Esto borra las tareas en espera; las que ya están en ejecución siguen hasta terminar o hasta que las revoquemos.

**3. Revocar una tarea concreta (terminar una ejecución por su ID):**

Primero obtén el `id` de la tarea con el comando del punto 1. Luego:

```powershell
docker compose exec celery_worker celery -A droptools_backend control revoke <TASK_ID> --terminate
```

Sustituye `<TASK_ID>` por el UUID que salió en `inspect active` (ej. `3b068bf7-c89b-482a-8f14-80fcac6cd3dc`).

**4. Asegurarte de que no quede nada (recomendado antes de volver a dar a "Iniciar a Reportar"):**

- Usar el botón **"Detener procesos"** en la UI (modo desarrollo), o
- Ejecutar **inspect active** y, si hay tareas del reporter, revocarlas una a una con el comando del punto 3, y después **purge** (punto 2).
