# 🚀 DropTools

**Sistema de Análisis de Saturación de Mercado para Dropshipping con IA**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.x-green.svg)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue.svg)](https://www.docker.com/)

---

## 📋 ¿Qué es DropTools?

Sistema de inteligencia artificial que detecta la saturación de mercado en productos de dropshipping. Utiliza embeddings vectoriales (CLIP) para identificar productos idénticos vendidos por diferentes proveedores, permitiendo encontrar **oportunidades de negocio con baja competencia**.

### 🎯 Problema que Resuelve

**Desafío:** Un mismo producto físico es vendido por múltiples proveedores usando diferentes nombres y fotos, haciendo difícil evaluar la competencia real.

**Solución:** Usar IA (embeddings vectoriales) para "ver" y "leer" productos. Si dos productos tienen vectores similares, son el mismo producto.

**Valor:** Identificar productos con alta demanda pero baja competencia (oportunidades de oro 💰).

---

## 📦 Clonar e instalar en otro equipo

Sigue estos pasos para replicar el proyecto tal cual en otra máquina (Windows, Linux o Mac).

> **Nota:** El proyecto se llama **DropTools**. Repositorio: `https://github.com/ssebasarias/DropTools.git`. Producción: **https://droptools.cloud**

### Prerrequisitos

- **Git**
- **Python 3.11+** (para desarrollo local del backend)
- **Node.js 18+** y npm (para el frontend React)
- **Docker y Docker Compose** (para base de datos, Redis, backend y frontend en contenedores)

### 1. Clonar el repositorio

```bash
git clone https://github.com/ssebasarias/DropTools.git
cd DropTools
```

### 2. Variables de entorno

Crea los archivos de entorno a partir del ejemplo (nunca subas `.env` ni `.env.docker` a Git):

```bash
# Copiar plantilla
cp .env.example .env

# Para Docker (base de datos, backend, Celery, etc.)
cp .env.example .env.docker
```

Edita `.env` y `.env.docker` con tus valores:

- **POSTGRES_PASSWORD** y **SECRET_KEY**: cambia por valores seguros.
- **DROPI_EMAIL** y **DROPI_PASSWORD**: credenciales de Dropi para el reporter.
- En `.env.docker`, **POSTGRES_HOST=db** y **CELERY_BROKER_URL=redis://redis:6379/0** (nombres de servicio Docker).

### 3. Backend (Python)

```bash
# Crear y activar entorno virtual

# Windows (PowerShell o CMD)
python -m venv venv
.\venv\Scripts\activate
# o usar:  .\scripts\activate_env.bat

# Linux / Mac
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 4. Frontend (React + Vite)

```bash
cd frontend
npm install
cd ..
```

### 5. Levantar servicios con Docker

Asegúrate de tener `.env.docker` configurado (o que Docker use las variables necesarias). Luego:

```bash
docker compose up -d
```

Esto levanta: PostgreSQL, Redis, backend Django, Celery worker, Flower y frontend. La base de datos se inicializa con `docs/droptools_db.sql` si existe en el primer arranque.

### 6. Migraciones (si corres backend fuera de Docker)

Si en algún momento ejecutas Django en local (no en contenedor), aplica migraciones:

```bash
# Con venv activado, desde la raíz del proyecto
cd backend
python manage.py migrate
cd ..
```

Si todo corre en Docker, el backend en el contenedor puede ejecutar migraciones al iniciar (o hazlo una vez con `docker compose exec backend python manage.py migrate`).

### 7. Crear superusuario (opcional)

Para acceder al admin de Django:

```bash
# Con Docker
docker compose exec backend python manage.py createsuperuser

# O en local (venv activado)
cd backend && python manage.py createsuperuser && cd ..
```

### 8. URLs de los servicios

| Servicio    | URL                    |
|------------|-------------------------|
| Frontend   | http://localhost:5173   |
| Backend API| http://localhost:8000   |
| Django Admin | http://localhost:8000/admin |
| Flower (Celery) | http://localhost:5555 |
| pgAdmin   | http://localhost:5050   |

### 9. Desarrollo local sin Docker (opcional)

- **Base de datos:** necesitas PostgreSQL y Redis en local (o solo levantar `db` y `redis` con Docker).
- **Backend:** con venv activado: `cd backend && python manage.py runserver`.
- **Frontend:** `cd frontend && npm run dev`.
- Ajusta en `.env`: `POSTGRES_HOST=localhost`, `CELERY_BROKER_URL=redis://localhost:6379/0`.

---

## ⚡ INICIO RÁPIDO (resumen)

### Prerequisitos

- Python 3.11+, Node.js 18+, Docker y Docker Compose, Git

### Instalación mínima

```bash
git clone https://github.com/ssebasarias/DropTools.git
cd DropTools
cp .env.example .env
cp .env.example .env.docker
# Editar .env y .env.docker con tus valores

python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

cd frontend && npm install && cd ..
docker compose up -d
```

### Ejecutar Pipeline ETL (4 Terminales)

```bash
# Terminal 1: Scraper (Extracción)
.\activate_env.bat
python backend/manage.py scraper

# Terminal 2: Loader (Carga a DB)
.\activate_env.bat
python backend/manage.py loader

# Terminal 3: Vectorizer (IA - Embeddings)
.\activate_env.bat
python backend/manage.py vectorizer

# Terminal 4: Clusterizer (Agrupación)
.\activate_env.bat
python backend/manage.py clusterizer
```

### Acceder a Servicios

- **Frontend (React):** http://localhost:5173
- **Backend API:** http://localhost:8000
- **Django Admin:** http://localhost:8000/admin
- **Flower (Celery):** http://localhost:5555
- **pgAdmin:** http://localhost:5050

---

## 🔐 Seguridad / Auth / Suscripciones (local)

### Auth

- **TokenAuthentication (DRF)**.
- Endpoints:
  - `POST /api/auth/register/` (registro público)
  - `POST /api/auth/login/`
  - `GET /api/auth/me/`

### Roles

- **ADMIN**: control total (interfaces `/admin/*` + endpoints de control/IA protegidos).
- **CLIENT**: interfaces `/user/*` con módulos habilitados por suscripción.

### Suscripciones (tiers)

- **BRONZE**: Reporter (generación de reportes / worker accounts)
- **SILVER**: + Report Analysis (AnalystReporter)
- **GOLD**: + Winner Products
- **PLATINUM**: + Market Intelligence + creativos (próximo)

### Suscripción activa (sin pagos todavía)

- Al registrarse: `subscription_active=false` (puede loguearse y ver UI, pero backend bloquea acciones).
- Para pruebas (sin pagos): activa la suscripción desde el endpoint admin o usando el comando de seed.

### Crear usuarios de prueba por tier

Ejecuta en `backend/`:

```bash
python manage.py seed_test_users --password "Test1234!" --domain "local.test" --prefix "tier"
```

Esto crea:
- `tier.bronze@local.test`
- `tier.silver@local.test`
- `tier.gold@local.test`
- `tier.platinum@local.test`

### Admin: gestionar suscripciones (sin pagos)

Endpoints (requieren rol `ADMIN`):
- `GET /api/admin/users/`
- `POST /api/admin/users/<user_id>/subscription/` body:
  - `subscription_tier`: `BRONZE|SILVER|GOLD|PLATINUM`
  - `subscription_active`: `true|false`

### Ejecutar workflow de reportes para un usuario cliente

El `workflow_orchestrator` ejecuta el flujo completo de generación de reportes:
1. Descarga reportes de Dropi (`reporterdownloader`)
2. Compara reportes y genera CSV (`reportcomparer`)
3. Procesa órdenes sin movimiento (`reporter`)

**Ejecutar con email del usuario cliente:**

```bash
# Desde backend/
python manage.py workflow_orchestrator --user-email "tier.bronze@local.test"
```

**Ejecutar con ID del usuario:**

```bash
python manage.py workflow_orchestrator --user-id 2
```

**Modo headless (sin interfaz gráfica):**

```bash
python manage.py workflow_orchestrator --user-email "cliente@ejemplo.com" --headless
```

**Usando scripts de ayuda:**

```powershell
# Windows PowerShell
.\scripts\run_workflow_for_client.ps1 -ClientEmail "tier.bronze@local.test"
.\scripts\run_workflow_for_client.ps1 -ClientEmail "cliente@ejemplo.com" -Headless
```

```bash
# Linux/Mac
./scripts/run_workflow_for_client.sh tier.bronze@local.test
./scripts/run_workflow_for_client.sh cliente@ejemplo.com --headless
```

**Requisitos:**
- El usuario debe existir en la base de datos
- El usuario debe tener `subscription_active=True` (o ser ADMIN)
- El usuario debe tener una `DropiAccount` configurada con label "reporter" (o default)

---

## 📚 DOCUMENTACIÓN

### 🎯 Guías por Objetivo

| Quiero... | Leer... | Tiempo |
|-----------|---------|--------|
| **Empezar rápido** | [docs/INICIO_RAPIDO.md](docs/INICIO_RAPIDO.md) | 10 min |
| **Ver comandos** | [docs/GUIA_COMANDOS.md](docs/GUIA_COMANDOS.md) | Referencia |
| **Solucionar problemas** | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Referencia |
| **Configurar desarrollo** | [docs/GUIA_DESARROLLO.md](docs/GUIA_DESARROLLO.md) | 20 min |
| **Entender arquitectura** | [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) | 30 min |
| **Conocer el proyecto** | [docs/PROYECTO.md](docs/PROYECTO.md) | 15 min |

### 📖 Índice Completo

Ver **[docs/README.md](docs/README.md)** para el índice completo de documentación.

---

## 🏗️ ARQUITECTURA

```
┌─────────────────────────────────────────────────────────┐
│                      DropTools                          │
└─────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Scraper    │───▶│    Loader    │───▶│  PostgreSQL  │
│   (Dropi)    │    │   (ETL)      │    │  + pgvector  │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                    ┌──────────────────────────┘
                    │
        ┌───────────▼───────────┐    ┌──────────────┐
        │    Vectorizer         │───▶│  Embeddings  │
        │  (CLIP AI Model)      │    │  (512-dim)   │
        └───────────────────────┘    └──────┬───────┘
                                            │
                    ┌───────────────────────┘
                    │
        ┌───────────▼───────────┐    ┌──────────────┐
        │    Clusterizer        │───▶│   Clusters   │
        │  (Hard + Soft Match)  │    │  (Productos) │
        └───────────────────────┘    └──────────────┘
```

**Ver arquitectura completa:** [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md)

---

## 🛠️ TECNOLOGÍAS

### Backend
- **Django 5.x** - Framework web
- **Django REST Framework** - API
- **PostgreSQL 17** - Base de datos relacional
- **pgvector** - Extensión para búsqueda vectorial
- **Celery + Redis** - Cola de tareas (reportes)

### IA / Machine Learning
- **PyTorch** - Framework de deep learning
- **CLIP (OpenAI)** - Modelo multimodal (imagen + texto)
- **Transformers** - Modelos pre-entrenados
- **scikit-learn** - Algoritmos de clustering

### Web Scraping
- **Selenium** - Automatización de navegador
- **WebDriver Manager** - Gestión de drivers

### Frontend
- **React 19** - UI
- **Vite** - Build y dev server
- **React Router** - Navegación
- **Leaflet / react-leaflet** - Mapa Colombia (dashboard cliente)

### DevOps
- **Docker** - Contenedores
- **Docker Compose** - Orquestación
- **pgAdmin** - Administración de DB

---

## 📊 ESTRUCTURA DEL PROYECTO

```
DropTools/
├── 📄 README.md                    ← EMPEZAR AQUÍ
├── 📄 requirements.txt             ← Dependencias Python
├── 📄 .env.example                 ← Plantilla de variables (copiar a .env)
├── 📄 docker-compose.yml            ← Orquestación Docker
├── 📄 Dockerfile                   ← Imagen Docker
├── 📄 .gitignore                   ← Archivos ignorados por Git
│
├── 📂 backend/                      ← DJANGO BACKEND
│   ├── manage.py                    ← CLI de Django
│   ├── droptools_backend/              ← Configuración Django (settings, urls, celery)
│   └── core/                        ← App principal
│       ├── management/commands/    ← COMANDOS ETL y Reporter ⭐
│       │   ├── scraper.py           ← Extracción de Dropi
│       │   ├── loader.py            ← Carga a PostgreSQL
│       │   ├── vectorizer.py        ← Embeddings
│       │   ├── clusterizer.py      ← Agrupación
│       │   └── unified_reporter.py ← Reporter unificado
│       └── reporter_bot/            ← Lógica del reporter (Dropi)
│
├── 📂 frontend/                     ← REACT + VITE
│   ├── package.json                 ← Dependencias Node
│   ├── public/                      ← Assets estáticos (incl. colombia-deptos.geojson)
│   └── src/                         ← Componentes, páginas, servicios
│
├── 📂 docs/                         ← DOCUMENTACIÓN
│   ├── droptools_db.sql                ← Script init DB (Docker)
│   ├── GUIA_COMANDOS.md             ← Guía de comandos
│   ├── ARQUITECTURA.md              ← Arquitectura
│   └── examples/                   ← Archivos de ejemplo
│
├── 📂 scripts/                      ← Scripts de ayuda (activate_env.bat, run_unified_reporter_local.*)
├── 📂 backups/                      ← Backups de DB (no subir *.sql)
├── 📂 raw_data/                     ← Datos crudos (no subir)
└── 📂 venv/                         ← Entorno virtual (no subir)
```

---

## 🎯 CASOS DE USO

### 1. Encontrar Productos con Baja Competencia
```sql
SELECT * FROM view_golden_opportunities
WHERE total_competitors <= 3
AND potential_profit > 20000
ORDER BY potential_profit DESC;
```

### 2. Detectar Arbitraje de Precios
```sql
SELECT cluster_id, MIN(sale_price), MAX(sale_price),
       MAX(sale_price) - MIN(sale_price) AS price_gap
FROM products p
JOIN product_cluster_membership m ON p.product_id = m.product_id
GROUP BY cluster_id
HAVING MAX(sale_price) - MIN(sale_price) > 10000
ORDER BY price_gap DESC;
```

### 3. Analizar Saturación por Categoría
```bash
# Usar diagnóstico del sistema
python backend/manage.py diagnose_stats
```

---

## 🔧 COMANDOS PRINCIPALES

### Entorno Virtual
```bash
# Activar (SIEMPRE PRIMERO)
.\activate_env.bat

# Desactivar
deactivate
```

### Pipeline ETL
```bash
# Scraper
python backend/manage.py scraper

# Loader
python backend/manage.py loader

# Vectorizer
python backend/manage.py vectorizer

# Clusterizer
python backend/manage.py clusterizer

# Diagnóstico
python backend/manage.py diagnose_stats
```

### Docker
```bash
# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener servicios
docker-compose down
```

**Ver todos los comandos:** [docs/GUIA_COMANDOS.md](docs/GUIA_COMANDOS.md)

---

## 📈 ROADMAP

### ✅ Completado
- [x] Web scraping de Dropi
- [x] Pipeline ETL completo
- [x] Vectorización con CLIP
- [x] Clustering multi-criterio
- [x] Dockerización completa
- [x] API REST con Django REST Framework
- [x] Frontend con React + Vite
- [x] Reporter unificado (Dropi) y Celery
- [x] Dashboard cliente con KPIs y mapa Colombia
- [x] Documentación y .env.example

### 🔮 Futuro
- [ ] Análisis de tendencias temporales
- [ ] Predicción de demanda con ML
- [ ] App móvil

---

## 🐛 SOLUCIÓN RÁPIDA DE PROBLEMAS

### Error: "ModuleNotFoundError"
```bash
.\activate_env.bat
pip install [nombre_modulo]
```

### Error: "Connection refused" (DB)
```bash
docker ps  # Verificar que Docker está corriendo
docker-compose up -d  # Iniciar si no está corriendo
```

### Error: "UnicodeDecodeError"
```bash
# Usar activate_env.bat (configura UTF-8)
.\activate_env.bat
```

**Ver guía completa:** [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

## 🤝 CONTRIBUIR

### Reportar Bugs
Abre un issue con:
- Descripción del problema
- Pasos para reproducir
- Logs relevantes

### Sugerir Mejoras
Abre un issue con:
- Descripción de la mejora
- Casos de uso
- Beneficios esperados

---

## 📝 LICENCIA

[Especificar licencia]

---

## 👥 AUTORES

- **Desarrollador Principal** - [Tu Nombre]

---

## 🙏 AGRADECIMIENTOS

- OpenAI por el modelo CLIP
- Hugging Face por Transformers
- Comunidad de Django
- Comunidad de PostgreSQL

---

## 📞 SOPORTE

- **Documentación:** Ver carpeta `docs/`
- **Guía de Comandos:** [docs/GUIA_COMANDOS.md](docs/GUIA_COMANDOS.md)
- **Issues:** [GitHub Issues]
- **Email:** [tu_email@ejemplo.com]

---

## 🎓 RECURSOS ADICIONALES

- **Django:** https://docs.djangoproject.com/
- **PostgreSQL:** https://www.postgresql.org/docs/
- **Docker:** https://docs.docker.com/
- **CLIP:** https://github.com/openai/CLIP
- **pgvector:** https://github.com/pgvector/pgvector

---

**Última actualización:** 2026-02  
**Versión:** 2.2  
**Estado:** ✅ En ejecución  
**Proyecto:** DropTools
