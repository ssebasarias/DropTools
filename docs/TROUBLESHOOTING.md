# 🐛 TROUBLESHOOTING - DAHELL INTELLIGENCE

**Versión:** 2.0  
**Última actualización:** 2025-12-14

---

## 📋 TABLA DE CONTENIDOS

1. [Problemas de Instalación](#problemas-de-instalación)
2. [Errores de Encoding](#errores-de-encoding)
3. [Errores de Conexión](#errores-de-conexión)
4. [Errores de Dependencias](#errores-de-dependencias)
5. [Errores de Docker](#errores-de-docker)
6. [Errores del Pipeline ETL](#errores-del-pipeline-etl)
7. [Diagnóstico y Logs](#diagnóstico-y-logs)

---

## 🔧 PROBLEMAS DE INSTALACIÓN

### ❌ Error: "Python no reconocido como comando"

**Síntoma:**
```
'python' no se reconoce como un comando interno o externo
```

**Solución:**
1. Verificar instalación de Python:
   ```bash
   python --version
   # o
   python3 --version
   ```

2. Agregar Python al PATH:
   - Windows: Configuración → Sistema → Variables de entorno
   - Agregar ruta de Python (ej: `C:\Python312\`)

3. Reiniciar terminal

---

### ❌ Error: "pip no encontrado"

**Síntoma:**
```
'pip' no se reconoce como un comando interno o externo
```

**Solución:**
```bash
# Reinstalar pip
python -m ensurepip --upgrade

# O usar python -m pip
python -m pip install -r requirements.txt
```

---

### ❌ Error: "No se puede crear venv"

**Síntoma:**
```
Error: Command '['venv\\Scripts\\python.exe', '-Im', 'ensurepip']' returned non-zero exit status 1
```

**Solución:**
```bash
# Eliminar venv existente
rm -rf venv

# Crear nuevo venv
python -m venv venv --clear

# Activar
.\activate_env.bat

# Reinstalar dependencias
pip install -r requirements.txt
```

---

## 🔤 ERRORES DE ENCODING

### ❌ Error: "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xf3"

**Síntoma:**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xf3 in position 79: invalid continuation byte
```

**Causa:**
- Archivos con encoding mixto (UTF-8 + Latin-1)
- Variables de entorno con caracteres especiales
- Conexión a DB sin encoding UTF-8

**Solución:**

#### 1. Activar entorno virtual (configura UTF-8 automáticamente)
```bash
.\activate_env.bat
```

#### 2. Verificar encoding en archivos Python
```python
# Al abrir archivos
with open('archivo.txt', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()
```

#### 3. Verificar conexión a DB
```python
conn = psycopg2.connect(
    dbname=str(dbname),
    user=str(user),
    password=str(password),
    client_encoding='UTF8'  # ← Importante
)
```

#### 4. Si persiste, limpiar archivos JSONL corruptos
```bash
# Mover archivos problemáticos
mv raw_data/*.jsonl raw_data/backup/

# Reiniciar scraper para generar nuevos archivos
```

---

### ❌ Error: "SyntaxError: Non-UTF-8 code starting with '\xff'"

**Síntoma:**
```
SyntaxError: Non-UTF-8 code starting with '\xff' in file
```

**Solución:**
1. Abrir archivo en VS Code
2. Cambiar encoding a UTF-8:
   - Click en encoding (esquina inferior derecha)
   - Seleccionar "Save with Encoding"
   - Elegir "UTF-8"

---

## 🔌 ERRORES DE CONEXIÓN

### ❌ Error: "Connection refused" (PostgreSQL)

**Síntoma:**
```
psycopg2.OperationalError: could not connect to server: Connection refused
```

**Causa:**
- Docker no está corriendo
- Puerto incorrecto
- Host incorrecto

**Solución:**

#### 1. Verificar Docker
```bash
docker ps
```

Si no hay contenedores:
```bash
docker-compose up -d
```

#### 2. Verificar puerto
```bash
# Ver puertos de PostgreSQL
docker ps | grep postgres

# Debería mostrar: 0.0.0.0:5433->5432/tcp
```

#### 3. Verificar variables de entorno (.env)
```env
POSTGRES_HOST=127.0.0.1  # Para local
POSTGRES_PORT=5433        # Puerto mapeado
```

#### 4. Probar conexión manual
```bash
docker exec -it dahell_db psql -U dahell_admin -d dahell_db
```

---

### ❌ Error: "password authentication failed"

**Síntoma:**
```
FATAL: password authentication failed for user "dahell_admin"
```

**Solución:**

#### 1. Verificar credenciales en .env
```env
POSTGRES_USER=dahell_admin
POSTGRES_PASSWORD=secure_password_123
```

#### 2. Reiniciar contenedor de DB
```bash
docker-compose down
docker-compose up -d
```

#### 3. Resetear password (si es necesario)
```bash
docker exec -it dahell_db psql -U postgres
```
```sql
ALTER USER dahell_admin WITH PASSWORD 'secure_password_123';
```

---

### ❌ Error: "No hay conexión DB. Reintentando en 10s..."

**Síntoma:**
```
[ERROR] No hay conexión DB. Reintentando en 10s...
```

**Causa:**
- Encoding incorrecto en variables de entorno
- DB no está lista
- Credenciales incorrectas

**Solución:**

#### 1. Verificar que DB está corriendo
```bash
docker ps | grep dahell_db
```

#### 2. Ver logs de DB
```bash
docker logs dahell_db
```

#### 3. Verificar encoding en código
```python
# En clusterizer.py y vectorizer.py
dbname = str(os.getenv("POSTGRES_DB", "dahell_db"))
user = str(os.getenv("POSTGRES_USER", "dahell_admin"))
password = str(os.getenv("POSTGRES_PASSWORD", "secure_password_123"))

conn = psycopg2.connect(
    dbname=dbname,
    user=user,
    password=password,
    client_encoding='UTF8'  # ← Usar parámetro directo
)
```

---

## 📦 ERRORES DE DEPENDENCIAS

### ❌ Error: "ModuleNotFoundError: No module named 'django'"

**Síntoma:**
```
ModuleNotFoundError: No module named 'django'
```

**Solución:**

#### 1. Activar entorno virtual
```bash
.\activate_env.bat
```

#### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

#### 3. Verificar instalación
```bash
pip list | grep django
```

---

### ❌ Error: "No matching distribution found for torchvision==0.21.1"

**Síntoma:**
```
ERROR: No matching distribution found for torchvision==0.21.1
```

**Causa:**
- Versión específica no disponible para tu plataforma

**Solución:**

#### 1. Usar versiones flexibles (ya corregido en requirements.txt)
```txt
torch>=2.0.0
torchvision>=0.15.0
```

#### 2. Reinstalar
```bash
pip install -r requirements.txt
```

---

### ❌ Error: "ImportError: DLL load failed"

**Síntoma:**
```
ImportError: DLL load failed while importing _ssl
```

**Solución:**

#### 1. Reinstalar Python
- Descargar Python 3.12 desde python.org
- Marcar "Add Python to PATH"
- Instalar

#### 2. Reinstalar dependencias
```bash
pip install --force-reinstall -r requirements.txt
```

---

## 🐳 ERRORES DE DOCKER

### ❌ Error: "docker: command not found"

**Síntoma:**
```
docker: command not found
```

**Solución:**
1. Instalar Docker Desktop (Windows/Mac)
2. O Docker Engine (Linux)
3. Reiniciar terminal
4. Verificar: `docker --version`

---

### ❌ Error: "Cannot connect to the Docker daemon"

**Síntoma:**
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Solución:**
1. Iniciar Docker Desktop
2. Esperar a que esté completamente iniciado
3. Verificar: `docker ps`

---

### ❌ Error: "port is already allocated"

**Síntoma:**
```
Error starting userland proxy: listen tcp 0.0.0.0:5433: bind: address already in use
```

**Solución:**

#### 1. Ver qué está usando el puerto
```bash
# Windows
netstat -ano | findstr :5433

# Linux/Mac
lsof -i :5433
```

#### 2. Matar proceso
```bash
# Windows
taskkill /PID [PID] /F

# Linux/Mac
kill -9 [PID]
```

#### 3. O cambiar puerto en docker-compose.yml
```yaml
ports:
  - "5434:5432"  # Cambiar 5433 a 5434
```

---

## 🔄 ERRORES DEL PIPELINE ETL

### ❌ Scraper: "selenium.common.exceptions.WebDriverException"

**Síntoma:**
```
WebDriverException: Message: 'chromedriver' executable needs to be in PATH
```

**Solución:**
```bash
# Reinstalar webdriver-manager
pip install --upgrade webdriver-manager

# Limpiar caché
rm -rf ~/.wdm
```

---

### ❌ Loader: "Error line X: 'utf-8' codec can't decode"

**Síntoma:**
```
Error line 10360: 'utf-8' codec can't decode byte 0xf3
```

**Causa:**
- Archivos JSONL con encoding mixto (NORMAL)

**Solución:**
- **Ya está manejado** en el código con `errors='replace'`
- El loader continuará procesando y reportará errores
- No requiere acción

**Verificar:**
```bash
# Ver logs del loader
# Debería mostrar: "Done. Valid records: X, Errors: Y"
```

---

### ❌ Vectorizer: "❌ Error en ciclo vectorizer"

**Síntoma:**
```
[ERROR] ❌ Error en ciclo vectorizer (Ver vectorizer_error.log)
```

**Solución:**

#### 1. Ver log de error
```bash
cat vectorizer_error.log
```

#### 2. Errores comunes:

**a) Encoding UTF-8:**
```python
# Verificar en vectorizer.py (línea 58-67)
client_encoding='UTF8'  # Debe usar parámetro directo
```

**b) Modelo no descargado:**
```bash
# Limpiar caché y reintentar
rm -rf cache_huggingface/
```

**c) Sin memoria:**
```python
# Reducir batch size en vectorizer.py
LIMIT 50  # En lugar de 100
```

---

### ❌ Clusterizer: "No hay conexión DB"

**Ver sección:** [Errores de Conexión](#errores-de-conexión)

---

## 📊 DIAGNÓSTICO Y LOGS

### Verificar Estado del Sistema

```bash
# 1. Verificar Docker
docker ps

# 2. Verificar Python
python --version

# 3. Verificar venv
which python  # Linux/Mac
where python  # Windows

# 4. Verificar dependencias
pip check

# 5. Ejecutar diagnóstico
python backend/manage.py diagnose_stats
```

---

### Ver Logs

#### Logs de Docker
```bash
# Todos los servicios
docker-compose logs -f

# Servicio específico
docker-compose logs -f dahell_db
docker-compose logs -f vectorizer
docker-compose logs -f clusterizer
```

#### Logs de Aplicación
```bash
# Windows
Get-Content logs\scraper.log -Tail 50 -Wait

# Linux/Mac
tail -f logs/scraper.log
```

#### Logs de Error
```bash
cat vectorizer_error.log
cat clusterizer_error.log
```

---

### Verificar Base de Datos

```bash
# Conectar a PostgreSQL
docker exec -it dahell_db psql -U dahell_admin -d dahell_db
```

```sql
-- Ver tablas
\dt

-- Contar productos
SELECT COUNT(*) FROM products;

-- Contar vectores
SELECT COUNT(*) FROM product_embeddings WHERE embedding_visual IS NOT NULL;

-- Contar clusters
SELECT COUNT(*) FROM unique_product_clusters;

-- Ver cobertura de clustering
SELECT 
    COUNT(DISTINCT m.product_id) * 100.0 / COUNT(DISTINCT p.product_id) as coverage_pct
FROM products p
LEFT JOIN product_cluster_membership m ON p.product_id = m.product_id;
```

---

### Reiniciar Todo

Si nada funciona, reiniciar completamente:

```bash
# 1. Detener procesos Python
.\reiniciar_procesos.ps1

# 2. Detener Docker
docker-compose down

# 3. Limpiar (CUIDADO: Elimina datos)
docker-compose down -v  # Elimina volúmenes
rm -rf raw_data/*.jsonl
rm -rf cache_huggingface/*

# 4. Reiniciar Docker
docker-compose up -d

# 5. Reiniciar pipeline (4 terminales)
# Ver GUIA_COMANDOS.md
```

---

## 📞 OBTENER AYUDA

### Antes de Reportar un Bug

1. ✅ Verificar que seguiste [INICIO_RAPIDO.md](../INICIO_RAPIDO.md)
2. ✅ Revisar esta guía de troubleshooting
3. ✅ Verificar logs de error
4. ✅ Buscar en Issues de GitHub

### Reportar un Bug

Incluir:
- **Descripción del problema**
- **Pasos para reproducir**
- **Logs relevantes** (copiar/pegar)
- **Entorno:**
  - OS: Windows/Linux/Mac
  - Python version: `python --version`
  - Docker version: `docker --version`
- **Archivos de configuración** (sin credenciales)

---

## 🔗 RECURSOS ADICIONALES

- **[GUIA_COMANDOS.md](GUIA_COMANDOS.md)** - Referencia de comandos
- **[GUIA_DESARROLLO.md](GUIA_DESARROLLO.md)** - Configuración de desarrollo
- **[ARQUITECTURA.md](ARQUITECTURA.md)** - Arquitectura del sistema

---

**Última actualización:** 2025-12-14  
**Mantenido por:** [Tu Nombre]
