# Instalación completa - DropTools

Sigue estos pasos **en tu terminal** (PowerShell o CMD) para dejar el repo listo y funcionando.

## Requisitos previos

- **Git**
- **Python 3.11+** (el proyecto recomienda 3.11; 3.14 puede dar problemas con ensurepip)
- **Node.js 18+** y npm
- **Docker Desktop** instalado y en ejecución

---

## 1. Variables de entorno

Ya están creados `.env` y `.env.docker` en la raíz del proyecto.

- **`.env`**: para desarrollo local (backend/frontend en tu PC, DB/Redis en Docker).  
  - `POSTGRES_HOST=localhost`, `POSTGRES_PORT=5433`
- **`.env.docker`**: para los contenedores.  
  - `POSTGRES_HOST=db`, `CELERY_BROKER_URL=redis://redis:6379/0`

**Qué debes editar tú:**

1. Abre `.env` y `.env.docker`.
2. Cambia **POSTGRES_PASSWORD** y **SECRET_KEY** por valores seguros.
3. Si usas Dropi: pon **DROPI_EMAIL** y **DROPI_PASSWORD**.
4. Opcional: cambia **PGADMIN_DEFAULT_PASSWORD** para pgAdmin.

---

## 2. Carpetas necesarias

Ya creadas en la raíz: `raw_data`, `logs`, `cache_huggingface`, `results`.  
Si no existieran:

```powershell
cd "c:\Users\guerr\OneDrive\Documentos\DropTools"
New-Item -ItemType Directory -Force -Path raw_data, logs, cache_huggingface, results
```

---

## 3. Entorno virtual Python (opcional para desarrollo local)

Si quieres ejecutar el backend o comandos Django en tu máquina (no en Docker):

```powershell
cd "c:\Users\guerr\OneDrive\Documentos\DropTools"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si `python -m venv venv` falla (por ejemplo con Python 3.14 o permisos), usa **Python 3.11** o 3.12:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 4. Frontend (npm)

```powershell
cd "c:\Users\guerr\OneDrive\Documentos\DropTools\frontend"
npm install
cd ..
```

---

## 5. Crear la imagen Docker (opcional)

Si quieres **solo construir la imagen** del backend (sin levantar contenedores):

```powershell
cd "c:\Users\guerr\OneDrive\Documentos\DropTools"
docker build -t droptools-backend:latest --target selenium .
```

O usar el script:

```powershell
.\scripts\build_docker_image.ps1
```

La imagen usa el target **selenium** (Python 3.11, Chromium, dependencias del backend).  
La primera vez puede tardar varios minutos (descarga de capas base e instalación de paquetes).

---

## 6. Levantar Docker

Con Docker Desktop abierto:

```powershell
cd "c:\Users\guerr\OneDrive\Documentos\DropTools"
docker compose up -d --build
```

Esto levanta: **PostgreSQL**, **Redis**, **backend** (Django), **Celery worker**, **Flower**, **pgAdmin** y **frontend** (Vite).  
`--build` construye las imágenes si no existen. La primera vez puede tardar varios minutos.

---

## 7. Migraciones y usuarios iniciales

Cuando los contenedores estén en ejecución:

```powershell
docker compose exec backend python manage.py migrate
```

Crear superusuario de administración:

```powershell
docker compose exec backend python manage.py createsuperuser
```

Si quieres usuarios de prueba desde `scripts/reporter_test_users.json`, puedes cargarlos con shell:

```powershell
docker compose exec backend python backend/manage.py shell -c "import json; from django.contrib.auth import get_user_model; U=get_user_model(); data=json.load(open('scripts/reporter_test_users.json',encoding='utf-8')); 
for row in data:
    email=(row.get('email') or '').strip().lower()
    if not email: 
        continue
    user, created = U.objects.get_or_create(username=email, defaults={'email': email})
    user.full_name = row.get('full_name') or row.get('name') or ''
    user.role = row.get('role') or 'CLIENT'
    user.subscription_tier = row.get('subscription_tier') or 'BRONZE'
    user.subscription_active = bool(row.get('subscription_active', True))
    user.dropi_email = row.get('dropi_email') or ''
    pwd = (row.get('dropi_password') or '').strip()
    if pwd:
        user.set_dropi_password_plain(pwd)
    app_pwd = (row.get('password') or '').strip()
    if app_pwd:
        user.set_password(app_pwd)
    user.save()
print('Usuarios de prueba cargados/actualizados')"
```

---

## 8. Comprobar que todo funciona

| Servicio       | URL                      |
|----------------|--------------------------|
| Frontend       | http://localhost:5173    |
| Backend API    | http://localhost:8000   |
| Django Admin  | http://localhost:8000/admin |
| Flower (Celery)| http://localhost:5555   |
| pgAdmin       | http://localhost:5050   |

- Abre http://localhost:5173 y deberías ver la app.
- Abre http://localhost:8000/admin e inicia sesión con el superusuario.

---

## Comandos útiles

```powershell
# Ver logs de todos los servicios
docker compose logs -f

# Solo backend
docker compose logs -f backend

# Detener todo
docker compose down
```

---

## Si algo falla

- **"Connection refused" a la base de datos**: comprueba que el contenedor `droptools_db` esté en marcha (`docker ps`).
- **Error al construir la imagen**: revisa que Docker tenga suficiente memoria (recomendado ≥ 4 GB para el frontend/backend).
- **Puerto en uso**: cambia en `docker-compose.yml` el mapeo de puertos (por ejemplo `"5434:5432"` para la DB) y en `.env` local usa ese puerto en `POSTGRES_PORT`.

Más detalles: [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md).
