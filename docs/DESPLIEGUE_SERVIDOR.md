# Despliegue en el servidor (post-pull)

Guía para actualizar el proyecto en el VPS después de hacer `git pull`. El repo es la fuente de verdad; en el servidor no deberían hacerse ediciones manuales de `docker-compose.production.yml`, `frontend/vite.config.js` ni `nginx/nginx.conf` salvo overrides puntuales (p. ej. certificados SSL).

## Antes del pull

Si hay cambios locales en el servidor que impiden `git pull` (por ejemplo en `docker-compose.production.yml`, `frontend/vite.config.js`, `nginx/nginx.conf`), elige una opción:

### Opción A: Guardar cambios locales y traer el repo

```bash
cd /opt/DropTools   # o la ruta donde esté el proyecto
git stash push -m "server local" -- docker-compose.production.yml frontend/vite.config.js nginx/nginx.conf
git pull
```

Si el repo ya incluye toda la configuración necesaria, **no** hagas `git stash pop`; los archivos del repo son los correctos. Si necesitas recuperar algo del stash: `git stash pop` y resuelve conflictos a mano.

### Opción B: Descartar cambios locales y traer el repo

```bash
cd /opt/DropTools
git checkout -- docker-compose.production.yml frontend/vite.config.js nginx/nginx.conf
git pull
```

## Después del pull

1. Ir al directorio del proyecto:
   ```bash
   cd /opt/DropTools
   ```

2. Recrear frontend y backend para que carguen la nueva configuración:
   ```bash
   docker compose -f docker-compose.production.yml up -d frontend backend --force-recreate
   ```

3. Recargar Nginx para aplicar cambios en `nginx.conf`:
   ```bash
   docker compose -f docker-compose.production.yml exec nginx nginx -s reload
   ```

## Variables de entorno en el servidor

El archivo `.env.production` **no** se versiona (está en `.gitignore`). Debe existir en el servidor con al menos:

- `SECRET_KEY` (obligatorio en producción)
- `POSTGRES_*`, `ALLOWED_HOSTS`, etc., según tu entorno

Opcionalmente puedes definir `CSRF_TRUSTED_ORIGINS` y `GOOGLE_REDIRECT_URI`; si no, el código usa valores por defecto para `droptools.cloud`.

## Comprobación rápida

1. Login como admin en `https://droptools.cloud/login` → debe redirigir al panel del frontend en `/admin`.
2. En el panel admin, el enlace "Django Admin" debe abrir `https://droptools.cloud/django-admin/` (en nueva pestaña).
