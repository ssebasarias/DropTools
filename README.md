# 🚀 DAHELL INTELLIGENCE

**Sistema de Análisis de Saturación de Mercado para Dropshipping con IA**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0-green.svg)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue.svg)](https://www.docker.com/)

---

## 📋 ¿Qué es Dahell Intelligence?

Sistema de inteligencia artificial que detecta la saturación de mercado en productos de dropshipping. Utiliza embeddings vectoriales (CLIP) para identificar productos idénticos vendidos por diferentes proveedores, permitiendo encontrar **oportunidades de negocio con baja competencia**.

### 🎯 Problema que Resuelve

**Desafío:** Un mismo producto físico es vendido por múltiples proveedores usando diferentes nombres y fotos, haciendo difícil evaluar la competencia real.

**Solución:** Usar IA (embeddings vectoriales) para "ver" y "leer" productos. Si dos productos tienen vectores similares, son el mismo producto.

**Valor:** Identificar productos con alta demanda pero baja competencia (oportunidades de oro 💰).

---

## ⚡ INICIO RÁPIDO (5 minutos)

### 1. Prerequisitos

- Python 3.12+
- Docker y Docker Compose
- Git

### 2. Instalación

```bash
# Clonar repositorio
git clone [url_del_repositorio]
cd Dahell

# Crear y activar entorno virtual
python -m venv venv
.\activate_env.bat

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
# Editar .env con tus credenciales de Dropi

# Iniciar servicios Docker
docker-compose up -d
```

### 3. Ejecutar Pipeline ETL (4 Terminales)

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

### 4. Acceder a Servicios

- **pgAdmin:** http://localhost:5050
- **Dashboard:** http://localhost:8501 (próximamente)
- **Django Admin:** http://localhost:8000/admin

---

## 📚 DOCUMENTACIÓN

### 🎯 Guías por Objetivo

| Quiero... | Leer... | Tiempo |
|-----------|---------|--------|
| **Empezar rápido** | [INICIO_RAPIDO.md](INICIO_RAPIDO.md) | 10 min |
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
│                    DAHELL INTELLIGENCE                  │
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
- **Django 6.0** - Framework web
- **PostgreSQL 17** - Base de datos relacional
- **pgvector** - Extensión para búsqueda vectorial

### IA / Machine Learning
- **PyTorch** - Framework de deep learning
- **CLIP (OpenAI)** - Modelo multimodal (imagen + texto)
- **Transformers** - Modelos pre-entrenados
- **scikit-learn** - Algoritmos de clustering

### Web Scraping
- **Selenium** - Automatización de navegador
- **WebDriver Manager** - Gestión de drivers

### DevOps
- **Docker** - Contenedores
- **Docker Compose** - Orquestación
- **pgAdmin** - Administración de DB

---

## 📊 ESTRUCTURA DEL PROYECTO

```
Dahell/
├── 📄 README.md                    ← EMPEZAR AQUÍ
├── 📄 INICIO_RAPIDO.md             ← Guía visual rápida
├── 📄 requirements.txt             ← Dependencias
├── 📄 activate_env.bat             ← Activar venv (USAR SIEMPRE)
├── 📄 config_encoding.py           ← Configuración UTF-8
├── 📄 docker-compose.yml           ← Orquestación Docker
├── 📄 Dockerfile                   ← Imagen Docker
├── 📄 .env                         ← Config local (NO SUBIR A GIT)
├── 📄 .gitignore                   ← Git ignore
│
├── 📂 backend/                     ← DJANGO BACKEND
│   ├── manage.py                   ← CLI de Django
│   ├── dahell_db.sql               ← Esquema de DB
│   ├── dahell_backend/             ← Configuración Django
│   └── core/                       ← App principal
│       └── management/commands/    ← COMANDOS ETL ⭐
│           ├── scraper.py          ← Extracción de Dropi
│           ├── loader.py           ← Carga a PostgreSQL
│           ├── vectorizer.py       ← Generación de embeddings
│           ├── clusterizer.py      ← Agrupación de productos
│           └── diagnose_stats.py   ← Diagnóstico del sistema
│
├── 📂 docs/                        ← DOCUMENTACIÓN
│   ├── GUIA_COMANDOS.md            ← Guía principal ⭐
│   ├── ARQUITECTURA.md             ← Arquitectura técnica
│   ├── GUIA_VENV.md                ← Entorno virtual
│   ├── PROYECTO.md                 ← Descripción del proyecto
│   └── examples/                   ← Archivos de ejemplo
│
├── 📂 logs/                        ← Logs de producción
├── 📂 backups/                     ← Backups de DB
├── 📂 raw_data/                    ← Datos crudos (JSONL)
├── 📂 cache_huggingface/           ← Caché de modelos IA
└── 📂 venv/                        ← Entorno virtual (NO SUBIR)
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
- [x] Normalización UTF-8
- [x] Documentación completa

### 🚧 En Desarrollo
- [ ] Dashboard con Streamlit
- [ ] API REST con Django REST Framework
- [ ] Sistema de alertas

### 🔮 Futuro
- [ ] Frontend con React
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

**Última actualización:** 2025-12-14  
**Versión:** 2.0 (Profesional)  
**Estado:** ✅ Listo para Producción
