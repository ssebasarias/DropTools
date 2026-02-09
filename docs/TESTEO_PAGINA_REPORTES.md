# Testeo final – Página de Reportes (Reporter)

Guía para verificar que el aplicativo funciona correctamente con la **página de reportes** (Configuración Reporter / Reporter Setup).

> **Nota:** Para un resumen de los cambios recientes (Google OAuth, reporter, componentes nuevos) y la verificación pre-testeo (lint, build, Django check), ver [CAMBIOS_PRE_TESTEO.md](./CAMBIOS_PRE_TESTEO.md).

## 1. Levantar el aplicativo

### Opción A: Docker (recomendado)

```powershell
cd c:\Users\guerr\OneDrive\Documentos\DropTools
docker-compose up -d backend db
```

- **Backend:** http://localhost:8000  
- **API:** http://localhost:8000/api/

Luego el frontend en local:

```powershell
cd frontend
npm run dev
```

- **Frontend:** http://localhost:5173  

### Opción B: Todo en local

1. **Base de datos:** PostgreSQL en puerto 5433 (o el que uses), con variables en `.env` / `.env.docker`.
2. **Backend:**
   ```powershell
   cd backend
   python manage.py runserver 0.0.0.0:8000
   ```
3. **Frontend:**
   ```powershell
   cd frontend
   npm run dev
   ```

Asegúrate de que `VITE_API_URL` (o el valor por defecto en `frontend/src/config/constants.js`) apunte a `http://localhost:8000/api` si el backend está en local.

---

## 2. Acceso a la página de reportes

1. Abre **http://localhost:5173**.
2. Inicia sesión (o regístrate) con un usuario que tenga al menos tier **BRONZE** (la página de reportes está protegida por suscripción).
3. En el menú de usuario, entra a **Reporter Setup** / **Configuración Reporter**.
4. La ruta directa es: **http://localhost:5173/user/reporter-setup**.

---

## 3. Checklist de testeo

Usa esta lista para el “último testeo” y comprobar que todo responde bien.

### Carga inicial

- [ ] La página carga sin error 404 ni pantalla en blanco.
- [ ] Se muestra el título **Reporter Configuration** y el subtítulo sobre “generación de reportes”.
- [ ] Si el backend está disponible, aparece el badge de modo (Desarrollo / Producción / Desarrollo Docker).
- [ ] No hay mensaje de error genérico en rojo por fallo de API (si el backend está caído, puede mostrarse un error controlado).

### Cuentas Dropi (worker)

- [ ] La sección de cuentas Dropi se carga (lista de cuentas o estado vacío).
- [ ] Si hay cuentas, se listan con email y estado (default, etc.).
- [ ] Formulario “Agregar cuenta”: email, contraseña, opción “usar como predeterminada”.
- [ ] Al enviar el formulario (con backend arriba), la cuenta se crea o se muestra un mensaje de error claro.
- [ ] Si el backend devuelve `proxy_assigned`, se muestra la IP/proxy asignada cuando corresponda.

### Configuración del reporter (hora)

- [ ] Se muestra la hora de ejecución actual (si existe en backend).
- [ ] Se puede cambiar la hora y guardar (si el backend lo permite).
- [ ] Tras guardar, el valor se actualiza en pantalla o se muestra confirmación/error.

### Slots y reservas

- [ ] La sección de **slots** (horas) carga (lista de slots o mensaje de “no slots”).
- [ ] Si hay slots, se muestran con hora y estado (disponible / ocupado / candado).
- [ ] Si no tienes reserva: se puede elegir un slot y (si aplica) estimación de órdenes mensuales, y confirmar reserva.
- [ ] Si ya tienes reserva: se muestra “Tu reporte se ejecuta diariamente a las HH:00” y opción de cancelar reserva.
- [ ] Tras crear o cancelar reserva, la vista se actualiza (tu reserva o la lista de slots).

### Estado y control del reporter

- [ ] **Estado:** se muestra “Reportes realizados hoy” y el número (o 0).
- [ ] Botón **Actualizar** (refresh) recarga estado, slots, reserva y lista de reportes sin error.
- [ ] **Iniciar reporter** (si está habilitado en tu entorno): el botón existe y al pulsar se inicia el flujo o se muestra mensaje/error del backend.
- [ ] En modo desarrollo: si aplica, el botón **Detener procesos** aparece y responde según backend.

### Lista de órdenes reportadas

- [ ] La sección “Órdenes reportadas” carga (tabla o estado vacío).
- [ ] Si no hay reportes: se muestra el mensaje tipo “No hay órdenes reportadas aún” con explicación.
- [ ] Si hay reportes: se listan columnas como número de guía, teléfono, cliente, producto, días sin movimiento, fecha de reporte.
- [ ] Los “días sin movimiento” se colorean (verde / amarillo / rojo) según el valor.
- [ ] Paginación o scroll funcionan si hay muchos registros (según implementación).

### Errores y bordes

- [ ] Con **backend caído**: la página no rompe; se muestran mensajes de error o estados vacíos coherentes.
- [ ] Con **usuario sin tier BRONZE**: se muestra la puerta de suscripción (SubscriptionGate) en lugar del contenido completo.
- [ ] Navegación: volver al dashboard o a otras secciones del usuario funciona desde el menú.

---

## 4. Endpoints de API usados por la página

Para depurar o verificar con DevTools (pestaña Network):

| Recurso | Uso en la página |
|--------|-------------------|
| `GET /api/reporter/env/` | Modo (desarrollo/producción) |
| `GET /api/reporter/config/` | Hora de ejecución, proxy asignado |
| `GET /api/reporter/status/` | Estado y reportes realizados hoy |
| `GET /api/reporter/list/?page=1&page_size=50&status=reportado` | Lista de órdenes reportadas |
| `GET /api/reporter/slots/` | Slots disponibles |
| `GET /api/reporter/reservations/` | Mi reserva |
| `POST /api/reporter/reservations/` | Crear reserva |
| `DELETE /api/reporter/reservations/` | Cancelar reserva |
| `GET /api/reporter/runs/?days=7` | Últimas ejecuciones |
| `GET /api/dropi/accounts/` | Cuentas Dropi |

---

## 5. Resumen rápido

- **URL a probar:** http://localhost:5173/user/reporter-setup  
- **Requisito:** usuario autenticado con suscripción BRONZE o superior.  
- **Backend:** debe estar en http://localhost:8000 (o la URL configurada en el frontend) para que slots, reservas, lista de reportes y estado respondan bien.

Si todos los ítems del checklist se cumplen, el aplicativo está funcionando correctamente con la página de reportes para este testeo final.
