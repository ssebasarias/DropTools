# 📚 GUÍA DE COMANDOS - DAHELL INTELLIGENCE

**Versión:** 2.1 (Optimizado)  
**Última actualización:** 2025-12-15

---

## 🎯 INICIO RÁPIDO

### 1. Activar Entorno Virtual (SIEMPRE PRIMERO)
```bash
.\activate_env.bat
```

### 2. Verificar Estado del Sistema
```bash
python backend/manage.py diagnose_stats
```

### 3. Ejecutar Pipeline Completo
```bash
# Terminal 1: Scraper (Extracción)
python backend/manage.py scraper

# Terminal 2: Loader (Carga a DB)
python backend/manage.py loader

# Terminal 3: Vectorizer (IA - Embeddings)
python backend/manage.py vectorizer

# Terminal 4: Clusterizer (Agrupación)
python backend/manage.py clusterizer
```

---

## 📋 COMANDOS POR CATEGORÍA

### 🔧 Gestión del Entorno

#### Activar venv
```bash
.\activate_env.bat
```

#### Desactivar venv
```bash
deactivate
```

#### Verificar venv activo
```bash
# Deberías ver (venv) al inicio de la línea
# Verificar Python del venv:
python --version
pip --version
```

#### Instalar/Actualizar dependencias
```bash
# Activar venv primero
.\activate_env.bat

# Instalar todas las dependencias
pip install -r requirements.txt

# Actualizar una dependencia específica
pip install --upgrade [nombre_paquete]

# Ver dependencias instaladas
pip list

# Verificar integridad
pip check
```

---

### 🗄️ Gestión de Base de Datos

#### Conectarse a PostgreSQL (Docker)
```bash
# Conectar con psql
docker exec -it dahell_db psql -U dahell_admin -d dahell_db

# Ejecutar comando SQL directo
docker exec dahell_db psql -U dahell_admin -d dahell_db -c "SELECT COUNT(*) FROM products;"
```

#### Verificar estado de la DB
```bash
# Ver bases de datos
docker exec dahell_db psql -U dahell_admin -d dahell_db -c "\l"

# Ver tablas
docker exec dahell_db psql -U dahell_admin -d dahell_db -c "\dt"

# Ver tamaño de tablas
docker exec dahell_db psql -U dahell_admin -d dahell_db -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

#### Backup y Restore
```bash
# Crear backup
docker exec dahell_db pg_dump -U dahell_admin dahell_db > backup_$(date +%Y%m%d).sql

# Restaurar backup
docker exec -i dahell_db psql -U dahell_admin dahell_db < backup_20251214.sql
```

#### Borrar todos los datos excepto usuarios
Deja la base de datos en cero (reportes, órdenes, productos, clusters, sesiones, etc.) y **conserva solo la tabla de usuarios** (`users`: login, rol, suscripción, credenciales Dropi).

```bash
# Desde el host (con backend en Docker)
docker compose exec backend python backend/manage.py clear_data_keep_users

# Opcional: no borrar sesiones (los usuarios no tendrán que volver a iniciar sesión)
docker compose exec backend python backend/manage.py clear_data_keep_users --no-sessions

# Solo ver qué se borraría, sin ejecutar
docker compose exec backend python backend/manage.py clear_data_keep_users --dry-run
```

Desde entorno local (venv activado):

```bash
python backend/manage.py clear_data_keep_users
python backend/manage.py clear_data_keep_users --no-sessions
python backend/manage.py clear_data_keep_users --dry-run
```

#### Verificar que no queden registros (SELECT / conteos)
Después de `clear_data_keep_users` puedes comprobar que las tablas quedaron vacías (excepto `users`) con SQL o con el comando Django que sigue.

**Conteos por tabla (psql):**

```bash
# Conectar a la DB y ejecutar SELECTs
docker exec -it dahell_db psql -U dahell_admin -d dahell_db -c "
SELECT 'raw_order_snapshots' AS tabla, COUNT(*) AS registros FROM raw_order_snapshots
UNION ALL SELECT 'report_batches', COUNT(*) FROM report_batches
UNION ALL SELECT 'order_reports', COUNT(*) FROM order_reports
UNION ALL SELECT 'workflow_progress', COUNT(*) FROM workflow_progress
UNION ALL SELECT 'order_movement_reports', COUNT(*) FROM order_movement_reports
UNION ALL SELECT 'users', COUNT(*) FROM users
ORDER BY tabla;
"
```

**Estimado de filas en todas las tablas (estadísticas de PostgreSQL):**

```bash
docker exec dahell_db psql -U dahell_admin -d dahell_db -c "
SELECT relname AS tabla, n_live_tup AS registros_aprox
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;
"
```

**Solo una tabla (ej. snapshots):**

```bash
docker exec dahell_db psql -U dahell_admin -d dahell_db -c "SELECT COUNT(*) FROM raw_order_snapshots;"
```

**Con Django (conteos de las tablas que vacía `clear_data_keep_users`):**

```bash
docker compose exec backend python backend/manage.py show_table_counts
```

#### Reset completo de la base de datos (empezar de cero)
Útil para dejar la DB vacía y aplicar todas las migraciones desde el principio (incluidas las de Reporter: `ReportBatch`, `RawOrderSnapshot`, `OrderReport`, etc.).

```bash
# 1. Bajar todos los servicios y eliminar volúmenes (borra datos de PostgreSQL)
docker compose down -v

