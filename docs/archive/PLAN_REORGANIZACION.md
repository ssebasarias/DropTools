# 🏗️ PLAN DE REORGANIZACIÓN DEL PROYECTO

## 📋 OBJETIVO
Consolidar toda la lógica en Django (backend) y eliminar duplicados para tener una estructura profesional.

---

## 🎯 CAMBIOS A REALIZAR

### 1. Eliminar Scripts Standalone Duplicados ❌
```
scripts/
├── diagnose_system.py     → ❌ ELIMINAR (duplicado de manage.py diagnose_stats)
├── test_db_encoding.py    → ❌ ELIMINAR (ya no necesario, encoding normalizado)
└── test_read.py           → ❌ ELIMINAR (script de prueba temporal)
```

**Razón:** Toda la lógica ya está en `backend/core/management/commands/`

### 2. Consolidar Archivos de Configuración 📝

#### Requirements
```
ANTES:
├── requirements.txt          → Básico
├── requirements_complete.txt → Completo
└── requirements_minimal.txt  → Mínimo

DESPUÉS:
└── requirements.txt          → ÚNICO (versión completa)
```

#### Archivos .env
```
MANTENER:
├── .env                      → Configuración local ✅
└── .env_docker               → Configuración Docker ✅

ELIMINAR:
└── (ninguno, están bien)
```

#### Archivos SQL
```
ANTES:
├── dahell_db.sql             → Raíz
├── backend/dahell_db.sql     → Backend (duplicado)
└── backup_dahell_db.sql      → Backup (843 MB)

DESPUÉS:
├── backend/dahell_db.sql     → ÚNICO (en backend) ✅
└── backups/                  → Nueva carpeta para backups
    └── backup_dahell_db.sql
```

### 3. Reorganizar Documentación 📚

```
ANTES (archivos dispersos en raíz):
├── DIAGNOSTICO_SISTEMA.md
├── GUIA_VENV.md
├── NORMALIZACION_RESUMEN.md
├── README_NORMALIZACION.md
├── pryecto.md
└── README.md

DESPUÉS (todo en docs/):
docs/
├── GUIA_COMANDOS.md          → ✅ NUEVO (guía principal)
├── GUIA_VENV.md              → Movido desde raíz
├── DIAGNOSTICO_SISTEMA.md    → Movido desde raíz
├── NORMALIZACION_RESUMEN.md  → Movido desde raíz
├── ARQUITECTURA.md           → ✅ NUEVO (descripción técnica)
└── PROYECTO.md               → Renombrado de pryecto.md

RAÍZ:
└── README.md                 → ✅ ACTUALIZADO (índice principal)
```

### 4. Limpiar Archivos Temporales 🗑️

```
ELIMINAR:
├── settings.py               → Obsoleto (usar backend/dahell_backend/settings.py)
├── install_log.txt           → Log temporal
├── migrate_error.txt         → Error antiguo
├── verificar_encoding.py     → Script temporal de verificación
└── index deproductos en dropi.json → Archivo de ejemplo (mover a docs/examples/)
```

### 5. Crear Carpetas Faltantes 📁

```
CREAR:
├── logs/                     → Para logs de producción
├── backups/                  → Para backups de DB
└── docs/examples/            → Para archivos de ejemplo
```

---

## 📊 ESTRUCTURA FINAL

