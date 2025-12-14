# 🔧 GUÍA DE DESARROLLO - DAHELL INTELLIGENCE

**Versión:** 2.0  
**Última actualización:** 2025-12-14

---

## 📋 TABLA DE CONTENIDOS

1. [Configuración del Entorno](#configuración-del-entorno)
2. [Estructura del Proyecto](#estructura-del-proyecto)
3. [Convenciones de Código](#convenciones-de-código)
4. [Desarrollo Local](#desarrollo-local)
5. [Testing](#testing)
6. [Debugging](#debugging)
7. [Deployment](#deployment)

---

## 🛠️ CONFIGURACIÓN DEL ENTORNO

### Prerequisitos

- **Python 3.12+**
- **Docker Desktop** (Windows/Mac) o Docker Engine (Linux)
- **Git**
- **PostgreSQL Client** (opcional, para debugging)
- **VS Code** (recomendado) con extensiones:
  - Python
  - Django
  - Docker
  - PostgreSQL

### Instalación Paso a Paso

#### 1. Clonar el Repositorio
```bash
git clone [url_del_repositorio]
cd Dahell
```

#### 2. Crear Entorno Virtual
```bash
# Windows
python -m venv venv
.\activate_env.bat

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

#### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

#### 4. Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# === DROPI CREDENTIALS ===
DROPI_EMAIL=tu_email@ejemplo.com
DROPI_PASSWORD=tu_password
HEADLESS=False  # True para producción

# === DATABASE (Local) ===
POSTGRES_USER=dahell_admin
POSTGRES_PASSWORD=secure_password_123
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_DB=dahell_db

# === SCRAPER CONFIG ===
MAX_PRODUCTS=200
RAW_DIR=raw_data

# === DJANGO ===
DJANGO_SECRET_KEY=tu_secret_key_aqui
DEBUG=True
```

#### 5. Iniciar Docker
```bash
docker-compose up -d
```

#### 6. Verificar Instalación
```bash
# Verificar Docker
docker ps

# Verificar Python
python --version

# Verificar dependencias
pip check

# Ejecutar diagnóstico
python backend/manage.py diagnose_stats
```

---

## 📁 ESTRUCTURA DEL PROYECTO

### Directorio Raíz
```
Dahell/
├── backend/              # Django backend
├── docs/                 # Documentación
├── frontend/             # Frontend (futuro)
├── logs/                 # Logs de aplicación
├── raw_data/             # Datos crudos (JSONL)
├── backups/              # Backups de DB
├── cache_huggingface/    # Caché de modelos IA
├── venv/                 # Entorno virtual (NO SUBIR A GIT)
├── .env                  # Variables de entorno (NO SUBIR A GIT)
├── .gitignore            # Git ignore
├── docker-compose.yml    # Orquestación Docker
├── requirements.txt      # Dependencias Python
└── README.md             # Documentación principal
```

### Backend Django
```
backend/
├── manage.py                    # CLI de Django
├── dahell_backend/              # Configuración del proyecto
│   ├── settings.py              # Configuración
│   ├── urls.py                  # URLs principales
│   └── wsgi.py                  # WSGI config
└── core/                        # App principal
    ├── models.py                # Modelos de DB
    ├── views.py                 # Vistas
    ├── admin.py                 # Admin de Django
    └── management/commands/     # Comandos personalizados
        ├── scraper.py           # Scraper de Dropi
        ├── loader.py            # Carga a DB
        ├── vectorizer.py        # Generación de embeddings
        ├── clusterizer.py       # Clustering
        └── diagnose_stats.py    # Diagnóstico
```

---

## 📝 CONVENCIONES DE CÓDIGO

### Python

#### Estilo
- **PEP 8** para estilo de código
- **Type hints** cuando sea posible
- **Docstrings** para funciones y clases

```python
def process_product(product_id: int, data: dict) -> bool:
    """
    Procesa un producto y lo guarda en la base de datos.
    
    Args:
        product_id: ID único del producto
        data: Diccionario con datos del producto
        
    Returns:
        True si se procesó correctamente, False en caso contrario
    """
    try:
        # Código aquí
        return True
    except Exception as e:
        logger.error(f"Error procesando producto {product_id}: {e}")
        return False
```

#### Logging
```python
import logging

logger = logging.getLogger(__name__)

# Niveles de logging
logger.debug("Información detallada para debugging")
logger.info("Información general")
logger.warning("Advertencia")
logger.error("Error")
logger.critical("Error crítico")
```

#### Encoding
**SIEMPRE usar UTF-8:**
```python
# Al abrir archivos
with open('archivo.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Al conectar a DB
conn = psycopg2.connect(
    dbname=dbname,
    user=user,
    password=password,
    client_encoding='UTF8'
)
```

### SQL

```sql
-- Usar nombres descriptivos
SELECT 
    p.product_id,
    p.title,
    p.sale_price
FROM products p
WHERE p.sale_price > 10000
ORDER BY p.sale_price DESC;

-- Evitar SELECT *
-- Usar aliases claros
-- Indentar correctamente
```

### Git

#### Commits
```bash
# Formato: tipo(scope): mensaje

# Ejemplos:
git commit -m "feat(scraper): agregar auto-relogin"
git commit -m "fix(loader): corregir encoding UTF-8"
git commit -m "docs(readme): actualizar guía de instalación"
git commit -m "refactor(vectorizer): optimizar carga de modelo"
```

#### Tipos de Commit
- `feat`: Nueva funcionalidad
- `fix`: Corrección de bug
- `docs`: Documentación
- `style`: Formato, sin cambios de código
- `refactor`: Refactorización
- `test`: Tests
- `chore`: Mantenimiento

---

## 💻 DESARROLLO LOCAL

### Workflow Típico

#### 1. Activar Entorno
```bash
.\activate_env.bat
```

#### 2. Iniciar Docker
```bash
docker-compose up -d
```

#### 3. Ejecutar Pipeline (4 Terminales)

**Terminal 1 - Scraper:**
```bash
.\venv\Scripts\python.exe backend/core/management/commands/scraper.py
```

**Terminal 2 - Loader:**
```bash
.\venv\Scripts\python.exe backend/core/management/commands/loader.py
```

**Terminal 3 - Vectorizer:**
```bash
.\venv\Scripts\python.exe backend/core/management/commands/vectorizer.py
```

**Terminal 4 - Clusterizer:**
```bash
.\venv\Scripts\python.exe backend/core/management/commands/clusterizer.py
```

#### 4. Monitorear Logs
```bash
# Ver logs de Docker
docker-compose logs -f

# Ver logs específicos
docker-compose logs -f vectorizer
docker-compose logs -f clusterizer
```

#### 5. Verificar Base de Datos
```bash
# Conectar a PostgreSQL
docker exec -it dahell_db psql -U dahell_admin -d dahell_db

# Queries útiles
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM product_embeddings WHERE embedding_visual IS NOT NULL;
SELECT COUNT(*) FROM unique_product_clusters;
```

---

## 🧪 TESTING

### Tests Unitarios

```python
# tests/test_loader.py
import unittest
from backend.core.management.commands.loader import ingest_record

class TestLoader(unittest.TestCase):
    def test_ingest_record(self):
        data = {
            "id": 123,
            "name": "Producto Test",
            "sale_price": 10000
        }
        result = ingest_record(data)
        self.assertTrue(result)
```

### Ejecutar Tests
```bash
# Todos los tests
python -m pytest

# Test específico
python -m pytest tests/test_loader.py

# Con coverage
python -m pytest --cov=backend
```

---

## 🐛 DEBUGGING

### VS Code Launch Configuration

Crear `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Scraper",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/backend/core/management/commands/scraper.py",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        },
        {
            "name": "Python: Loader",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/backend/core/management/commands/loader.py",
            "console": "integratedTerminal"
        }
    ]
}
```

### Debugging Tips

#### 1. Usar breakpoints
```python
import pdb; pdb.set_trace()  # Breakpoint
```

#### 2. Logging detallado
```python
logging.basicConfig(level=logging.DEBUG)
```

#### 3. Verificar variables de entorno
```python
import os
print(f"POSTGRES_HOST: {os.getenv('POSTGRES_HOST')}")
```

---

## 🚀 DEPLOYMENT

### Producción

#### 1. Configurar Variables de Entorno
```env
# .env (producción)
DEBUG=False
HEADLESS=True
POSTGRES_HOST=db  # Usar nombre del servicio Docker
```

#### 2. Build Docker
```bash
docker-compose build
```

#### 3. Iniciar Servicios
```bash
docker-compose up -d
```

#### 4. Verificar
```bash
docker ps
docker-compose logs -f
```

### Backup de Base de Datos

```bash
# Crear backup
docker exec dahell_db pg_dump -U dahell_admin dahell_db > backups/backup_$(date +%Y%m%d).sql

# Restaurar backup
docker exec -i dahell_db psql -U dahell_admin dahell_db < backups/backup_20251214.sql
```

---

## 📊 MONITOREO

### Métricas Clave

```sql
-- Productos en DB
SELECT COUNT(*) FROM products;

-- Productos vectorizados
SELECT COUNT(*) FROM product_embeddings WHERE embedding_visual IS NOT NULL;

-- Clusters formados
SELECT COUNT(*) FROM unique_product_clusters;

-- Cobertura de clustering
SELECT 
    COUNT(DISTINCT m.product_id) * 100.0 / COUNT(DISTINCT p.product_id) as coverage_pct
FROM products p
LEFT JOIN product_cluster_membership m ON p.product_id = m.product_id;
```

### Logs

```bash
# Ver logs en tiempo real
tail -f logs/scraper.log
tail -f logs/loader.log
tail -f logs/vectorizer.log
tail -f logs/clusterizer.log
```

---

## 🔒 SEGURIDAD

### Variables de Entorno

**NUNCA subir a Git:**
- `.env`
- Credenciales de Dropi
- Secrets de Django
- Passwords de DB

### Gitignore

Verificar que `.gitignore` incluye:
```
.env
.env.local
venv/
*.log
raw_data/*.jsonl
cache_huggingface/
```

---

## 📞 SOPORTE

### Problemas Comunes

Ver **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** para soluciones detalladas.

### Contacto

- **Issues:** [GitHub Issues]
- **Email:** [tu_email@ejemplo.com]
- **Documentación:** `docs/`

---

**Última actualización:** 2025-12-14  
**Mantenido por:** [Tu Nombre]