# 2. Levantar de nuevo (DB se crea vacía y se ejecuta init.sql si existe)
docker compose up -d

# 3. Esperar unos segundos a que la DB acepte conexiones, luego aplicar migraciones
docker compose exec backend python backend/manage.py migrate

# Si init.sql ya creó tablas y migrate falla por "table already exists", marcar migraciones iniciales como aplicadas y aplicar el resto:
# docker compose exec backend python backend/manage.py migrate --fake-initial

# 4. Verificar migraciones de la app core
docker compose exec backend python backend/manage.py showmigrations core
```

**Si migrate falla con "relation already exists" o "column does not exist" (contenttypes, etc.):**  
La base de datos fue creada por `init.sql` con un esquema que no coincide con el historial de migraciones de Django (p. ej. `django_content_type` sin columna `name`). En ese caso **la migración core 0006 no llega a ejecutarse** y en `raw_order_snapshots` puede faltar la columna `customer_email`.

**Solución rápida (añadir columnas a mano en `raw_order_snapshots`):**

```bash
# Linux / macOS (bash)
docker exec -i dahell_db psql -U dahell_admin -d dahell_db < scripts/add_raw_order_snapshot_columns.sql
```

```powershell
# Windows PowerShell (el operador < no redirige; usar tubería)
Get-Content scripts/add_raw_order_snapshot_columns.sql -Raw | docker exec -i dahell_db psql -U dahell_admin -d dahell_db
```

Así el downloader de reportes puede guardar snapshots sin depender de que las migraciones de contenttypes/auth pasen.

**Si quieres intentar que migrate pase:** puedes marcar como aplicadas las migraciones que fallen (fake) una a una, hasta que Django llegue a core. Por ejemplo, tras `migrate --fake-initial`, si falla en `contenttypes.0002`, ejecuta `migrate contenttypes 0002 --fake` y luego `migrate` de nuevo; repite para cada error. Es frágil si init.sql y Django no coinciden.

#### Reconstruir contenedores tras cambios de código
Después de modificar código Python (backend, Celery, reporter_bot, etc.) hay que reconstruir y reiniciar los contenedores afectados para que carguen los cambios:

```bash
# Reconstruir y levantar backend y celery_worker (monitoreo CPU/RAM en logs, reporter, downloader, comparer)
docker compose up -d --build backend celery_worker

# Solo reiniciar sin reconstruir imagen (si no cambiaste Dockerfile ni dependencias)
docker compose restart backend celery_worker
```

---

### 🐳 Gestión de Docker

#### Ver contenedores
```bash
# Ver contenedores activos
docker ps

# Ver todos los contenedores
docker ps -a
```

#### Iniciar/Detener servicios
```bash
# Iniciar todos los servicios
docker-compose up -d

# Detener todos los servicios
docker-compose down

# Reiniciar un servicio específico
docker compose restart db
docker compose restart pgadmin

# Reconstruir contenedores que sufrieron cambios de código (ver sección "Reset completo" arriba)
docker compose up -d --build backend celery_worker
```

#### Ver logs
```bash
# Logs de la base de datos
docker-compose logs -f db

# Logs de pgAdmin
docker-compose logs -f pgadmin

# Logs de todos los servicios
docker-compose logs -f

# logs de celery
docker compose logs -f celery_worker
```

#### Acceder a pgAdmin
```bash
# Abrir en navegador:
http://localhost:5050

# Credenciales (definidas en .env):
Email: admin@dahell.com
Password: admin
```

---

### 🕷️ ETL Pipeline (Extracción, Transformación, Carga)

#### 1. Scraper (Extracción de Dropi)
```bash
# Activar venv
.\activate_env.bat

# Ejecutar scraper
python backend/manage.py scraper

# Opciones (editar en .env):
# HEADLESS_MODE=True   → Sin ventana del navegador
# HEADLESS_MODE=False  → Con ventana visible (para debugging)
# MAX_PRODUCTS=200     → Límite de productos a extraer
```

**Salida:** Archivos JSONL en `raw_data/raw_products_YYYYMMDD.jsonl`

#### 2. Loader (Carga a Base de Datos)
```bash
# Activar venv
.\activate_env.bat