```
Dahell/
├── .env                          # Configuración local
├── .env_docker                   # Configuración Docker
├── .gitignore                    # Git ignore
├── README.md                     # Documentación principal
├── requirements.txt              # Dependencias (ÚNICO)
├── activate_env.bat              # Activador de venv
├── config_encoding.py            # Configuración UTF-8
├── docker-compose.yml            # Orquestación Docker
├── Dockerfile                    # Imagen Docker
├── verificar_encoding.py         # Script de verificación
│
├── backend/                      # Django Backend
│   ├── manage.py                 # CLI de Django
│   ├── dahell_db.sql             # Esquema de DB (ÚNICO)
│   ├── dahell_backend/           # Configuración Django
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── core/                     # App principal
│       ├── models.py             # Modelos ORM
│       ├── views.py
│       ├── admin.py
│       └── management/
│           └── commands/         # Management commands
│               ├── scraper.py    # ✅ Scraper
│               ├── loader.py     # ✅ Loader
│               ├── vectorizer.py # ✅ Vectorizer
│               ├── clusterizer.py# ✅ Clusterizer
│               └── diagnose_stats.py # ✅ Diagnóstico
│
├── frontend/                     # React Frontend (futuro)
│   ├── src/
│   ├── public/
│   └── package.json
│
├── docs/                         # Documentación
│   ├── GUIA_COMANDOS.md          # ✅ Guía principal
│   ├── GUIA_VENV.md              # Guía del venv
│   ├── DIAGNOSTICO_SISTEMA.md    # Diagnóstico técnico
│   ├── NORMALIZACION_RESUMEN.md  # Resumen de cambios
│   ├── ARQUITECTURA.md           # Arquitectura del sistema
│   ├── PROYECTO.md               # Descripción del proyecto
│   └── examples/                 # Archivos de ejemplo
│       └── index_productos_dropi.json
│
├── logs/                         # Logs de producción
│   ├── scraper.log
│   ├── loader.log
│   ├── vectorizer.log
│   └── clusterizer.log
│
├── backups/                      # Backups de DB
│   └── backup_YYYYMMDD.sql
│
├── raw_data/                     # Datos crudos (JSONL)
│   └── raw_products_*.jsonl
│
├── cache_huggingface/            # Caché de modelos IA
│
└── venv/                         # Entorno virtual (NO subir a Git)
```

---

## ✅ CHECKLIST DE REORGANIZACIÓN

### Fase 1: Limpieza
- [ ] Eliminar `scripts/diagnose_system.py`
- [ ] Eliminar `scripts/test_db_encoding.py`
- [ ] Eliminar `scripts/test_read.py`
- [ ] Eliminar carpeta `scripts/` (si queda vacía)
- [ ] Eliminar `settings.py` (raíz)
- [ ] Eliminar `install_log.txt`
- [ ] Eliminar `backend/migrate_error.txt`
- [ ] Eliminar `requirements_minimal.txt`
- [ ] Eliminar `dahell_db.sql` (raíz, mantener el de backend)

### Fase 2: Consolidación
- [ ] Reemplazar `requirements.txt` con `requirements_complete.txt`
- [ ] Eliminar `requirements_complete.txt` (ya está en requirements.txt)

### Fase 3: Reorganización de Documentación
- [ ] Mover `GUIA_VENV.md` a `docs/`
- [ ] Mover `DIAGNOSTICO_SISTEMA.md` a `docs/`
- [ ] Mover `NORMALIZACION_RESUMEN.md` a `docs/`
- [ ] Renombrar `pryecto.md` a `docs/PROYECTO.md`
- [ ] Eliminar `README_NORMALIZACION.md` (info ya en otros docs)

### Fase 4: Crear Carpetas
- [ ] Crear `logs/`
- [ ] Crear `backups/`
- [ ] Crear `docs/examples/`
- [ ] Mover `backup_dahell_db.sql` a `backups/`
- [ ] Mover `index deproductos en dropi.json` a `docs/examples/`

### Fase 5: Actualizar README
- [ ] Crear nuevo `README.md` principal
- [ ] Agregar índice de documentación
- [ ] Agregar quick start

---

## 🚨 ADVERTENCIAS

### NO ELIMINAR:
- ✅ `venv/` - Entorno virtual
- ✅ `raw_data/` - Datos crudos
- ✅ `cache_huggingface/` - Modelos IA
- ✅ `frontend/` - Frontend React
- ✅ `.env` y `.env_docker` - Configuración
- ✅ `activate_env.bat` - Activador de venv
- ✅ `config_encoding.py` - Configuración UTF-8

### VERIFICAR ANTES DE ELIMINAR:
- ⚠️ Scripts en `scripts/` - Verificar que no haya lógica única
- ⚠️ `backup_dahell_db.sql` - Es un backup grande (843 MB), mover a `backups/`

---

## 📝 NOTAS

1. **Scripts standalone eliminados:** Toda la lógica está en Django management commands
2. **Documentación centralizada:** Todo en `docs/` para fácil acceso
3. **Configuración unificada:** Un solo `requirements.txt` con todo
4. **Estructura profesional:** Sigue convenciones de Django

---

**Próximo paso:** Ejecutar el plan de reorganización