# Ejecutar loader (modo daemon)
python backend/manage.py loader

# El loader:
# - Lee archivos .jsonl de raw_data/
# - Inserta/actualiza productos en la DB
# - Corre en loop infinito (revisa cada 60s)
```

**Nota:** El loader corre continuamente. Detener con `Ctrl+C`.

#### 3. Vectorizer (Generación de Embeddings con IA)
```bash
# Activar venv
.\activate_env.bat

# Ejecutar vectorizer
python backend/manage.py vectorizer

# El vectorizer:
# - Descarga imágenes de productos
# - Genera embeddings con CLIP (512 dimensiones)
# - Almacena vectores en product_embeddings
# - Corre en loop infinito
```

**Requisitos:**
- GPU NVIDIA (opcional, acelera el proceso)
- Modelo CLIP se descarga automáticamente (~350MB)

#### 4. Clusterizer (Agrupación de Productos)
```bash
# Activar venv
.\activate_env.bat

# Ejecutar clusterizer
python backend/manage.py clusterizer

# El clusterizer:
# - Fase 1: Hard clustering (bodega + SKU)
# - Fase 2: Soft clustering (IA visual + texto)
# - Calcula métricas de saturación
# - Corre en loop infinito
```

---

### 📊 Diagnóstico y Monitoreo

#### Diagnóstico completo del sistema
```bash
.\activate_env.bat
python backend/manage.py diagnose_stats
```

**Muestra:**
- Total de productos en DB
- Productos con imágenes
- Vectores generados
- Clusters creados
- Top proveedores

#### Verificar encoding
```bash
.\activate_env.bat
python verificar_encoding.py
```

#### Probar conexión a DB
```bash
.\activate_env.bat
python -c "from config_encoding import setup_utf8; import psycopg2; conn = psycopg2.connect(dbname='dahell_db', user='dahell_admin', password='secure_password_123', host='127.0.0.1', port='5433'); print('✅ Conexión exitosa'); conn.close()"
```

---

### 🌐 Django (Backend Web)

#### Servidor de desarrollo
```bash
.\activate_env.bat
cd backend
python manage.py runserver
```

**Acceder:** http://localhost:8000

#### Crear superusuario (Admin)
```bash
.\activate_env.bat
cd backend
python manage.py createsuperuser
```

#### Acceder al Admin de Django
```bash
# Primero crear superusuario (ver arriba)
# Luego iniciar servidor:
python manage.py runserver

# Abrir en navegador:
http://localhost:8000/admin
```

#### Migraciones (si es necesario)
```bash
.\activate_env.bat
cd backend
python manage.py makemigrations
python manage.py migrate
```

**Nota:** Los modelos tienen `managed=False`, por lo que Django no crea/modifica tablas. El esquema se define en `dahell_db.sql`.

---

### 📈 Dashboard (Streamlit)

#### Ejecutar dashboard local
```bash
.\activate_env.bat
streamlit run scripts/dashboard.py
```

**Acceder:** http://localhost:8501

#### Dashboard en Docker
```bash
# Iniciar servicio
docker-compose up -d dashboard

# Ver logs
docker-compose logs -f dashboard
```

**Acceder:** http://localhost:8501

---

## 🔄 FLUJO DE TRABAJO TÍPICO

### Configuración Inicial (Solo una vez)
```bash
# 1. Clonar repositorio (si aplica)
git clone [url]
cd Dahell

# 2. Crear y activar venv
python -m venv venv
.\activate_env.bat

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar .env
# Editar .env con tus credenciales

# 5. Iniciar Docker
docker-compose up -d

# 6. Verificar conexión
python backend/manage.py diagnose_stats
```

### Ejecución Diaria (4 Terminales)
```bash
# Terminal 1: Scraper
.\activate_env.bat
python backend/manage.py scraper

# Terminal 2: Loader
.\activate_env.bat
python backend/manage.py loader

# Terminal 3: Vectorizer
.\activate_env.bat
python backend/manage.py vectorizer

# Terminal 4: Clusterizer
.\activate_env.bat
python backend/manage.py clusterizer
```

### Monitoreo
```bash
# Terminal 5: Diagnóstico periódico
.\activate_env.bat
while ($true) { 
    python backend/manage.py diagnose_stats
    Start-Sleep -Seconds 300  # Cada 5 minutos
}
```

---

## 🐛 SOLUCIÓN DE PROBLEMAS

### Error: "ModuleNotFoundError"
```bash
# Verificar que el venv está activo
.\activate_env.bat

# Instalar el módulo faltante
pip install [nombre_modulo]
```

### Error: "Connection refused" (DB)
```bash
# Verificar que Docker está corriendo
docker ps

# Si no está corriendo:
docker-compose up -d

# Verificar puerto correcto en .env
# POSTGRES_PORT=5433
```

### Error: "UnicodeDecodeError"
```bash
# Verificar encoding UTF-8
python -c "import sys; print(sys.stdout.encoding)"

# Debería mostrar: utf-8
# Si no, usar activate_env.bat
```

### Scraper se detiene o falla
```bash
# Verificar credenciales en .env
# DROPI_EMAIL=...
# DROPI_PASSWORD=...

# Ejecutar en modo visible para debugging
# Editar .env: HEADLESS_MODE=False
```

### Vectorizer muy lento
```bash
# Verificar si usa GPU
python -c "import torch; print(f'CUDA disponible: {torch.cuda.is_available()}')"

# Si no hay GPU, es normal que sea lento
# Considerar ejecutar en servidor con GPU
```

---

## 📝 COMANDOS ÚTILES

### Ver espacio en disco
```bash
# Ver tamaño de raw_data/
du -sh raw_data/

# Ver tamaño de cache de modelos
du -sh cache_huggingface/
```

### Limpiar caché
```bash
# Limpiar caché de pip
pip cache purge

# Limpiar __pycache__
find . -type d -name __pycache__ -exec rm -rf {} +

# Limpiar archivos .pyc
find . -type f -name "*.pyc" -delete
```

### Git (Control de versiones)
```bash
# Ver estado
git status

# Agregar cambios
git add .

# Commit
git commit -m "Descripción de cambios"

# Push
git push origin main
```

---

## 🔐 VARIABLES DE ENTORNO (.env)

### Variables Principales
```env
# Base de Datos
POSTGRES_DB=dahell_db
POSTGRES_USER=dahell_admin
POSTGRES_PASSWORD=secure_password_123
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433

# Dropi (Scraper)
DROPI_EMAIL=tu_email@ejemplo.com
DROPI_PASSWORD=tu_contraseña
HEADLESS_MODE=False

# pgAdmin
PGADMIN_EMAIL=admin@dahell.com
PGADMIN_PASSWORD=admin
```

---

## 📚 DOCUMENTACIÓN ADICIONAL

- **`docs/GUIA_VENV.md`** - Guía detallada del entorno virtual
- **`docs/DIAGNOSTICO_SISTEMA.md`** - Diagnóstico completo del proyecto
- **`docs/NORMALIZACION_RESUMEN.md`** - Resumen de cambios de normalización
- **`pryecto.md`** - Descripción del proyecto y objetivos
- **`README.md`** - Documentación principal del proyecto

---

## 🎓 MEJORES PRÁCTICAS

### ✅ SIEMPRE:
1. Activar venv antes de trabajar: `.\activate_env.bat`
2. Usar UTF-8 en todos los archivos
3. Hacer backup de la DB antes de cambios importantes
4. Revisar logs si algo falla
5. Mantener Docker corriendo para la DB

### ❌ NUNCA:
1. Ejecutar scripts sin activar el venv
2. Editar directamente la DB (usar scripts)
3. Subir `.env` a Git (contiene credenciales)
4. Mezclar encodings (solo UTF-8)
5. Detener Docker mientras los scripts corren

---

## 🚀 COMANDOS DE PRODUCCIÓN

### Ejecutar en modo producción (sin logs verbosos)
```bash
# Scraper en background
nohup python backend/manage.py scraper > logs/scraper.log 2>&1 &

# Loader en background
nohup python backend/manage.py loader > logs/loader.log 2>&1 &

# Vectorizer en background
nohup python backend/manage.py vectorizer > logs/vectorizer.log 2>&1 &

# Clusterizer en background
nohup python backend/manage.py clusterizer > logs/clusterizer.log 2>&1 &
```

### Ver logs en producción
```bash
tail -f logs/scraper.log
tail -f logs/loader.log
tail -f logs/vectorizer.log
tail -f logs/clusterizer.log
```

---

## 📞 AYUDA Y SOPORTE

### Recursos
- Documentación Django: https://docs.djangoproject.com/
- Documentación PostgreSQL: https://www.postgresql.org/docs/
- Documentación Docker: https://docs.docker.com/

### Comandos de ayuda
```bash
# Ayuda de Django
python backend/manage.py help

# Ayuda de un comando específico
python backend/manage.py help scraper

# Ayuda de pip
pip help
```

---

**Última actualización:** 2025-12-14  
**Versión del proyecto:** 2.0 (Post-Normalización)
